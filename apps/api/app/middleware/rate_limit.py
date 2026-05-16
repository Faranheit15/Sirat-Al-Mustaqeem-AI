import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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
        protected_paths: Iterable[str],
    ) -> None:
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(limit=requests_per_minute)
        self.protected_paths = tuple(protected_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path not in self.protected_paths:
            response = await call_next(request)
            return response

        user = getattr(request.state, "user", None)
        user_id = getattr(user, "user_id", None)
        client_host = request.client.host if request.client else "anonymous"
        key = user_id if isinstance(user_id, str) else client_host
        allowed, retry_after = self.limiter.check(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response
