"""
QuickDCP Python SDK (fixed)

Minimal client for the QuickDCP API with multipart upload helper.
Requires: requests>=2.31, Python 3.9+

Example:
    from quickdcp.client import QuickDCP
    qc = QuickDCP(base_url="http://localhost:8080", customer="dev", api_key="dev")
    r = qc.render_job({"job_id": "JOB-1", "profile": {"res": "2K"}})
    print(r)
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import pathlib
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, TypedDict, Union

import requests

# --------------------------------------------------------------------------------------
# Types
# --------------------------------------------------------------------------------------
class RenderResponse(TypedDict):
    job_id: str
    status: str

class JobSummary(TypedDict):
    job_id: str
    status: str

class ProofInitRes(TypedDict):
    job_id: str
    manifest_sha256: str
    tsq_der: str

class ProofAckRes(TypedDict):
    job_id: str
    status: str
    manifest_sha256: str
    tsa_ok: bool

class UploadInitRes(TypedDict):
    upload_id: str
    key: str
    size: int
    sha256: str

class PartSignRes(TypedDict):
    url: str

class CompletePart(TypedDict):
    ETag: str
    PartNumber: int

class HeadRes(TypedDict):
    key: str
    exists: bool
    size: Optional[int]


@dataclass
class ClientOptions:
    base_url: str
    customer: str
    api_key: str
    timeout: Tuple[int, int] = (10, 300)  # (connect, read)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def _headers(opts: ClientOptions, content: Optional[str] = "application/json") -> Dict[str, str]:
    h = {
        "X-QD-Customer": opts.customer,
        "Authorization": f"QuickDCP {opts.api_key}",
    }
    if content:
        h["Content-Type"] = content
    return h


def _jsonfetch(opts: ClientOptions, method: str, url: str, **kw) -> Any:
    r = requests.request(method, url, timeout=opts.timeout, **kw)
    txt = r.text
    try:
        data = r.json() if txt else None
    except Exception:
        data = None
    if not r.ok:
        raise requests.HTTPError(f"HTTP {r.status_code}: {data or txt}", response=r)
    return data


def _sha256_file(path: Union[str, os.PathLike], block: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_b64(buf: bytes) -> str:
    return base64.b64encode(hashlib.sha256(buf).digest()).decode()


# --------------------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------------------
class QuickDCP:
    def __init__(self, base_url: str, customer: str, api_key: str, timeout: Tuple[int, int] | None = None) -> None:
        self.opts = ClientOptions(base_url.rstrip("/"), customer, api_key, timeout or (10, 300))

    # ----------------- Jobs -----------------
    def render_job(self, payload: Dict[str, Any]) -> RenderResponse:
        url = f"{self.opts.base_url}/jobs/render"
        return _jsonfetch(self.opts, "POST", url, headers=_headers(self.opts), data=json.dumps(payload))

    def get_job(self, job_id: str) -> Dict[str, Any]:
        url = f"{self.opts.base_url}/jobs/{requests.utils.quote(job_id)}"
        return _jsonfetch(self.opts, "GET", url, headers=_headers(self.opts, content=None))

    def list_jobs(self) -> List[JobSummary]:
        url = f"{self.opts.base_url}/jobs"
        return _jsonfetch(self.opts, "GET", url, headers=_headers(self.opts, content=None))

    # ----------------- Proof -----------------
    def proof_init(self, job_id: str) -> ProofInitRes:
        url = f"{self.opts.base_url}/proof/init"
        return _jsonfetch(self.opts, "POST", url, headers=_headers(self.opts), data=json.dumps({"job_id": job_id}))

    def proof_ack_tsa(self, job_id: str, tsr_base64: str, tsa_cert_pem: Optional[str] = None) -> ProofAckRes:
        url = f"{self.opts.base_url}/proof/ack/tsa"
        body = {"job_id": job_id, "tsr_base64": tsr_base64}
        if tsa_cert_pem:
            body["tsa_cert_pem"] = tsa_cert_pem
        return _jsonfetch(self.opts, "POST", url, headers=_headers(self.opts), data=json.dumps(body))

    def proof_status(self, job_id: str) -> ProofAckRes:
        url = f"{self.opts.base_url}/proof/status/{requests.utils.quote(job_id)}"
        return _jsonfetch(self.opts, "GET", url, headers=_headers(self.opts, content=None))

    # ----------------- Upload -----------------
    def upload_init(self, filename: str, size: int, sha256: str) -> UploadInitRes:
        url = f"{self.opts.base_url}/upload/init"
        form = {
            "filename": filename,
            "size": str(size),
            "sha256": sha256,
        }
        return _jsonfetch(self.opts, "POST", url, headers=_headers(self.opts, content="application/x-www-form-urlencoded"), data=requests.models.RequestEncodingMixin._encode_params(form))

    def sign_part(self, key: str, upload_id: str, part_number: int) -> PartSignRes:
        url = f"{self.opts.base_url}/upload/part"
        form = {
            "key": key,
            "upload_id": upload_id,
            "part_number": str(part_number),
        }
        return _jsonfetch(self.opts, "POST", url, headers=_headers(self.opts, content="application/x-www-form-urlencoded"), data=requests.models.RequestEncodingMixin._encode_params(form))

    def upload_complete(self, key: str, upload_id: str, parts: List[CompletePart]) -> Dict[str, Any]:
        url = f"{self.opts.base_url}/upload/complete"
        body = {"key": key, "upload_id": upload_id, "parts": parts}
        return _jsonfetch(self.opts, "POST", url, headers=_headers(self.opts), data=json.dumps(body))

    def upload_head(self, key: str) -> HeadRes:
        url = f"{self.opts.base_url}/upload/head?key={requests.utils.quote(key)}"
        return _jsonfetch(self.opts, "GET", url, headers=_headers(self.opts, content=None))

    # ----------------- High-level multipart -----------------
    def upload_file(self, filepath: Union[str, os.PathLike], part_size_mb: int = 64) -> Dict[str, Any]:
        """Upload a local file via multipart and return { key, sha256, size, parts }.

        S3 enforces 5MB min per part; we enforce that here. Uses streaming and
        computes the file SHA-256 up-front so the API can record it.
        """
        p = pathlib.Path(filepath).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(str(p))
        size = p.stat().st_size
        sha = _sha256_file(p)

        init = self.upload_init(p.name, size, sha)
        key = init["key"]
        upload_id = init["upload_id"]

        part_size = max(5, part_size_mb) * 1024 * 1024
        parts: List[CompletePart] = []
        sent = 0
        t0 = time.time()

        with open(p, "rb") as f:
            part_no = 1
            while True:
                chunk = f.read(part_size)
                if not chunk:
                    break
                # get presigned url
                presign = self.sign_part(key, upload_id, part_no)
                url = presign["url"]
                chk = _sha256_b64(chunk)
                # PUT to S3
                put = requests.put(url, data=chunk, headers={"x-amz-checksum-sha256": chk}, timeout=self.opts.timeout)
                if put.status_code not in (200, 201):
                    raise requests.HTTPError(f"part PUT failed: {put.status_code} {put.text}")
                etag = (put.headers.get("ETag") or "").strip('"')
                if not etag:
                    raise RuntimeError("missing ETag on part PUT")
                parts.append({"ETag": etag, "PartNumber": part_no})
                sent += len(chunk)
                # progress (stderr)
                elapsed = max(0.001, time.time() - t0)
                rate = sent / elapsed
                pct = (sent / size * 100.0) if size else 100.0
                print(f"[qdcp] part {part_no} — {pct:.1f}% @ {int(rate/1024/1024)} MB/s", flush=True)
                part_no += 1

        self.upload_complete(key, upload_id, parts)
        return {"key": key, "sha256": sha, "size": size, "parts": len(parts)}


__all__ = [
    "QuickDCP",
    "ClientOptions",
    "RenderResponse",
    "JobSummary",
    "ProofInitRes",
    "ProofAckRes",
    "UploadInitRes",
    "PartSignRes",
    "CompletePart",
    "HeadRes",
]
