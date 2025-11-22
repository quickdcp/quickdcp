# QuickDCP Master Blueprint 2025

## 1. Core Subsystems
- API Gateway (FastAPI)
- Job Queue + Worker Cluster
- Vault (KDM, certificates, signatures)
- S3 Storage (Ingest, Out, Vault, Logs)
- Supabase/PG (state + audit)
- UI Static Pages
- SDKs (Python, Node, CLI)

## 2. Internal Flows
### Ingest Flow
upload → ingest job → worker → QC → proof-chain → out-bucket

### KDM Flow
request → batch-plan → sign → encrypt-per-key → deliver

### Proof Chain
hashes → signatures → chain manifest → audit log → customer export

## 3. Security Layers
- API keys
- Worker token HMAC
- Audit logs
- DB constraints
- KDM signature validation
- Zero-trust bucket policies

## 4. Deployment Layers
- Local Docker stack
- GHCR container build
- Fly.io / AWS ECS deploy
- Supabase migrations
- CDN public UI

## 5. Extensibility
- Future: AI QC, HDR transforms, IMF ingest, cloud render nodes, festival batch verification.
