#!/usr/bin/env python3
"""
QuickDCP Worker

Polls the API for the next job, simulates processing, and posts back a manifest.

Env:
  API_BASE       = http://quickdcp-api:8080 (default inside Docker)
  WORKER_TOKEN   = dev  (must match API expected worker token)
  POLL_MS        = 1000 (poll interval in ms)
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, Optional

import requests


def env_str(key: str, default: str) -> str:
    v = os.getenv(key)
    return v if v else default


API_BASE = env_str("API_BASE", "http://quickdcp-api:8080")
WORKER_TOKEN = env_str("WORKER_TOKEN", "dev")
POLL_MS = int(os.getenv("POLL_MS", "1000"))


def log(msg: str) -> None:
    print(f"[worker] {msg}", flush=True)


def fetch_next_job(session: requests.Session) -> Dict[str, Any]:
    """
    Call /jobs/internal/next-job and normalize responses to a dict.

    Normalization rules:
      - 204 No Content              -> {"status": "EMPTY"}
      - empty body                  -> {"status": "EMPTY"}
      - non-2xx                     -> {"status": "ERROR", "code": ..., "body": ...}
      - JSON list -> we pass list up and normalize in caller
      - JSON dict -> returned as-is
    """
    url = f"{API_BASE.rstrip('/')}/jobs/internal/next-job"
    headers = {"x-worker-token": WORKER_TOKEN}

    try:
        resp = session.post(url, headers=headers, timeout=10)
    except requests.RequestException as exc:
        log(f"network error: {exc!r}")
        return {"status": "NETWORK_ERROR", "error": str(exc)}

    # No-content means no job
    if resp.status_code == 204:
        return {"status": "EMPTY"}

    # Unauthorized usually means bad worker token
    if resp.status_code == 401:
        log("HTTP 401 from API – bad worker token?")
        return {"status": "AUTH_ERROR", "code": 401}

    # Other non-OK codes
    if not resp.ok:
        body_preview = resp.text[:200].replace("\n", " ")
        log(f"HTTP {resp.status_code} error from API: {body_preview!r}")
        return {"status": "ERROR", "code": resp.status_code, "body": body_preview}

    # Some APIs send an empty 200 for "no job" – treat as EMPTY too
    if not resp.content or not resp.text.strip():
        return {"status": "EMPTY"}

    # Try to parse JSON; may be dict or list
    try:
        data: Any = resp.json()
    except ValueError:
        body_preview = resp.text[:200].replace("\n", " ")
        log(f"non-JSON 200 response from API: {body_preview!r}")
        return {"status": "ERROR", "body": body_preview}

    # We return raw JSON; caller will normalize list vs dict
    if isinstance(data, (dict, list)):
        return {"status": "OK", "data": data}

    # Unexpected JSON type
    return {"status": "ERROR", "body": f"unexpected JSON type: {type(data).__name__}"}


def simulate_job_work(jid: str) -> Dict[str, Any]:
    """
    Fake job processor – replace with real DCP work later.
    """
    log(f"processing job {jid} (simulated)")
    # simulate variable processing time
    time.sleep(1 + random.random())
    # return a stub manifest
    return {
        "job_id": jid,
        "status": "DONE",
        "frames_processed": random.randint(1000, 5000),
        "notes": "simulated worker run",
    }


def post_job_result(session: requests.Session, result: Dict[str, Any]) -> None:
    """
    POST the manifest back to the API (stub endpoint – adjust when backend is ready).
    """
    url = f"{API_BASE.rstrip('/')}/jobs/internal/job-result"
    headers = {
        "x-worker-token": WORKER_TOKEN,
        "content-type": "application/json",
    }

    try:
        resp = session.post(url, headers=headers, data=json.dumps(result), timeout=10)
    except requests.RequestException as exc:
        log(f"failed to POST job result: {exc!r}")
        return

    if not resp.ok:
        body_preview = resp.text[:200].replace("\n", " ")
        log(f"job result POST error HTTP {resp.status_code}: {body_preview!r}")
        return

    log(f"job result accepted for job {result.get('job_id')}")


def normalize_job_payload(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Take the normalized fetch_next_job() output and convert to a single job dict or None.

    Returns:
      - None if there is no job or we should skip this iteration
      - A dict representing a job otherwise
    """
    status = raw.get("status")

    # No job conditions
    if status in ("EMPTY", "NETWORK_ERROR", "AUTH_ERROR", "ERROR"):
        # We log details higher up but we treat them as "no job to process" here.
        return None

    if status != "OK":
        log(f"unexpected fetch status: {status!r} payload={raw!r}")
        return None

    data = raw.get("data")

    # API may return a single dict or a list of dicts
    if isinstance(data, list):
        if not data:
            return None
        first = data[0]
        if not isinstance(first, dict):
            log(f"first list item is not a dict: {first!r}")
            return None
        return first

    if isinstance(data, dict):
        return data

    log(f"unexpected data type in job payload: {type(data).__name__}")
    return None


def main() -> None:
    poll_sleep = POLL_MS / 1000.0
    log(f"start api={API_BASE} token={WORKER_TOKEN!r}")

    with requests.Session() as session:
        while True:
            raw = fetch_next_job(session)

            # Handle special statuses with logging and backoff
            status = raw.get("status")
            if status == "NETWORK_ERROR":
                time.sleep(3.0)
                continue
            if status == "AUTH_ERROR":
                # No point hammering the API if token is wrong
                log("auth error – check WORKER_TOKEN; backing off 10s")
                time.sleep(10.0)
                continue
            if status == "ERROR":
                log(f"API error payload: {raw!r}")
                time.sleep(3.0)
                continue

            job = normalize_job_payload(raw)

            if job is None:
                # Nothing to do this tick
                time.sleep(poll_sleep)
                continue

            jid = job.get("job_id")
            if not jid:
                log(f"job missing job_id: {job!r}")
                time.sleep(poll_sleep)
                continue

            # Process the job
            result = simulate_job_work(jid)

            # Try to POST result (endpoint may not exist yet; that's fine in dev)
            post_job_result(session, result)

            # Small delay before polling again
            time.sleep(poll_sleep)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("shutting down by KeyboardInterrupt")
