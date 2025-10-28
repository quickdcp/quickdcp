from __future__ import annotations
"""
QuickDCP main FastAPI application (final, fixed)
- Auth enforced on protected routers
- Paths aligned with SDK/CLI (/upload, /jobs, /proof, /kdm)
- Public /verify router
- CORS + basic metrics middleware
- Startup environment checks
- Safe file logging
"""

import os
import json
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api.routes.jobs import router as jobs_router
from api.routes.upload_stream import router as upload_router
from api.routes.proof import router as proof_router
from api.routes.kdm import router as kdm_router
from api.routes.verify import router as verify_router
from api.utils.auth import require_auth
from api import startup_check

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
PUBLIC = os.path.join(ROOT, "public")
LOGS = os.path.join(ROOT, "logs")
os.makedirs(LOGS, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
nowz = lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def log(evt: dict) -> None:
    try:
        with open(os.path.join(LOGS, "app.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    except Exception:
        # logging must never crash the API
        pass

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="QuickDCP - Complete", version="1.0.0")
startup_check.run()

# CORS (relaxed for MVP; tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static site (docs/tools/public assets)
if os.path.exists(PUBLIC):
    app.mount("/public", StaticFiles(directory=PUBLIC), name="public")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def root():
    idx = os.path.join(PUBLIC, "index.html")
    if os.path.exists(idx):
        return open(idx, "r", encoding="utf-8").read()
    return "<h1>QuickDCP API</h1>"

@app.get("/health")
def health():
    return {"ok": True, "ts": nowz(), "kill": os.environ.get("KILL", "0")}

# Protected routers (require headers: X-QD-Customer, Authorization: "QuickDCP <key>")
app.include_router(upload_router, prefix="/upload", tags=["upload"], dependencies=[Depends(require_auth)])
app.include_router(jobs_router,   prefix="/jobs",   tags=["jobs"],   dependencies=[Depends(require_auth)])
app.include_router(proof_router,  prefix="/proof",  tags=["proof"],  dependencies=[Depends(require_auth)])
app.include_router(kdm_router,    prefix="/kdm",    tags=["kdm"],    dependencies=[Depends(require_auth)])

# Public verification (no auth)
app.include_router(verify_router, prefix="/verify", tags=["verify"]) 

# ---------------------------------------------------------------------------
# Basic metrics (JSON; replace with Prometheus in production)
# ---------------------------------------------------------------------------
METRICS = {"jobs_ok": 0, "jobs_fail": 0}

@app.middleware("http")
async def _metrics_mv(request: Request, call_next):
    resp = await call_next(request)
    if request.method == "POST" and request.url.path.startswith("/jobs"):
        if 200 <= resp.status_code < 300:
            METRICS["jobs_ok"] += 1
        else:
            METRICS["jobs_fail"] += 1
    return resp

@app.get("/metrics")
def metrics():
    return METRICS

# ---------------------------------------------------------------------------
# Uvicorn entry
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
