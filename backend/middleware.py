import json
import time
import uuid
from collections import defaultdict

from starlette.types import ASGIApp, Receive, Scope, Send


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

RATE_LIMITS = {
    "/api/auth": (10, 60),  # 10 requests per minute for auth
    "/api/orchestrate": (5, 60),  # 5 per minute for orchestration
    "/api/chat": (10, 60),  # 10 per minute for chat
    "default": (30, 60),  # 30 per minute for other endpoints
}

_RATE_LIMIT_BODY = json.dumps({"detail": "Too many requests. Please try again later."}).encode()


def _get_client_ip(scope: Scope) -> str:
    """Extract client IP from ASGI scope."""
    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


def _get_path(scope: Scope) -> str:
    """Extract path from ASGI scope."""
    return scope.get("path", "")


def _get_header_value(scope: Scope, name: str) -> str:
    """Extract header value from ASGI scope."""
    name_lower = name.lower().encode()
    for key, value in scope.get("headers", []):
        if key == name_lower:
            return value.decode()
    return ""


class RateLimitMiddleware:
    """Pure ASGI rate-limit middleware — avoids BaseHTTPMiddleware event loop issues in tests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = _get_path(scope)
        request_id = _get_header_value(scope, "x-request-id") or str(uuid.uuid4())[:12]

        if path.startswith("/api/"):
            client_ip = _get_client_ip(scope)
            matched = "default"
            for prefix in RATE_LIMITS:
                if path.startswith(prefix):
                    matched = prefix
                    break

            max_req, window = RATE_LIMITS[matched]
            if not rate_limiter.check(f"{client_ip}:{matched}", max_req, window):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 429,
                        "headers": [
                            [b"content-type", b"application/json"],
                            [b"retry-after", str(window).encode()],
                            [b"x-request-id", request_id.encode()],
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": _RATE_LIMIT_BODY})
                return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([b"x-request-id", request_id.encode()])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
