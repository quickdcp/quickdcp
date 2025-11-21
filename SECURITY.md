# Security Policy — QuickDCP

## Controls

- TLS 1.3 transport
- S3 Object Lock (COMPLIANCE mode)
- KMS-encrypted buckets (out / vault / logs)
- RFC-3161 TSA verification with deterministic TSQ
- Canonical JSON hashing (NFC + sorted keys)
- Worker-token–protected internal API
- API key auth (`X-QD-Customer` + `Authorization: QuickDCP <key>`)
- Postgres schema with row-level isolation (customer-scoped)
- Rate limiting (token bucket)
- Cost guard (per-job max from env)
- SBOM stored in vault

## Threats & Mitigations

### Credential theft
- No secrets in repo
- `.env` ignored by Git
- IAM keys rotated externally

### Output tampering
- Object Lock prevents overwrite/delete
- Manifest SHA256 anchored via TSA

### Fake proofs
- Deterministic TSQ generation
- TSA certificate optional CA-pinning
- Offline verify scripts

### Abuse / flooding
- Per-customer rate limiting
- Cost guard halts expensive profiles
- Worker isolation

### Data integrity loss
- Versioned buckets
- Immutable logs
- DB migration kept minimal and explicit

## Reporting

Security issues should be reported privately to the operator of the deployment running this instance.
