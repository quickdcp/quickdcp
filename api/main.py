from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api import startup_check
from api.routes import billing, internal, kdm, proof, upload_stream, verify
from api.utils.db import DB


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


app = FastAPI(
    title="QuickDCP API",
    version="1.0.0",
    description="QuickDCP API for upload, job orchestration, proof chain, and verification.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Run startup checks once at import time (env, required files, etc.)
startup_check.run()

# CORS for local dev and basic cross-origin usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Standardize HTTPException into ErrorResponse
    payload = ErrorResponse(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        details=None,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Catch-all: log and wrap
    payload = ErrorResponse(
        code="INTERNAL_ERROR",
        message="Unexpected error",
        details={"type": exc.__class__.__name__},
    )
    return JSONResponse(
        status_code=500,
        content=payload.model_dump(),
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    # Basic health + DB connectivity check
    try:
        db = DB()
        with db.conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {"ok": True, "db": db_status}


# Router registration
app.include_router(upload_stream.router)
app.include_router(proof.router)
app.include_router(internal.router)
app.include_router(verify.router)
app.include_router(billing.router)
app.include_router(kdm.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "quickdcp", "status": "ok"}


if __name__ == "__main__":
    # This is what keeps the container alive when it runs `python -m api.main`
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )
