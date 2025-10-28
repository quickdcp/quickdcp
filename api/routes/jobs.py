"""
QuickDCP jobs router (fixed)
- In-memory job registry (replace with DB in production)
- Create job (/jobs/render)
- Get job status or manifest (/jobs/{job_id})
- List jobs (/jobs)
- Worker internal endpoints: next-job, update-job (token guarded)
- Manifest remains locked until TSA proof OK (via proof_store)
"""
from __future__ import annotations

import os
import secrets
from typing import Dict, Optional, List

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from api.utils.proof_store import load as proof_load

router = APIRouter()

# ----------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------
class RenderProfile(BaseModel):
    # Extend as needed (resolution, aspect, rate, audio cfg)
    res: Optional[str] = Field(default=None, description="e.g. 2K, 4K")
    shape: Optional[str] = Field(default=None, description="e.g. FLAT, SCOPE")
    extras: Optional[dict] = Field(default=None, description="additional encode options")

class RenderRequest(BaseModel):
    job_id: Optional[str] = Field(default=None, description="optional custom job id")
    input_key: Optional[str] = Field(default=None, description="location of uploaded asset")
    profile: RenderProfile = Field(default_factory=RenderProfile)

class RenderResponse(BaseModel):
    job_id: str
    status: str

class JobSummary(BaseModel):
    job_id: str
    status: str

class ManifestQC(BaseModel):
    audio_lufs: Optional[float] = None
    video_issues: Optional[int] = None
    subtitle_sync_ms: Optional[int] = None

class Manifest(BaseModel):
    job_id: str
    profile: dict = Field(default_factory=dict)
    outputs: dict = Field(default_factory=dict)
    qc: ManifestQC = Field(default_factory=ManifestQC)
    proof: dict = Field(default_factory=dict)

class WorkerNextResponse(BaseModel):
    job_id: Optional[str] = None
    profile: Optional[dict] = None
    status: str = "EMPTY"

class WorkerUpdateRequest(BaseModel):
    job_id: str
    manifest: Manifest
    status: str = Field(default="PASS", regex=r"^(PASS|FAIL|PROCESSING|QUEUED)$")

# ----------------------------------------------------------------------------
# In-memory store (replace with DB)
# ----------------------------------------------------------------------------
JOBS: Dict[str, Dict] = {}
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "dev-worker-token")

# ----------------------------------------------------------------------------
# Public API (auth applied at router include in main.py)
# ----------------------------------------------------------------------------
@router.post("/render", response_model=RenderResponse)
def render_job(req: RenderRequest):
    """Create a job and set it to QUEUED. Worker will pick it up."""
    job_id = req.job_id or secrets.token_hex(6).upper()
    if job_id in JOBS:
        raise HTTPException(409, "job_id already exists")

    JOBS[job_id] = {
        "status": "QUEUED",
        "profile": (req.profile.model_dump() if isinstance(req.profile, BaseModel) else req.profile) or {},
        "input_key": req.input_key,
        "manifest": {"job_id": job_id, "proof": {}},
    }
    return RenderResponse(job_id=job_id, status="QUEUED")


@router.get("/{job_id}")
def job_status(job_id: str):
    """Return job status if not proven; unlock manifest only after TSA OK."""
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(404, "job not found")

    rec = proof_load(job_id)
    if not rec or not rec.get("tsa_ok", False):
        return {"job_id": job_id, "status": j.get("status", "PENDING")}
    return j["manifest"]


@router.get("", response_model=List[JobSummary])
def list_jobs():
    return [JobSummary(job_id=jid, status=j["status"]) for jid, j in JOBS.items()]

# ----------------------------------------------------------------------------
# Internal worker API (token guarded via header)
# ----------------------------------------------------------------------------
@router.post("/internal/next-job", response_model=WorkerNextResponse)
def next_job(x_worker_token: Optional[str] = Header(None)):
    if x_worker_token != WORKER_TOKEN:
        raise HTTPException(401, "bad token")
    for jid, j in JOBS.items():
        if j.get("status") == "QUEUED":
            j["status"] = "PROCESSING"
            return WorkerNextResponse(job_id=jid, profile=j.get("profile", {}), status="PROCESSING")
    return WorkerNextResponse(status="EMPTY")


@router.post("/internal/update-job")
def update_job(body: WorkerUpdateRequest, x_worker_token: Optional[str] = Header(None)):
    if x_worker_token != WORKER_TOKEN:
        raise HTTPException(401, "bad token")
    jid = body.job_id
    if jid not in JOBS:
        raise HTTPException(404, "job not found")
    # Coerce pydantic Manifest -> dict
    JOBS[jid]["manifest"] = body.manifest.model_dump() if isinstance(body.manifest, BaseModel) else body.manifest
    JOBS[jid]["status"] = body.status
    return {"ok": True}