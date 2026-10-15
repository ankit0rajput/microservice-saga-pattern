from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request


logger = logging.getLogger("ecommerce.middleware")


def add_request_middleware(app: FastAPI, service_name: str) -> None:
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id

        started_at = perf_counter()
        logger.info(
            "request.start service=%s method=%s path=%s request_id=%s",
            service_name,
            request.method,
            request.url.path,
            request_id,
        )

        response = await call_next(request)
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)

        response.headers["x-request-id"] = request_id
        response.headers["x-service-name"] = service_name
        response.headers["x-process-time-ms"] = str(elapsed_ms)

        logger.info(
            "request.end service=%s method=%s path=%s status=%s request_id=%s elapsed_ms=%s",
            service_name,
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            elapsed_ms,
        )
        return response
