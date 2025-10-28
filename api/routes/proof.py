"""
QuickDCP proof router (fixed)
- Deterministic TSQ generation from canonicalized job manifest (sha256)
- TSA acknowledgment and OpenSSL verification
- Persist proof state per job_id using proof_store
- Status endpoint to inspect current proof record
Requirements: openssl available in runtime image.
"""
from __future__ import annotations

from base64 import b64encode, b64decode
import subprocess
import tempfile
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.routes.jobs import JOBS
from api.utils.manifest import sha256_manifest
from api.utils.proof_store import init as proof_init, load as proof_load, save as proof_save

router = APIRouter()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ProofInitReq(BaseModel):
    job_id: str = Field(description="Target job id")

class ProofInitRes(BaseModel):
    job_id: str
    manifest_sha256: str
    tsq_der: str = Field(description="Base64-encoded TSQ in DER format")

class ProofAckReq(BaseModel):
    job_id: str
    tsr_base64: str = Field(description="Base64-encoded TSR (DER)")
    tsa_cert_pem: Optional[str] = Field(default=None, description="Optional CA bundle to verify against")

class ProofStatusRes(BaseModel):
    job_id: str
    status: str
    manifest_sha256: str
    tsa_ok: bool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _openssl_ts_query_hex_digest(sha_hex: str) -> bytes:
    """Return a TSQ (DER) for a given hex SHA-256 digest using openssl."""
    try:
        return subprocess.check_output([
            "openssl", "ts", "-query",
            "-sha256", "-digest", sha_hex,
            "-cert", "-no_nonce", "-outform", "DER",
        ])
    except FileNotFoundError:
        raise HTTPException(500, "openssl not found in runtime")
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"openssl ts -query failed: {e}")


def _openssl_ts_verify(tsr_der: bytes, tsq_der: bytes, ca_pem: Optional[str]) -> None:
    """Verify TSR against TSQ using openssl; raise HTTPException on failure."""
    with tempfile.TemporaryDirectory() as d:
        tsr_p = f"{d}/resp.tsr"
        tsq_p = f"{d}/req.tsq"
        with open(tsr_p, "wb") as f:
            f.write(tsr_der)
        with open(tsq_p, "wb") as f:
            f.write(tsq_der)

        cmd = ["openssl", "ts", "-verify", "-in", tsr_p, "-queryfile", tsq_p]
        if ca_pem:
            ca_p = f"{d}/tsa.pem"
            with open(ca_p, "w", encoding="utf-8") as f:
                f.write(ca_pem)
            cmd.extend(["-CAfile", ca_p])
        try:
            out = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            raise HTTPException(500, "openssl not found in runtime")
        if out.returncode != 0:
            raise HTTPException(400, f"TSA verify failed: {out.stderr.strip() or out.stdout.strip()}")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/init", response_model=ProofInitRes)
def init_proof(body: ProofInitReq):
    j = JOBS.get(body.job_id)
    if not j:
        raise HTTPException(404, "job not found")

    # Hash canonical manifest; this allows TSQ creation even before TSA ack
    sha_hex = sha256_manifest(j["manifest"])
    tsq_der = _openssl_ts_query_hex_digest(sha_hex)

    # Persist record skeleton
    proof_init(body.job_id, sha_hex)

    return ProofInitRes(job_id=body.job_id, manifest_sha256=sha_hex, tsq_der=b64encode(tsq_der).decode())


@router.post("/ack/tsa", response_model=ProofStatusRes)
def ack_tsa(body: ProofAckReq):
    rec = proof_load(body.job_id)
    if not rec:
        raise HTTPException(404, "init first")

    # Recreate TSQ deterministically from stored manifest hash
    tsq_der = _openssl_ts_query_hex_digest(rec["manifest_sha256"])  # determinism guard

    tsr_der = None
    try:
        tsr_der = b64decode(body.tsr_base64)
    except Exception:
        raise HTTPException(400, "tsr_base64 is not valid base64")

    _openssl_ts_verify(tsr_der, tsq_der, body.tsa_cert_pem)

    # Mark verified
    rec["tsa_ok"] = True
    rec["status"] = "TSA_OK"
    proof_save(body.job_id, rec)

    return ProofStatusRes(job_id=body.job_id, status=rec["status"], manifest_sha256=rec["manifest_sha256"], tsa_ok=True)


@router.get("/status/{job_id}", response_model=ProofStatusRes)
def proof_status(job_id: str):
    rec = proof_load(job_id)
    if not rec:
        raise HTTPException(404, "no proof")
    return ProofStatusRes(job_id=job_id, status=rec.get("status", "PENDING"), manifest_sha256=rec.get("manifest_sha256", ""), tsa_ok=bool(rec.get("tsa_ok")))
