import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.ip_utils import get_client_ip


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_secs: int) -> None:
        self.max_requests = max_requests
        self.window_secs = window_secs
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(self, key: str, now: float | None = None) -> tuple[bool, int]:
        now = now if now is not None else time.monotonic()
        q = self._hits[key]
        cutoff = now - self.window_secs
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.max_requests:
            retry_after = max(1, int(self.window_secs - (now - q[0])) + 1)
            return False, retry_after
        q.append(now)
        return True, 0

    def clear(self) -> None:
        self._hits.clear()


_global_ip_limiter = SlidingWindowLimiter(max_requests=120, window_secs=60)
_login_ip_limiter = SlidingWindowLimiter(max_requests=20, window_secs=60)
_run_cooldown_limiter = SlidingWindowLimiter(max_requests=1, window_secs=3)
_run_hourly_limiter = SlidingWindowLimiter(max_requests=120, window_secs=3600)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/health", "/"):
            return await call_next(request)

        ip = get_client_ip(request)
        if path == "/api/v1/auth/login" and request.method == "POST":
            allowed, retry = _login_ip_limiter.check_and_record(ip)
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": f"Juda ko'p so'rov. {retry} soniyadan keyin urinib ko'ring."},
                )

        allowed, retry = _global_ip_limiter.check_and_record(ip)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"So'rovlar limiti oshdi. {retry} soniyadan keyin urinib ko'ring."},
            )

        return await call_next(request)


def enforce_run_rate_limit(user_id: str) -> None:
    """Enforce per-user code run limits: 1 run per 3s and 120 runs per hour."""
    ok_cd, retry_cd = _run_cooldown_limiter.check_and_record(user_id)
    if not ok_cd:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Kod ishga tushirish uchun {retry_cd} soniya kuting.",
        )

    ok_hr, _ = _run_hourly_limiter.check_and_record(user_id)
    if not ok_hr:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Soatlik kod ishga tushirish limiti (120 ta) tugadi.",
        )
