"""
Public verification endpoints (fixed)

Allows anyone to check the status of a QuickDCP proof by job_id or by
manifest SHA-256 (hex). Uses the local file-backed proof_store.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.utils import proof_store

router = APIRouter()


class VerifyResponse(BaseModel):
    status: str = Field(description="PENDING or VALID")
    job_id: Optional[str] = None
    manifest_sha256: Optional[str] = None


@router.get("/{ref}", response_model=VerifyResponse)
def verify(ref: str):
    """Verify by job_id or manifest SHA-256.

    1) Try to load a proof record by job_id (exact match)
    2) If not found, scan known records and return the one whose
       manifest_sha256 equals `ref` (case-insensitive)
    """
    # 1) As job_id
    rec = proof_store.load(ref)
    if rec:
        return VerifyResponse(
            status="VALID" if rec.get("tsa_ok") else "PENDING",
            job_id=rec.get("job_id"),
            manifest_sha256=rec.get("manifest_sha256"),
        )

    # 2) As manifest sha
    ref_hex = ref.lower()
    try:
        for jid in proof_store.list_ids():
            r = proof_store.load(jid)
            if r and str(r.get("manifest_sha256", "")).lower() == ref_hex:
                return VerifyResponse(
                    status="VALID" if r.get("tsa_ok") else "PENDING",
                    job_id=r.get("job_id"),
                    manifest_sha256=r.get("manifest_sha256"),
                )
    except Exception:
        # fall through to 404
        pass

    raise HTTPException(404, "not found")
