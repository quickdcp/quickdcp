import time

BUCKETS = {}


def allow(key: str, rate: int = 5, per: int = 1):
    """
    Simple token-bucket rate limiter.
    - key: identifier (e.g. customer or route+customer)
    - rate: number of tokens refilled per `per` seconds
    - per: refill interval

    Returns True if allowed, False if limited.
    """
    now = int(time.time())
    bucket = BUCKETS.get(key, {"ts": now, "tokens": rate})

    elapsed = now - bucket["ts"]
    if elapsed > 0:
        # refill tokens
        bucket["tokens"] = min(rate, bucket["tokens"] + (elapsed * rate // per))
        bucket["ts"] = now

    if bucket["tokens"] > 0:
        bucket["tokens"] -= 1
        BUCKETS[key] = bucket
        return True

    BUCKETS[key] = bucket
    return False
