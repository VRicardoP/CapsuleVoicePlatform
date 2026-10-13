"""Middleware for RGPD compliance, auditing, and security.

Implements:
- RGPD Art. 30: Processing activities logging
- RGPD Art. 32: Security measures
- RGPD Art. 33: Breach detection support
- LOPDGDD Art. 5: Confidentiality duty
- AI Act Art. 12: Traceability logging
"""

import logging as _logging
import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class _RequestIdFilter(_logging.Filter):
    """Inject ``request_id`` from structlog contextvars into stdlib LogRecords.

    This bridges the gap between structlog (used by middleware) and stdlib
    ``logging.getLogger(__name__)`` used by services, so that every log line
    carries the current request's correlation ID.
    """

    def filter(self, record: _logging.LogRecord) -> bool:
        ctx = structlog.contextvars.get_contextvars()
        record.request_id = ctx.get("request_id", "-")  # type: ignore[attr-defined]
        return True


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request auditing.

    Logs all API requests for RGPD compliance:
    - Request timestamp
    - Client IP (for security incident investigation)
    - User ID (if authenticated)
    - Endpoint accessed
    - Response status
    - Processing time

    This data supports:
    - RGPD Art. 30: Processing activities register
    - RGPD Art. 33: Security incident investigation
    - NIS2 Art. 21: Security event logging
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Install the filter once on the root logger so that every stdlib
        # logger (services, repositories) includes request_id automatically.
        root = _logging.getLogger()
        if not any(isinstance(f, _RequestIdFilter) for f in root.filters):
            root.addFilter(_RequestIdFilter())

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import structlog

        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract client IP (handle proxies)
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip

        # Bind request_id to all structlog entries in this request scope
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_ip=client_ip,
            path=request.url.path,
        )

        # Start timing
        start_time = time.perf_counter()

        # Process request
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time

            # Log successful request
            await self._log_request(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                status_code=response.status_code,
                process_time=process_time,
                user_id=getattr(request.state, "user_id", None),
            )

            # Add request ID (security headers set by SecurityHeadersMiddleware)
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            process_time = time.perf_counter() - start_time

            # Log failed request (potential security incident)
            await self._log_request(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                status_code=500,
                process_time=process_time,
                error=str(e),
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling reverse proxies.

        Only trusts X-Forwarded-For/X-Real-IP headers when the direct
        connection comes from a private/loopback IP (i.e. Traefik/Docker).
        """
        import ipaddress

        if request.client:
            direct_ip = request.client.host
            try:
                if ipaddress.ip_address(direct_ip).is_private:
                    forwarded = request.headers.get("X-Forwarded-For")
                    if forwarded:
                        return forwarded.split(",")[0].strip()
                    real_ip = request.headers.get("X-Real-IP")
                    if real_ip:
                        return real_ip
            except ValueError:
                pass
            return direct_ip

        return "unknown"

    async def _log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        client_ip: str,
        status_code: int,
        process_time: float,
        user_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Log request for audit trail."""
        log_data = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "status_code": status_code,
            "process_time_ms": round(process_time * 1000, 2),
        }

        if user_id:
            log_data["user_id"] = user_id

        if error:
            log_data["error"] = error
            logger.error("Request failed", **log_data)
        elif status_code >= 400:
            logger.warning("Request error", **log_data)
        else:
            logger.info("Request completed", **log_data)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware.

    For production, use Redis-based rate limiting.

    This supports:
    - RGPD Art. 32: Security measures (prevent brute force)
    - NIS2 Art. 21: Access control
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._request_counts: dict[str, list[float]] = {}
        self._cleanup_counter = 0

    @staticmethod
    def _extract_client_ip(request: Request) -> str:
        """Extract client IP directly from request (independent of AuditMiddleware).

        Only trusts X-Forwarded-For/X-Real-IP headers when the direct
        connection comes from a private/loopback IP (i.e. Traefik/Docker).
        """
        if request.client:
            direct_ip = request.client.host
            try:
                import ipaddress

                if ipaddress.ip_address(direct_ip).is_private:
                    forwarded = request.headers.get("X-Forwarded-For")
                    if forwarded:
                        return forwarded.split(",")[0].strip()
                    real_ip = request.headers.get("X-Real-IP")
                    if real_ip:
                        return real_ip
            except ValueError:
                pass
            return direct_ip
        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._extract_client_ip(request)
        current_time = time.time()
        window_start = current_time - 60

        # Periodic cleanup of stale IPs to prevent memory leak
        self._cleanup_counter += 1
        if self._cleanup_counter >= 100:
            self._cleanup_counter = 0
            stale_ips = [
                ip
                for ip, timestamps in self._request_counts.items()
                if not timestamps or timestamps[-1] < window_start
            ]
            for ip in stale_ips:
                del self._request_counts[ip]

        # Get request history for this IP
        if client_ip not in self._request_counts:
            self._request_counts[client_ip] = []

        # Remove old entries
        self._request_counts[client_ip] = [
            t for t in self._request_counts[client_ip] if t > window_start
        ]

        # Check rate limit
        if len(self._request_counts[client_ip]) >= self.requests_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                requests=len(self._request_counts[client_ip]),
            )
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        # Record this request
        self._request_counts[client_ip].append(current_time)

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.

    Implements security best practices:
    - Content Security Policy
    - HSTS
    - No sniffing
    - Frame options
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Prevent browser caching of API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response
