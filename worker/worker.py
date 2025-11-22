#!/usr/bin/env python3
"""
QuickDCP Worker

Continuously polls the API for work, normalizes ANY kind of response
(dict, list, string, None), processes jobs, and posts results back.

Environment:
  API_BASE        default: http://quickdcp-api:8080
  WORKER_TOKEN    default: dev
  POLL_INTERVAL   default: 1.0 seconds
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

import requests

API_BASE = os.getenv("API_BASE", "http://quickdcp-api:8080")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "dev")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))

HEADERS = {
    "x-worker-token": WORKER_TOKEN,
}


# ---------------------------------------------------------------------
# Payload normalizer
# ---------------------------------------------------------------------
def normalize_next_job_payload(obj: Any) -> Dict[str, Any] | None:
    """
    Normalize ANY /jobs/internal/next-job response:

        "EMPTY" / "NO_JOBS" / "NONE" → None
        [] → None
        [{}] → dict
        {} → dict
        random string → dict with {raw: ...}
        weird type → dict with {raw: ...}
    """
    # None or missing
    if obj is None:
        return None

    # Strings
    if isinstance(obj, str):
        s = obj.strip().lower()
        if s in ("empty", "none", "no_jobs", "no-jobs"):
            return None
        return {"status": "UNKNOWN", "raw": obj}

    # List-of-dicts
    if isinstance(obj, list):
        if not obj:
            return None
        first = obj[0]
        if isinstance(first, dict):
            return first
        return {"status": "UNKNOWN", "raw": obj}

    # Dict
    if isinstance(obj, dict):
        if obj.get("status") == "EMPTY":
            return None
        return obj

    # Fallback
    return {"status": "UNKNOWN", "raw": obj}


# ---------------------------------------------------------------------
# Fetch job
# ---------------------------------------------------------------------
def fetch_next_job() -> Dict[str, Any] | None:
    try:
        res = requests.post(
            f"{API_BASE}/jobs/internal/next-job",
            headers=HEADERS,
            timeout=10,
        )
    except Exception as exc:  # noqa
        print("[worker] network error:", exc)
        time.sleep(2)
        return None

    # Try decode JSON
    try:
        data = res.json()
    except Exception:
        print("[worker] /next-job non-JSON:", res.text[:200])
        return None

    # Normalize
    job = normalize_next_job_payload(data)
    return job


# ---------------------------------------------------------------------
# Update job
# ---------------------------------------------------------------------
def update_job(job_id: str, status: str, payload: Dict[str, Any] | None = None) -> None:
    body = {"job_id": job_id, "status": status}
    if payload is not None:
        body["payload"] = payload

    try:
        r = requests.post(
            f"{API_BASE}/jobs/internal/update-job",
            headers=HEADERS,
            json=body,
            timeout=10,
        )
        if r.status_code != 200:
            print("[worker] update-job error:", r.status_code, r.text[:200])
    except Exception as exc:  # noqa
        print("[worker] network error updating job:", exc)


# ---------------------------------------------------------------------
# Job processing logic
# ---------------------------------------------------------------------
def process_job(job: Dict[str, Any]) -> None:
    job_id = job.get("job_id")
    job_type = job.get("type", "unknown")

    print(f"[worker] processing job_id={job_id!r} type={job_type!r}")

    # Simulate actual work
    time.sleep(2)

    update_job(
        job_id,
        status="DONE",
        payload={"note": "dummy worker completed", "job": job},
    )

    print(f"[worker] completed job_id={job_id!r}")


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------
def main() -> None:
    print(f"[worker] start api={API_BASE} token={WORKER_TOKEN!r}")

    while True:
        job = fetch_next_job()

        if job is None:
            time.sleep(POLL_INTERVAL)
            continue

        job_id = job.get("job_id")
        if not job_id:
            print("[worker] invalid job payload:", job)
            time.sleep(POLL_INTERVAL)
            continue

        try:
            process_job(job)
        except Exception as exc:  # noqa
            print(f"[worker] error in job {job_id!r}:", exc)
            update_job(job_id, "ERROR", {"error": str(exc)})
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
