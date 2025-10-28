#!/usr/bin/env python3
"""
QuickDCP uploader (fixed)

CLI tool to stream a large file to the QuickDCP API using S3 multipart uploads.
- Computes full-file SHA256
- Initiates multipart: POST /upload/init
- Presigns each part: POST /upload/part
- PUTs each part directly to S3 with x-amz-checksum-sha256
- Completes upload: POST /upload/complete
- Verifies with GET /upload/head

Examples
--------
python3 ops/qdcp_upload.py /path/to/movie.mov \
  --api http://localhost:8080 \
  --customer dev --key dev \
  --part-size 64
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import sys
import time
from typing import Dict, List

import requests

DEFAULT_PART_MB = int(os.getenv("QDCP_PART_MB", "64"))
TIMEOUT = (10, 300)  # (connect, read)


def sha256_file(path: str, block: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def checksum_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


def human(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or unit == "TB":
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n}B"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="QuickDCP multipart uploader")
    p.add_argument("path", help="file to upload")
    p.add_argument("--api", default=os.getenv("API", "http://localhost:8080"))
    p.add_argument("--customer", default=os.getenv("QD_CUSTOMER", "dev"))
    p.add_argument("--key", default=os.getenv("QD_KEY", "dev"))
    p.add_argument("--part-size", type=int, default=DEFAULT_PART_MB, help="part size in MB (default: env QDCP_PART_MB or 64)")
    p.add_argument("--verify", action="store_true", help="HEAD the object after completion")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    path = args.path
    if not os.path.isfile(path):
        print(json.dumps({"ok": False, "error": "file_not_found", "path": path}))
        return 1

    size = os.path.getsize(path)
    part_size = args.part_size * 1024 * 1024
    parts_total = max(1, math.ceil(size / part_size))

    headers = {
        "X-QD-Customer": args.customer,
        "Authorization": f"QuickDCP {args.key}",
    }

    print(f"[qdcp] hashing {path} ({human(size)}) …", file=sys.stderr)
    file_sha = sha256_file(path)

    # init
    print("[qdcp] init multipart …", file=sys.stderr)
    r = requests.post(
        f"{args.api}/upload/init",
        headers=headers,
        data={"filename": os.path.basename(path), "size": str(size), "sha256": file_sha},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    meta = r.json()
    upload_id = meta["upload_id"]
    key = meta["key"]

    # upload parts
    etags: List[Dict[str, int | str]] = []
    sent = 0
    part_no = 1
    t0 = time.time()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(part_size)
            if not chunk:
                break
            # presign url
            pr = requests.post(
                f"{args.api}/upload/part",
                headers=headers,
                data={"key": key, "upload_id": upload_id, "part_number": str(part_no)},
                timeout=TIMEOUT,
            )
            pr.raise_for_status()
            url = pr.json()["url"]

            # PUT to S3 with checksum header (base64 of binary sha256)
            chk = checksum_b64(chunk)
            for attempt in range(1, 5):
                try:
                    put = requests.put(url, data=chunk, headers={"x-amz-checksum-sha256": chk}, timeout=TIMEOUT)
                    if put.status_code in (200, 201):
                        break
                except Exception as e:
                    if attempt == 4:
                        raise
                time.sleep(0.5 * attempt)

            etag = put.headers.get("ETag", "").strip('"')
            if not etag:
                print(json.dumps({"ok": False, "error": "missing_etag", "part": part_no}), file=sys.stderr)
                return 2
            etags.append({"ETag": etag, "PartNumber": part_no})

            sent += len(chunk)
            elapsed = time.time() - t0
            rate = sent / elapsed if elapsed > 0 else 0
            pct = (sent / size * 100) if size else 100.0
            print(f"[qdcp] part {part_no}/{parts_total} uploaded — {pct:.1f}% @ {human(int(rate))}/s", file=sys.stderr)
            part_no += 1

    # complete
    print("[qdcp] complete multipart …", file=sys.stderr)
    cr = requests.post(
        f"{args.api}/upload/complete",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({"key": key, "upload_id": upload_id, "parts": etags}),
        timeout=TIMEOUT,
    )
    cr.raise_for_status()

    result = {"ok": True, "key": key, "sha256": file_sha, "size": size, "parts": len(etags)}

    if args.verify:
        try:
            hr = requests.get(f"{args.api}/upload/head", headers=headers, params={"key": key}, timeout=TIMEOUT)
            if hr.status_code == 200:
                result["head"] = hr.json()
        except Exception as e:
            result["head_error"] = str(e)

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.HTTPError as e:
        print(json.dumps({"ok": False, "error": "http", "status": e.response.status_code, "body": e.response.text}), file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(4)
