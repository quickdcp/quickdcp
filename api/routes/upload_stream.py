"""
QuickDCP upload router (fixed)
- S3 multipart upload: init, presign part URLs, complete
- Defaults to bucket from env S3_BUCKET_INGEST
- SHA256 checksum flow (client must send x-amz-checksum-sha256 when PUTting parts)
- Optional HEAD endpoint to verify final object exists

Auth is enforced by main.py include (require_auth).
"""
from __future__ import annotations

import os
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Form, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
BUCKET_INGEST = os.getenv("S3_BUCKET_INGEST", "quickdcp-ingest")
S3 = boto3.client("s3", region_name=REGION)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class InitRes(BaseModel):
    upload_id: str
    key: str
    size: int
    sha256: str

class PartSignRes(BaseModel):
    url: str

class CompletePart(BaseModel):
    ETag: str
    PartNumber: int

class CompleteReq(BaseModel):
    key: str
    upload_id: str
    parts: List[CompletePart]

class HeadRes(BaseModel):
    key: str
    exists: bool
    size: Optional[int] = None

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/init", response_model=InitRes)
def init_upload(
    filename: str = Form(...),
    size: int = Form(...),
    sha256: str = Form(...),
):
    """Start a multipart upload and return UploadId + object key.
    Client will PUT parts to presigned URLs with x-amz-checksum-sha256.
    """
    if not filename:
        raise HTTPException(400, "filename is required")
    key = f"ingest/{filename}"
    try:
        r = S3.create_multipart_upload(
            Bucket=BUCKET_INGEST,
            Key=key,
            ChecksumAlgorithm="SHA256",
        )
    except ClientError as e:
        raise HTTPException(500, f"s3 init failed: {e}")
    return InitRes(upload_id=r["UploadId"], key=key, size=size, sha256=sha256)


@router.post("/part", response_model=PartSignRes)
def sign_part(
    key: str = Form(...),
    upload_id: str = Form(...),
    part_number: int = Form(...),
):
    if not key or not upload_id or not part_number:
        raise HTTPException(400, "key, upload_id, and part_number are required")
    try:
        url = S3.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": BUCKET_INGEST,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": int(part_number),
                "ChecksumAlgorithm": "SHA256",
            },
            ExpiresIn=3600,
        )
    except ClientError as e:
        raise HTTPException(500, f"s3 presign failed: {e}")
    return PartSignRes(url=url)


@router.post("/complete")
async def complete(request: Request):
    try:
        data = CompleteReq(**(await request.json()))
    except Exception:
        raise HTTPException(400, "invalid JSON payload")

    try:
        S3.complete_multipart_upload(
            Bucket=BUCKET_INGEST,
            Key=data.key,
            UploadId=data.upload_id,
            MultipartUpload={"Parts": [p.model_dump() for p in data.parts]},
            ChecksumAlgorithm="SHA256",
        )
    except ClientError as e:
        raise HTTPException(500, f"s3 complete failed: {e}")
    return {"ok": True, "key": data.key}


@router.get("/head", response_model=HeadRes)
def head(key: str):
    """HEAD the object to confirm existence/size (post-complete)."""
    try:
        r = S3.head_object(Bucket=BUCKET_INGEST, Key=key)
        return HeadRes(key=key, exists=True, size=r.get("ContentLength"))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey"}:
            return HeadRes(key=key, exists=False)
        raise HTTPException(500, f"s3 head failed: {e}")
