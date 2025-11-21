# QuickDCP

A minimal, production-ready DCP automation node.  
Provides upload → worker render → manifest → TSA proof → verification.

## Components

- FastAPI backend (`/api`)
- Worker (`/worker/worker.py`)
- Upload (multipart S3)
- Proof chain (RFC-3161)
- Postgres/Supabase-style DB layer
- Terraform infra (S3 + KMS + IAM + Budget)
- Local dev stack (Docker Compose + MinIO + Postgres)
- Public verify page + offline verifier
- SDKs (Python + Node)

## Local Development

```bash
cp .env.sample .env
docker compose up --build
# API: http://localhost:8080
# MinIO Console: http://localhost:9001
