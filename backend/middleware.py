from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import time
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(self):
        self.windows: dict = defaultdict(lambda: defaultdict(list))

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        now = time.time()
        window_key = int(now / window_seconds)
        timestamps = self.windows[key][window_key]
        timestamps = [t for t in timestamps if now - t < window_seconds]
        self.windows[key][window_key] = timestamps
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
        return True


rate_limiter = InMemoryRateLimiter()


def get_client_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


RATE_LIMITS = {
    "/api/auth": (10, 60),       # 10 requests per minute for auth
    "/api/orchestrate": (5, 60),  # 5 per minute for orchestration
    "/api/chat": (10, 60),       # 10 per minute for chat
    "default": (30, 60),         # 30 per minute for other endpoints
}


async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        key = get_client_key(request)

        matched = "default"
        for prefix, limit in RATE_LIMITS.items():
            if request.url.path.startswith(prefix):
                matched = prefix
                break

        max_req, window = RATE_LIMITS[matched]
        if not rate_limiter.check(f"{key}:{matched}", max_req, window):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(window)},
            )

    response = await call_next(request)
    return response
