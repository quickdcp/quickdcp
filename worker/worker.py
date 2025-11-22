#!/usr/bin/env python3
"""
QuickDCP Worker (robust version)

Continuously polls the API for jobs, handles all known weird responses,
and safely processes jobs without ever crashing.

Environment:
  API_BASE       = http://quickdcp-api:8080 (Docker)
  WORKER_TOKEN   = dev
  POLL_MS        = 1000
"""

import os
import time
import json
import random
from typing import Any, Dict, List, Optional
import requests


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

API_BASE = os.environ.get("API_BASE", "http://quickdcp-api:8080")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "dev")
POLL_MS = int(os.environ.get("POLL_MS", "1000"))


def log(msg: str) -> None:
    print(f"[worker] {msg}", flush=True)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def fetch_next_job() -> Dict[str, Any]:
    """Call next-job endpoint and normalize all result shapes."""

    url = f"{API_BASE}/jobs/internal/next-job"

    try:
        resp = requests.post(
            url,
            headers={"x-worker-token": WORKER_TOKEN},
            timeout=10,
        )
    except Exception as e:
        return {"status": "NETWORK_ERROR", "error": str(e)}

    # API returns 401 → wrong worker token
    if resp.status_code == 401:
        return {"status": "BAD_TOKEN"}

    # API uses 200 ALWAYS, even for “no job”
    # Content-type always application/json
    try:
        data = resp.json()
    except Exception:
        body = resp.text.strip().replace("\n", " ")
        return {"status": "BAD_JSON", "body": body}

    # ----------------------------------------------------------------------
    # SPECIAL: Your API returns ["", 204] for NO JOB
    # ----------------------------------------------------------------------
    if (
        isinstance(data, list)
        and len(data) == 2
        and data[1] == 204
    ):
        return {"status": "EMPTY"}

    # ----------------------------------------------------------------------
    # Normal paths: dict job, or list-of-dicts
    # ----------------------------------------------------------------------
    return {"status": "OK", "data": data}


# ---------------------------------------------------------------------------
# NORMALIZER
# ---------------------------------------------------------------------------

def normalize_job(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert raw API responses into a clean single job dict."""

    st = payload.get("status")

    if st == "EMPTY":
        return None

    if st == "BAD_TOKEN":
        log("invalid WORKER_TOKEN — worker cannot continue")
        time.sleep(2)
        return None

    if st == "NETWORK_ERROR":
        log(f"network error: {payload.get('error')}")
        time.sleep(1)
        return None

    if st == "BAD_JSON":
        log(f"non-JSON response from API: {payload.get('body')}")
        time.sleep(1)
        return None

    # status == OK
    data = payload.get("data")

    # dict → good job
    if isinstance(data, dict):
        return data

    # list → expected either [job] or garbage
    if isinstance(data, list):
        if len(data) == 0:
            return None

        first = data[0]

        if not isinstance(first, dict):
            log(f"first list item is not a dict: {first!r}")
            return None

        return first

    # unknown garbage
    log(f"weird API payload ignored: {data!r}")
    return None


# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

def process_job(job: Dict[str, Any]):
    """Placeholder processing logic."""
    jid = job.get("job_id", "unknown")
    log(f"processing job {jid}")

    # Simulated work
    time.sleep(1)

    # Normally you would POST results here


def main():
    log(f"start api={API_BASE} token='{WORKER_TOKEN}'")

    while True:
        payload = fetch_next_job()
        job = normalize_job(payload)

        if job is None:
            time.sleep(POLL_MS / 1000)
            continue

        # Ensure job_id exists
        if "job_id" not in job:
            log(f"job missing job_id: {job}")
            time.sleep(POLL_MS / 1000)
            continue

        process_job(job)
        time.sleep(POLL_MS / 1000)


if __name__ == "__main__":
    main()
