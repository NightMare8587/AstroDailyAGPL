"""Per-client rate limiting (sliding window, in memory).

State lives in this process, which is correct for a single Railway instance. If the service is
scaled to several replicas the limits apply per replica; move the counters to Redis then.
"""
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

from .config import Settings, get_settings

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque[float]] = {}
_MAX_KEYS = 50_000
_calls = 0


def reset() -> None:
    with _lock:
        _hits.clear()


def client_ip(request: Request, settings: Settings) -> str:
    """The caller's IP. Behind Railway's proxy the last X-Forwarded-For entry is the one the
    proxy itself appended, so it cannot be forged by the client; earlier entries can."""
    hops = settings.proxy_hops()
    forwarded = request.headers.get("x-forwarded-for")
    if hops and forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return request.client.host if request.client else "unknown"


def _check(scope: str, key: str, limit: int, window: float, now: float) -> float | None:
    """Record a hit. Returns None if allowed, else seconds until the next slot frees up."""
    global _calls
    with _lock:
        _calls += 1
        if _calls % 1000 == 0 or len(_hits) > _MAX_KEYS:
            stale = [k for k, q in _hits.items() if not q or q[-1] <= now - window]
            for k in stale:
                del _hits[k]
        q = _hits.setdefault((scope, key), deque())
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            return max(q[0] + window - now, 0.0)
        q.append(now)
        return None


def limit(scope: str, per_minute_attr: str):
    """FastAPI dependency factory: limit(scope, name of the Settings field holding requests/minute)."""
    def dependency(request: Request) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        per_minute = getattr(settings, per_minute_attr)
        wait = _check(scope, client_ip(request, settings), per_minute, 60.0, time.monotonic())
        if wait is not None:
            retry = int(wait) + 1
            raise HTTPException(
                status_code=429, detail="Too many requests. Please slow down.",
                headers={"Retry-After": str(retry)},
            )
    return dependency
