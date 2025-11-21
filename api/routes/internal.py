from fastapi import APIRouter, HTTPException, Header
from typing import Optional
import os
from api.utils.db import DB

router = APIRouter(prefix="/internal", tags=["internal"])

db = DB()
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "dev-worker-token")


@router.post("/next-job")
def next_job(x_worker_token: Optional[str] = Header(None)):
    if x_worker_token != WORKER_TOKEN:
        raise HTTPException(401, "bad worker token")

    # NOTE:
    # For production, replace with SELECT ... FOR UPDATE SKIP LOCKED.
    # Here we just pick the first queued job.
    with db.conn.cursor() as cur:
        cur.execute(
            """
            select job_id, profile
            from jobs
            where status='QUEUED'
            order by created_at
            limit 1
            """
        )
        row = cur.fetchone()

        if not row:
            return ("", 204)

        job_id, profile = row

        # mark job as processing
        cur.execute(
            """
            update jobs
            set status='PROCESSING', updated_at=now()
            where job_id=%s
            """,
            (job_id,)
        )

        return {"job_id": job_id, "profile": profile}


@router.post("/update-job")
def update_job(body: dict, x_worker_token: Optional[str] = Header(None)):
    if x_worker_token != WORKER_TOKEN:
        raise HTTPException(401, "bad worker token")

    job_id = body.get("job_id")
    manifest = body.get("manifest")
    status = body.get("status", "PASS")

    if not job_id:
        raise HTTPException(400, "missing job_id")

    try:
        db.update_job(job_id, manifest, status)
    except Exception:
        raise HTTPException(404, "job not found")

    return {"ok": True}
