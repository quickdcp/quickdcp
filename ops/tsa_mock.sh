#!/usr/bin/env bash
set -euo pipefail

# Create mock TSA keypair + certificate (DEV ONLY)
openssl genrsa -out tsa.key 2048
openssl req -new -x509 -key tsa.key -out tsa.crt -subj "/CN=QuickDCP Mock TSA" -days 3650

SHA="$1"  # hex sha256 of manifest

# Build TSQ deterministically
openssl ts -query \
  -sha256 \
  -digest "$SHA" \
  -cert \
  -no_nonce \
  -outform DER \
  -out req.tsq

# Sign TSQ -> produce TSR
openssl ts -reply \
  -queryfile req.tsq \
  -signer tsa.crt \
  -inkey tsa.key \
  -token_out \
  -out resp.tsr

# Verify locally (sanity check)
openssl ts -verify \
  -in resp.tsr \
  -queryfile req.tsq \
  -CAfile tsa.crt

echo "TSA mock OK"
