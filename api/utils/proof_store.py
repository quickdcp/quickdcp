"""
File-backed proof store for QuickDCP (fixed)

Responsibilities
----------------
- Persist minimal proof records per job_id as compact JSON.
- Provide atomic writes (temp file + replace) to avoid corruption.
- Lazy-create storage directory: <project>/jobs/proof/
- Tiny convenience helpers: load, save, init, exists, list_ids, delete.

Record shape (example)
----------------------
{
  "job_id": "JOB-123",
  "status": "PENDING" | "TSA_OK",
  "manifest_sha256": "...",
  "tsa_ok": true
}
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Resolve project root two levels up: api/utils -> project
ROOT = Path(__file__).resolve().parents[2]
PROOFD = ROOT / "jobs" / "proof"
PROOFD.mkdir(parents=True, exist_ok=True)


def _path(job_id: str) -> Path:
    return PROOFD / f"{job_id}.proof.json"


def exists(job_id: str) -> bool:
    return _path(job_id).exists()


def load(job_id: str) -> Optional[Dict]:
    p = _path(job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # If corrupted, treat as missing (callers can re-init)
        return None


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def save(job_id: str, record: Dict) -> None:
    p = _path(job_id)
    s = json.dumps(record, separators=(",", ":"))
    _atomic_write(p, s)


def init(job_id: str, manifest_sha256: str) -> Dict:
    rec = load(job_id) or {"job_id": job_id, "status": "PENDING"}
    rec["manifest_sha256"] = manifest_sha256
    save(job_id, rec)
    return rec


def list_ids() -> List[str]:
    out: List[str] = []
    for f in PROOFD.glob("*.proof.json"):
        out.append(f.stem.replace(".proof", ""))
    return sorted(out)


def delete(job_id: str) -> bool:
    p = _path(job_id)
    try:
        p.unlink(missing_ok=True)
        return True
    except Exception:
        return False


if __name__ == "__main__":  # basic self-test
    jid = "JOB-SELFTEST"
    init(jid, "abcd" * 16)
    rec = load(jid)
    assert rec and rec["manifest_sha256"].startswith("abcd")
    rec["tsa_ok"] = True
    rec["status"] = "TSA_OK"
    save(jid, rec)
    assert load(jid).get("tsa_ok") is True
    print("ids:", list_ids())
    delete(jid)
