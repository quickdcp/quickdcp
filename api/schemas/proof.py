"""
Pydantic schemas for QuickDCP proof routes.
Shared between routers and clients.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ProofInitReq(BaseModel):
    """Request: initialize TSA proof for a job."""
    job_id: str = Field(description="Target job id")


class ProofInitRes(BaseModel):
    """Response: TSQ material for TSA along with manifest SHA256."""
    job_id: str
    manifest_sha256: str = Field(min_length=64, max_length=64, description="Hex SHA256 of canonical manifest")
    tsq_der: str = Field(description="Base64-encoded TSQ in DER format")


class ProofAckReq(BaseModel):
    """Request: acknowledge TSA response for a job."""
    job_id: str
    tsr_base64: str = Field(description="Base64-encoded TSR (DER)")
    tsa_cert_pem: Optional[str] = Field(default=None, description="Optional CA bundle to verify against")


class ProofStatusRes(BaseModel):
    """Response: current proof state for a job."""
    job_id: str
    status: str = Field(description="PENDING or TSA_OK")
    manifest_sha256: str = Field(default="", description="Hex SHA256 of canonical manifest")
    tsa_ok: bool = Field(default=False, description="True if TSA verify completed successfully")
