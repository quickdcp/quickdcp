#!/usr/bin/env python3
"""
QuickDCP Worker (fixed)

Polls the API for the next job, simulates processing, and posts back a manifest.
Environment:
  API_BASE       = http://localhost:8080 (default)
  WORKER_TOKEN   = dev-worker-token (must match server)
  QD_CUSTOMER    = dev
  QD_KEY         = dev
  POLL_MS        = 1000 (poll interval)
"""
from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict

import requests

API = os.getenv("API_BASE", "http://localhost:8080")
TOK = os.getenv("WORKER_TOKEN", "dev-worker-token")
H = {
    "X-Worker-Token": TOK,
    "Authorization": f"QuickDCP {os.getenv('QD_KEY', 'dev')}",
    "X-QD-Customer": os.getenv("QD_CUSTOMER", "dev"),
    "Content-Type": "application/json",
}
POLL_MS = int(os.getenv("POLL_MS", "1000"))


def log(*a: Any) -> None:
    print("[worker]", *a, flush=True)


def process(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate a DCP render + QC manifest."""
    time.sleep(random.uniform(0.4, 1.2))
    return {
        "profile": profile or {},
        "outputs": {
            "dcp_zip": f"s3://quickdcp-out/{int(time.time())}/dcp.zip",
        },
        "qc": {
            "audio_lufs": -23.0,
            "video_issues": 0,
            "subtitle_sync_ms": 5,
        },
        "proof": {},
    }


def main() -> None:
    log("start", "api=", API)
    while True:
        try:
            r = requests.post(f"{API}/jobs/internal/next-job", headers=H, timeout=(10, 300))
            j = r.json()
        except Exception:
            time.sleep(POLL_MS / 1000.0)
            continue

        if j.get("status") == "EMPTY":
            time.sleep(POLL_MS / 1000.0)
            continue

        jid = j.get("job_id")
        if not jid:
            time.sleep(0.5)
            continue

        log("processing", jid)
        man = {
            "job_id": jid,
            **process(j.get("profile", {})),
        }
        body = {"job_id": jid, "manifest": man, "status": "PASS"}
        try:
            requests.post(f"{API}/jobs/internal/update-job", headers=H, data=json.dumps(body), timeout=(10, 300)).raise_for_status()
            log("updated", jid)
        except Exception as e:
            log("update failed", jid, e)
            time.sleep(1)

        time.sleep(0.1)


if __name__ == "__main__":
    main()
