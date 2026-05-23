"""HTTP request / response logging middleware.

Logs every inbound request (method, path, client IP) and the resulting
response (status code, duration).  Sensitive headers are redacted.
"""

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)

_QUIET_PATHS = frozenset({"/health", "/openapi.json", "/docs", "/redoc"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request and its response with timing information."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "-")
        has_auth = "authorization" in request.headers

        # Use DEBUG for noisy infrastructure paths, INFO for everything else.
        is_quiet = path in _QUIET_PATHS
        log_fn = logger.debug if is_quiet else logger.info

        log_fn(
            "request_started  | %s %s | client=%s ua=%s auth=%s",
            method,
            path,
            client_ip,
            user_agent,
            has_auth,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed   | %s %s | duration=%.1fms",
                method,
                path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        log_fn(
            "request_finished | %s %s | status=%s duration=%.1fms",
            method,
            path,
            response.status_code,
            duration_ms,
        )

        return response
