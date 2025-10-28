"""
QuickDCP startup checks (fixed)

Runs at app boot to surface misconfiguration early. This module only prints
warnings; it must not crash the API. In production you may choose to raise on
critical misconfig.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable

REQUIRED_ENV = [
    "AWS_DEFAULT_REGION",
    "S3_BUCKET_INGEST",
]

OPTIONAL_ENV = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "WORKER_TOKEN",
    "FILMPASSPORT_BASE",
    "FILMPASSPORT_KEY",
]


def _warn(msg: str) -> None:
    print(f"[startup] WARN: {msg}")


def _info(msg: str) -> None:
    print(f"[startup] INFO: {msg}")


def _check_env(names: Iterable[str], required: bool = False) -> None:
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        if required:
            _warn(f"missing required env: {', '.join(missing)}")
        else:
            _info(f"missing optional env: {', '.join(missing)}")


def _check_files() -> None:
    root = Path(__file__).resolve().parents[1]
    public = root / "public"
    if not (public / "verify.html").exists():
        _info("public/verify.html not found (optional)")
    sbom = root / "vault" / "sbom.spdx.json"
    if not sbom.exists():
        _info("vault/sbom.spdx.json not found (optional)")


def _check_tools() -> None:
    # openssl is required for proof chain
    if shutil.which("openssl") is None:
        _warn("openssl not found in PATH (proof endpoints will fail)")


def run() -> None:
    """Entry-point: run all checks; never raise."""
    try:
        _check_env(REQUIRED_ENV, required=True)
        _check_env(OPTIONAL_ENV, required=False)
        _check_files()
        _check_tools()
        _info("startup checks completed")
    except Exception as e:
        _warn(f"startup checks encountered an error: {e}")
