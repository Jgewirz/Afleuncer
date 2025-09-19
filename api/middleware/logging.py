"""
Request logging middleware with correlation ID and Prometheus metrics
"""
import time
import json
import uuid
from fastapi import Request, Response, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from lib.prometheus_metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_response_size_bytes,
    update_uptime
)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in request state for downstream use
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_seconds = time.time() - start_time
        duration_ms = duration_seconds * 1000

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Update Prometheus metrics
        endpoint = request.url.path
        method = request.method
        status = str(response.status_code)

        # Don't track metrics endpoint itself
        if endpoint != "/metrics":
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration_seconds)

            # Try to get response size
            content_length = response.headers.get("content-length")
            if content_length:
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(int(content_length))

        # Update uptime
        update_uptime()

        # Log request (JSON format for structured logging)
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "dur_ms": round(duration_ms, 2),
            "request_id": request_id
        }

        # Print as JSON line (can be picked up by log aggregators)
        print(json.dumps(log_data))

        return response


def install_logging(app: FastAPI):
    """Install the request logging middleware on the app"""
    app.add_middleware(RequestLoggingMiddleware)