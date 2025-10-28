"""
FilmPassport verification helper (fixed)

Purpose
-------
Tiny utility to validate FilmPassport IDs and (optionally) verify them against a
remote FilmPassport API if environment variables are provided.

Environment (optional)
----------------------
FILMPASSPORT_BASE   = e.g. https://api.filmpassport.legal
FILMPASSPORT_KEY    = API key or bearer token for remote verification
FILMPASSPORT_TIMEOUT= request timeout in seconds (default 6)

API contract (expected)
-----------------------
GET {BASE}/verify/{fp_id}
  200 -> { "status": "VALID"|"INVALID"|"PENDING", ... }

Functions
---------
- is_valid_format(fp_id): quick format check (FP-YYYY-XXXX)
- verify(fp_id, timeout=None): offline-safe verify, returns dict summary
- attach_ack(manifest: dict, fp_id: str, verify_result: dict) -> dict: mutates manifest

Notes
-----
This module is optional plumbing for the proof chain. Routers should treat
"UNKNOWN" or network errors as non-fatal and continue the TSA flow.
"""
from __future__ import annotations

import os
import re
import time
from typing import Optional, Dict, Any

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - requests is in requirements but keep soft import
    requests = None  # fallback for environments without requests

FP_REGEX = re.compile(r"^FP-(20\d{2})-([A-Z0-9]{3,12})$")


def is_valid_format(fp_id: str) -> bool:
    """Return True if fp_id looks like FP-YYYY-XXXX."""
    if not isinstance(fp_id, str):
        return False
    return bool(FP_REGEX.match(fp_id.strip()))


def _timeout(default: int = 6) -> int:
    try:
        return int(os.getenv("FILMPASSPORT_TIMEOUT", str(default)))
    except Exception:
        return default


def verify(fp_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
    """Verify a FilmPassport ID.

    If FILMPASSPORT_BASE is not set or `requests` is missing, returns an
    offline result: { status: "UNKNOWN", offline: True }.
    """
    fp_id = (fp_id or "").strip().upper()
    if not is_valid_format(fp_id):
        return {"status": "ERROR", "error": "invalid_format", "fp_id": fp_id}

    base = os.getenv("FILMPASSPORT_BASE")
    key = os.getenv("FILMPASSPORT_KEY")
    to = timeout or _timeout()

    if not base or requests is None:
        return {"status": "UNKNOWN", "offline": True, "fp_id": fp_id}

    url = f"{base.rstrip('/')}/verify/{fp_id}"
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    t0 = time.time()
    try:
        r = requests.get(url, headers=headers, timeout=to)
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "fp_id": fp_id}

    elapsed = round((time.time() - t0) * 1000)

    if r.status_code == 200:
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        status = str(data.get("status", "UNKNOWN")).upper()
        if status not in {"VALID", "INVALID", "PENDING"}:
            status = "UNKNOWN"
        return {"status": status, "details": data, "fp_id": fp_id, "rt_ms": elapsed}

    return {"status": "ERROR", "code": r.status_code, "fp_id": fp_id}


def attach_ack(manifest: Dict[str, Any], fp_id: str, verify_result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach a FilmPassport ack object to manifest["proof"].

    Returns the modified manifest for convenience.
    """
    fp_ack = {
        "fp_id": fp_id,
        "status": verify_result.get("status", "UNKNOWN"),
        "details": verify_result.get("details"),
    }
    proof = manifest.setdefault("proof", {})
    proof["fp_ack"] = fp_ack
    return manifest


if __name__ == "__main__":  # simple self-test
    tests = [
        "FP-2025-ABCD",
        "fp-2020-12345",
        "bad",
        "FP-1999-XYZ",
    ]
    for t in tests:
        print(t, is_valid_format(t), verify(t))
