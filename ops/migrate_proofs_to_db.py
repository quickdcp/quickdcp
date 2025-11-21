#!/usr/bin/env python3
import json
from pathlib import Path
from api.utils.db import DB


def run(root="jobs/proof"):
    db = DB()
    p = Path(root)

    if not p.exists():
        print("no legacy proofs found; skipping")
        return

    for f in p.glob("*.proof.json"):
        try:
            data = json.loads(f.read_text())

            job_id = data.get("job_id") or f.stem.replace(".proof", "")
            sha = data.get("manifest_sha256")

            if not sha:
                print(f"SKIP (no sha): {f.name}")
                continue

            # init / update DB record
            db.proof_init(job_id, sha)

            if data.get("tsa_ok"):
                db.proof_update_tsa_ok(job_id)

            if data.get("fp_proof_id"):
                db.proof_update_fp(
                    job_id,
                    data["fp_proof_id"],
                    bool(data.get("fp_verified"))
                )

            print("MIGRATED:", f.name)

        except Exception as e:
            print("ERR:", f, e)


if __name__ == "__main__":
    run()
