#!/usr/bin/env bash
# QuickDCP offline TSR verification helper (fixed)
#
# Verifies an RFC-3161 timestamp response (TSR) against a manifest SHA-256.
# You can provide either a precomputed hex digest with --sha, or a JSON
# manifest with --manifest (in which case we compute the canonical SHA-256
# using a tiny embedded Python routine matching the API's normalization rules).
#
# Usage:
#   ops/verify_offline.sh --sha <HEX> --tsr resp.tsr [--ca tsa.crt]
#   ops/verify_offline.sh --manifest manifest.json --tsr resp.tsr [--ca tsa.crt]
#
# Exits 0 on success, non-zero otherwise. Prints a short report.

set -euo pipefail

SHA_HEX=""
MANIFEST=""
TSR=""
CAFILE=""
QUIET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sha) SHA_HEX="$2"; shift 2;;
    --manifest) MANIFEST="$2"; shift 2;;
    --tsr) TSR="$2"; shift 2;;
    --ca) CAFILE="$2"; shift 2;;
    -q|--quiet) QUIET=1; shift;;
    -h|--help)
      sed -n '1,40p' "$0"; exit 0;;
    *) echo "[ERR] unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "$TSR" ]]; then
  echo "[ERR] --tsr <file> is required" >&2
  exit 2
fi

if [[ -z "$SHA_HEX" && -z "$MANIFEST" ]]; then
  echo "[ERR] provide either --sha <HEX> or --manifest <file>" >&2
  exit 2
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "[ERR] openssl not found in PATH" >&2
  exit 3
fi

# Compute canonical SHA-256 from manifest if requested
if [[ -z "$SHA_HEX" ]]; then
  if [[ ! -f "$MANIFEST" ]]; then
    echo "[ERR] manifest not found: $MANIFEST" >&2
    exit 2
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERR] python3 is required to canonicalize manifest JSON" >&2
    exit 3
  fi
  SHA_HEX=$(python3 - "$MANIFEST" <<'PY'
import sys,json,hashlib,unicodedata
p=sys.argv[1]
obj=json.load(open(p,'r',encoding='utf-8'))

def norm(x):
  if isinstance(x,str): return unicodedata.normalize('NFC',x)
  if isinstance(x,list): return [norm(i) for i in x]
  if isinstance(x,dict): return {k:norm(v) for k,v in x.items()}
  return x
obj=norm(obj)
s=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
print(hashlib.sha256(s).hexdigest())
PY
)
fi

# Build TSQ in DER
REQ_TSQ=$(mktemp)
trap 'rm -f "$REQ_TSQ"' EXIT

if [[ $QUIET -eq 0 ]]; then
  echo "[info] manifest sha256: $SHA_HEX"
  echo "[info] building TSQ …"
fi

# Openssl ts -query will write DER to stdout; redirect to file
if ! openssl ts -query -sha256 -digest "$SHA_HEX" -cert -no_nonce -outform DER >"$REQ_TSQ"; then
  echo "[ERR] openssl ts -query failed" >&2
  exit 4
fi

# Verify TSR
if [[ $QUIET -eq 0 ]]; then
  echo "[info] verifying TSR against TSQ …"
fi

VERIFY_CMD=(openssl ts -verify -in "$TSR" -queryfile "$REQ_TSQ")
if [[ -n "$CAFILE" ]]; then
  VERIFY_CMD+=( -CAfile "$CAFILE" )
fi

if ! OUT=$("${VERIFY_CMD[@]}" 2>&1); then
  [[ $QUIET -eq 0 ]] && echo "$OUT"
  echo "[FAIL] TSA verify failed" >&2
  exit 5
fi

if [[ $QUIET -eq 0 ]]; then
  echo "[ok] TSA verify: PASS"
  echo "[info] TSR details:"; openssl ts -reply -in "$TSR" -text -token_in | sed 's/^/  /'
else
  echo "PASS"
fi
