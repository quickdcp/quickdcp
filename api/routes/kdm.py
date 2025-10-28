"""
QuickDCP KDM router (fixed)
- Issues stub KDM records and attaches them to the job manifest
- Enforces max 60-day validity window
- Accepts multiple cinema certificates
- Provides list endpoint to inspect KDMs for a job
NOTE: This is a non-cryptographic stub for MVP. In production, replace issuance
with real KDM XML generation, key wrapping, and TSA timestamping.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.routes.jobs import JOBS

router = APIRouter()

MAX_DAYS = 60

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class CinemaCert(BaseModel):
    cn: Optional[str] = Field(default=None, description="Common Name of the cinema device")
    cert_pem: str = Field(description="Cinema certificate PEM text")

    @field_validator("cert_pem")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()

class KDMIssueRequest(BaseModel):
    job_id: str
    cinemas: List[CinemaCert]
    key_id: Optional[str] = Field(default=None, description="Content key identifier (UUID hex)")
    cpl_id: Optional[str] = Field(default=None, description="Composition Playlist UUID")
    valid_from: Optional[datetime] = Field(default=None, description="UTC start time; default now")
    valid_until: Optional[datetime] = Field(default=None, description="UTC end time; mutually exclusive with days")
    days: Optional[int] = Field(default=14, description=f"Validity window in days (max {MAX_DAYS})")
    delivery_emails: Optional[List[str]] = None

    @field_validator("days")
    @classmethod
    def _max_days(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > MAX_DAYS):
            raise ValueError(f"days must be 1..{MAX_DAYS}")
        return v

class KDMRecord(BaseModel):
    kdm_id: str
    cn: str
    cert_fingerprint: str
    valid_from: str
    valid_until: str
    key_id: str
    cpl_id: Optional[str] = None
    delivered: bool = False

class KDMIssueResponse(BaseModel):
    job_id: str
    kdm_count: int
    kdms: List[KDMRecord]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _fpem(pem: str) -> str:
    """Return a short fingerprint of a PEM (sha256 hex)."""
    return hashlib.sha256(pem.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/issue", response_model=KDMIssueResponse)
def issue_kdm(body: KDMIssueRequest):
    job_id = body.job_id
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    if not body.cinemas:
        raise HTTPException(400, "cinemas is required and cannot be empty")

    # Resolve validity window
    start = body.valid_from or datetime.now(timezone.utc)
    if body.valid_until and body.days is not None:
        raise HTTPException(400, "Provide either valid_until or days, not both")
    if body.valid_until is None:
        days = body.days or 14
        if days > MAX_DAYS:
            raise HTTPException(400, f"days cannot exceed {MAX_DAYS}")
        end = start + timedelta(days=days)
    else:
        end = body.valid_until
        delta = end - start
        if delta.total_seconds() <= 0:
            raise HTTPException(400, "valid_until must be after valid_from")
        if delta > timedelta(days=MAX_DAYS):
            raise HTTPException(400, f"valid window cannot exceed {MAX_DAYS} days")

    key_id = body.key_id or str(uuid.uuid4())

    kdms: List[KDMRecord] = []
    for c in body.cinemas:
        cn = c.cn or "CINEMA-UNKNOWN"
        rec = KDMRecord(
            kdm_id=str(uuid.uuid4()),
            cn=cn,
            cert_fingerprint=_fpem(c.cert_pem),
            valid_from=_iso(start),
            valid_until=_iso(end),
            key_id=key_id,
            cpl_id=body.cpl_id,
            delivered=False,
        )
        kdms.append(rec)

    # Attach to manifest
    manifest = j.setdefault("manifest", {})
    klist = manifest.setdefault("kdm", [])
    for r in kdms:
        klist.append(r.model_dump())

    return KDMIssueResponse(job_id=job_id, kdm_count=len(kdms), kdms=kdms)


@router.get("/list/{job_id}", response_model=List[KDMRecord])
def list_kdms(job_id: str):
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    out = []
    for item in j.get("manifest", {}).get("kdm", []):
        try:
            out.append(KDMRecord(**item))
        except Exception:
            # ignore malformed entries in MVP
            continue
    return out