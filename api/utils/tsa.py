"""
TSA utilities for QuickDCP (fixed)

Provides small helpers around OpenSSL RFC-3161 tooling:
- build_tsq(sha_hex): generate a deterministic TSQ (DER) from a hex SHA-256
- verify_tsr(tsr_der, sha_hex, ca_pem=None): verify TSR matches TSQ for given digest
- extract_tsr_info(tsr_der): best-effort parse of human-readable fields
- ensure_openssl(): sanity check that openssl exists in PATH

These helpers are used by the proof router; they allow unit testing and
centralize OpenSSL error handling.
"""
from __future__ import annotations

import subprocess
import tempfile
from typing import Optional, Dict

class OpenSSLNotFound(RuntimeError):
    pass

class OpenSSLVerifyError(RuntimeError):
    pass


_checked = False

def ensure_openssl() -> None:
    """Raise OpenSSLNotFound if the openssl binary is not available."""
    global _checked
    if _checked:
        return
    try:
        subprocess.run(["openssl", "version"], check=True, capture_output=True)
    except FileNotFoundError as e:
        raise OpenSSLNotFound("openssl executable not found in PATH") from e
    except subprocess.CalledProcessError as e:
        raise OpenSSLNotFound(f"openssl error: {e}") from e
    _checked = True


def build_tsq(sha_hex: str) -> bytes:
    """Return TSQ (DER) for a manifest hex SHA-256.

    This uses -no_nonce and includes cert chain request for better portability.
    """
    ensure_openssl()
    try:
        return subprocess.check_output([
            "openssl", "ts", "-query",
            "-sha256", "-digest", sha_hex,
            "-cert", "-no_nonce", "-outform", "DER",
        ])
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"openssl ts -query failed: {e}") from e


def verify_tsr(tsr_der: bytes, sha_hex: str, ca_pem: Optional[str] = None) -> None:
    """Verify a TSR against a TSQ rebuilt from sha_hex. Raises on failure."""
    ensure_openssl()
    with tempfile.TemporaryDirectory() as d:
        tsr_p = f"{d}/resp.tsr"
        tsq_p = f"{d}/req.tsq"
        with open(tsr_p, "wb") as f:
            f.write(tsr_der)
        tsq = build_tsq(sha_hex)
        with open(tsq_p, "wb") as f:
            f.write(tsq)
        cmd = ["openssl", "ts", "-verify", "-in", tsr_p, "-queryfile", tsq_p]
        if ca_pem:
            ca_p = f"{d}/tsa.pem"
            with open(ca_p, "w", encoding="utf-8") as f:
                f.write(ca_pem)
            cmd.extend(["-CAfile", ca_p])
        try:
            out = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as e:
            raise OpenSSLNotFound("openssl executable not found in PATH") from e
        if out.returncode != 0:
            raise OpenSSLVerifyError(out.stderr.strip() or out.stdout.strip() or "verify failed")


def extract_tsr_info(tsr_der: bytes) -> Dict[str, str]:
    """Return a best-effort info dict from a TSR (serial, policy, time, etc.).

    This parses the human-readable text output of openssl ts -reply -text.
    If parsing fails, returns an empty dict.
    """
    ensure_openssl()
    info: Dict[str, str] = {}
    with tempfile.NamedTemporaryFile(suffix=".tsr") as f:
        f.write(tsr_der)
        f.flush()
        try:
            out = subprocess.check_output([
                "openssl", "ts", "-reply", "-in", f.name, "-text", "-token_in"
            ], text=True)
        except subprocess.CalledProcessError:
            return info
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Serial number:"):
            info["serial"] = s.split(":", 1)[-1].strip()
        elif s.startswith("Time stamp: "):
            info["time"] = s.split(":", 1)[-1].strip()
        elif s.startswith("Policy OID:"):
            info["policy"] = s.split(":", 1)[-1].strip()
        elif s.startswith("Nonce:"):
            info["nonce"] = s.split(":", 1)[-1].strip()
    return info


if __name__ == "__main__":  # minimal self-test for presence
    try:
        ensure_openssl()
        print("openssl ok")
    except Exception as e:
        print("openssl missing:", e)
