"""
QuickDCP Python SDK package (fixed)

Usage:
    from quickdcp import QuickDCP
    qc = QuickDCP(base_url="http://localhost:8080", customer="dev", api_key="dev")
"""
from __future__ import annotations

from .client import (
    QuickDCP,
    ClientOptions,
    RenderResponse,
    JobSummary,
    ProofInitRes,
    ProofAckRes,
    UploadInitRes,
    PartSignRes,
    CompletePart,
    HeadRes,
)

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

__version__ = "0.1.0"
