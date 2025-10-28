"""
Manifest utilities for QuickDCP (fixed)

Goals
-----
- Produce a deterministic, canonical JSON byte representation of any manifest
  (NFC-normalized strings, sorted object keys, minimal separators).
- Compute a stable SHA-256 digest over that canonical form.
- Provide lightweight helpers for equality and sanitation.

These rules must NOT reorder lists; array order is preserved intentionally so
operators can see the real sequence of outputs/KDMs.
"""
from __future__ import annotations

import json
import hashlib
import unicodedata
from typing import Any

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize(value: Any) -> Any:
    """Recursively normalize strings to NFC and descend into lists/dicts.

    We do not change list order and we do not coerce types; the goal is only to
    remove Unicode composition variance and ensure nested structures are
    normalized prior to canonical serialization.
    """
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        # Normalize values; keys are used as-is and sorted later by the dumper.
        return {k: _normalize(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------------------
# Canonicalization
# ---------------------------------------------------------------------------

def canonical_manifest_bytes(obj: Any, *, ensure_ascii: bool = False) -> bytes:
    """Return canonical JSON bytes for `obj`.

    - NFC-normalize all strings recursively
    - Sort object keys (stable ordering)
    - Use minimal separators to avoid whitespace variance
    - Keep list order as-is
    """
    obj = _normalize(obj)
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=ensure_ascii,
    ).encode("utf-8")


def sha256_manifest(obj: Any) -> str:
    """Return hex SHA-256 of the canonical manifest bytes."""
    return hashlib.sha256(canonical_manifest_bytes(obj)).hexdigest()


def canonical_equal(a: Any, b: Any) -> bool:
    """True if two objects are canonically identical (byte-wise)."""
    return canonical_manifest_bytes(a) == canonical_manifest_bytes(b)


def sanitize(obj: Any) -> Any:
    """Return a safe-to-serialize copy (currently just normalization hook).

    Useful before storing to disk or sending across the wire.
    """
    return _normalize(obj)


if __name__ == "__main__":  # simple self-checks
    sample = {"b": ["e\u0301", "x"], "a": "cafe\u0301"}  # decomposed accents
    bytes1 = canonical_manifest_bytes(sample)
    bytes2 = canonical_manifest_bytes({"a": "café", "b": ["é", "x"]})
    assert bytes1 == bytes2
    print("canonical sha256:", sha256_manifest(sample))
    print("equal:", canonical_equal(sample, {"a": "café", "b": ["é", "x"]}))
