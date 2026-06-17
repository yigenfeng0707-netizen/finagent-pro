import json
import os
import time
import uuid
from collections import defaultdict

from loguru import logger
from starlette.types import ASGIApp, Receive, Scope, Send


class InMemoryRateLimiter:
    """单机内存限流器 — 适用于单worker或测试环境"""

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


class RedisRateLimiter:
    """Redis sorted-set 滑动窗口限流器 — 适用于多worker共享限流状态

    当 Redis 不可用时自动降级为 InMemoryRateLimiter，确保服务不中断。
    """

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._pool = None
        self._fallback = InMemoryRateLimiter()
        self._redis_available: bool | None = None  # None = 尚未检测

    async def _get_redis(self):
        if self._pool is None:
            import redis.asyncio as aioredis

            self._pool = aioredis.from_url(
                self._redis_url,
                socket_connect_timeout=2,
                socket_timeout=3,
                decode_responses=True,
            )
            # 验证连接
            await self._pool.ping()
            self._redis_available = True
            logger.info("Redis 限流器已连接")
        return self._pool

    async def _ensure_pool(self):
        """归还连接池资源（redis-py async 自动管理，此处仅做占位）"""
        pass

    async def check_async(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """异步限流检查，Redis 不可用时自动降级到内存"""
        try:
            r = await self._get_redis()
        except Exception:
            if self._redis_available is not False:
                logger.warning("Redis 限流器不可用，降级为内存限流")
                self._redis_available = False
            return self._fallback.check(key, max_requests, window_seconds)

        try:
            redis_key = f"ratelimit:{key}"
            now = time.time()
            cutoff = now - window_seconds

            # 移除窗口外的旧记录
            await r.zremrangebyscore(redis_key, 0, cutoff)
            # 统计当前窗口内的请求数
            count = await r.zcard(redis_key)

            if count >= max_requests:
                return False

            # 添加新请求（member 必须唯一，使用 timestamp+uuid 片段）
            member = f"{now:.6f}:{uuid.uuid4().hex[:8]}"
            await r.zadd(redis_key, {member: now})
            await r.expire(redis_key, window_seconds * 2)
            return True

        except Exception:
            logger.warning("Redis 限流操作失败，降级为内存限流")
            return self._fallback.check(key, max_requests, window_seconds)


# ---------------------------------------------------------------------------
# 模块级单例 — 保持向后兼容 (conftest.py 访问 rate_limiter.windows)
# ---------------------------------------------------------------------------
rate_limiter = InMemoryRateLimiter()

# Redis 限流器（多worker时使用，懒初始化）
_redis_limiter: RedisRateLimiter | None = None


def _get_redis_limiter() -> RedisRateLimiter | None:
    """获取 Redis 限流器实例（仅当 REDIS_URL 配置时启用）"""
    global _redis_limiter
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    if _redis_limiter is None:
        _redis_limiter = RedisRateLimiter(redis_url)
    return _redis_limiter


RATE_LIMITS = {
    "/api/auth": (10, 60),  # 10 requests per minute for auth
    "/api/orchestrate": (5, 60),  # 5 per minute for orchestration
    "/api/chat": (10, 60),  # 10 per minute for chat
    "/ws/": (20, 60),  # 20 WebSocket connections per minute
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


def _is_websocket_upgrade(scope: Scope) -> bool:
    """检测是否为 WebSocket 升级请求"""
    return scope["type"] == "websocket"


class RateLimitMiddleware:
    """Pure ASGI rate-limit middleware — 支持 HTTP + WebSocket 限流，多worker共享 Redis 状态

    - HTTP 请求: 正常限流并注入 x-request-id 响应头
    - WebSocket 连接: 对 upgrade 请求进行限流，连接建立后透传
    - 多worker: 当 REDIS_URL 配置时使用 Redis sorted-set 共享限流窗口
    - 测试兼容: rate_limiter.windows.clear() 仍可用于重置内存状态
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path = _get_path(scope)
        request_id = _get_header_value(scope, "x-request-id") or str(uuid.uuid4())[:12]
        is_ws = _is_websocket_upgrade(scope)

        # 对 /api/ 和 /ws/ 路径执行限流
        should_check = path.startswith("/api/") or path.startswith("/ws/")
        if should_check:
            client_ip = _get_client_ip(scope)
            matched = "default"
            for prefix in RATE_LIMITS:
                if path.startswith(prefix):
                    matched = prefix
                    break

            max_req, window = RATE_LIMITS[matched]
            rate_key = f"{client_ip}:{matched}"

            # 优先使用 Redis 限流器（多worker场景）
            redis_rl = _get_redis_limiter()
            if redis_rl is not None:
                allowed = await redis_rl.check_async(rate_key, max_req, window)
            else:
                allowed = rate_limiter.check(rate_key, max_req, window)

            if not allowed:
                if is_ws:
                    # WebSocket: 发送 close frame
                    await send({"type": "websocket.close", "code": 1013, "reason": "Rate limit exceeded"})
                else:
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

        # WebSocket 连接: 限流通过后直接透传（无需注入 HTTP 响应头）
        if is_ws:
            await self.app(scope, receive, send)
            return

        # HTTP: 注入 x-request-id 响应头
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([b"x-request-id", request_id.encode()])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestTimingMiddleware:
    """记录请求耗时与状态码，便于生产环境可观测性排查。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()
        request_id = _get_header_value(scope, "x-request-id") or str(uuid.uuid4())[:12]
        path = _get_path(scope)
        method = scope.get("method", "")
        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.time() - start) * 1000, 2)
            level = "warning" if status_code >= 500 else "info"
            getattr(logger, level)(f"{method} {path} {status_code} {duration_ms}ms request_id={request_id}")
