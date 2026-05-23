import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import get_logger

logger = get_logger(__name__)

WINDOW_SECONDS = 60


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        window_start = now - self.window_seconds
        requests = self._requests[key]

        while requests and requests[0] <= window_start:
            requests.popleft()

        if len(requests) >= self.limit:
            retry_after = max(1, int(self.window_seconds - (now - requests[0])))
            return False, retry_after

        requests.append(now)
        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        requests_per_minute: int,
        protected_prefixes: Iterable[str],
    ) -> None:
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(limit=requests_per_minute)
        self.protected_prefixes = tuple(protected_prefixes)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not request.url.path.startswith(self.protected_prefixes):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        key = authorization.removeprefix("Bearer ").strip()
        if not key:
            key = request.client.host if request.client else "anonymous"

        allowed, retry_after = self.limiter.check(key)
        if not allowed:
            logger.warning(
                "rate_limited | path=%s retry_after=%ss",
                request.url.path,
                retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={"data": None, "error": "Rate limit exceeded.", "message": None},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
