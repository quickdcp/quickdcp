"""
QuickDCP auth utilities (fixed)
- FastAPI dependency `require_auth` to guard protected routes
- Header contract:
    X-QD-Customer: <customer-id>
    Authorization: QuickDCP <api-key>
- Helpful errors when scheme is wrong (e.g., Bearer instead of QuickDCP)
- Returns a context dict that routers can optionally use
"""
from __future__ import annotations

from fastapi import Header, HTTPException
from typing import Optional, Dict

SCHEME = "QuickDCP "


def _fail(msg: str) -> None:
    # 401 with a descriptive message; add a hint to use the right scheme
    raise HTTPException(
        status_code=401,
        detail=msg,
        headers={"WWW-Authenticate": "QuickDCP realm=api"},
    )


def _parse_authorization(authorization: str) -> str:
    """Validate Authorization header and return the API key string."""
    if authorization.startswith("Bearer "):
        _fail("Use 'Authorization: QuickDCP <key>' (not Bearer)")
    if not authorization.startswith(SCHEME):
        _fail("Authorization scheme must be 'QuickDCP <key>'")
    key = authorization[len(SCHEME) :].strip()
    if not key:
        _fail("Empty API key")
    return key


def require_auth(
    x_qd_customer: str = Header(..., alias="X-QD-Customer"),
    authorization: str = Header(..., alias="Authorization"),
) -> Dict[str, str]:
    """FastAPI dependency to protect routes.

    Returns a small context dict routers can consume if needed.
    """
    key = _parse_authorization(authorization)
    # Minimal sanity on customer id
    cust = x_qd_customer.strip()
    if not cust:
        _fail("X-QD-Customer header is required")
    return {"customer": cust, "api_key": key}
