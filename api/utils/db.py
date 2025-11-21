import os
import json
import psycopg

DB_URL = os.getenv("DATABASE_URL")


class DB:
    def __init__(self):
        # Robust connection with retry: Postgres may not be ready when API starts
        import time
        from psycopg import OperationalError

        last_err = None
        for _ in range(30):
            try:
                self.conn = psycopg.connect(DB_URL, autocommit=True)
                last_err = None
                break
            except OperationalError as exc:
                last_err = exc
                time.sleep(1)

        if last_err is not None:
            # Give up after retries so the error is visible in logs
            raise last_err

    # ---------------------------------------------------------
    # CUSTOMER CONTEXT (for RLS)
    # ---------------------------------------------------------
    def set_customer(self, code: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "select set_config('qd.customer_code', %s, true)",
                (code,)
            )

    # ---------------------------------------------------------
    # JOBS
    # ---------------------------------------------------------
    def create_job(self, job_id: str, customer_code: str, profile: dict):
        with self.conn.cursor() as cur:
            self.set_customer(customer_code)
            cur.execute(
                """
                insert into jobs(job_id, customer_id, status, profile, manifest)
                values (
                    %s,
                    qd_customer_id(),
                    'QUEUED',
                    %s,
                    %s
                )
                on conflict(job_id)
                do update set profile = excluded.profile
                returning id
                """,
                (
                    job_id,
                    json.dumps(profile),
                    json.dumps({"job_id": job_id, "proof": {}})
                )
            )
            row = cur.fetchone()
            return row[0]

    def get_job(self, job_id: str, customer_code: str):
        with self.conn.cursor() as cur:
            self.set_customer(customer_code)
            cur.execute(
                "select id, status, profile, manifest from jobs where job_id=%s",
                (job_id,)
            )
            return cur.fetchone()

    def update_job(self, job_id: str, manifest: dict, status: str):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                update jobs
                set manifest=%s,
                    status=%s,
                    updated_at=now()
                where job_id=%s
                """,
                (json.dumps(manifest), status, job_id)
            )

    # ---------------------------------------------------------
    # PROOFS
    # ---------------------------------------------------------
    def proof_init(self, job_id: str, sha: str):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into proofs(job_id, manifest_sha256, status)
                select id, %s, 'PENDING'
                from jobs
                where job_id=%s
                on conflict(job_id)
                do update set
                    manifest_sha256 = excluded.manifest_sha256,
                    updated_at = now()
                """,
                (sha, job_id)
            )

    def proof_get(self, job_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select
                    p.status,
                    p.manifest_sha256,
                    p.tsa_ok,
                    p.fp_proof_id,
                    p.fp_verified
                from proofs p
                join jobs j on j.id = p.job_id
                where j.job_id=%s
                """,
                (job_id,)
            )
            row = cur.fetchone()
            if not row:
                return None

            return {
                "status": row[0],
                "manifest_sha256": row[1],
                "tsa_ok": row[2],
                "fp_proof_id": row[3],
                "fp_verified": row[4],
            }

    def proof_update_tsa_ok(self, job_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                update proofs
                set tsa_ok=true,
                    status='TSA_OK',
                    updated_at=now()
                where job_id = (
                    select id from jobs where job_id=%s
                )
                """,
                (job_id,)
            )

    def proof_update_fp(self, job_id: str, proof_id: str, verified: bool):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                update proofs
                set fp_proof_id=%s,
                    fp_verified=%s,
                    updated_at=now()
                where job_id = (
                    select id from jobs where job_id=%s
                )
                """,
                (proof_id, verified, job_id)
            )
