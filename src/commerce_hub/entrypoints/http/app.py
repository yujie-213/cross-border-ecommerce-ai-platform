from contextlib import asynccontextmanager
import logging
import re
from uuid import uuid4

from fastapi import FastAPI

from commerce_hub import __version__
from commerce_hub.bootstrap.database import DatabaseReadiness
from commerce_hub.bootstrap.logging import configure_logger, trace_id
from commerce_hub.bootstrap.settings import Settings, load_settings
from commerce_hub.entrypoints.http.errors import error_response, install_error_handlers


class RequestBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = next((value.decode("ascii", errors="ignore") for key, value in scope["headers"] if key.lower() == b"x-trace-id"), "")
        current = supplied if re.fullmatch(r"[a-f0-9]{32}", supplied) else uuid4().hex
        token = trace_id.set(current)
        started = False
        status = 500

        async def safe_send(message):
            nonlocal started, status
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                message["headers"] = [(key, value) for key, value in message.get("headers", []) if key.lower() not in {b"x-trace-id", b"cache-control"}]
                message["headers"] += [(b"x-trace-id", current.encode()), (b"cache-control", b"no-store")]
            await send(message)

        logger = logging.getLogger("commerce_hub")
        try:
            await self.app(scope, receive, safe_send)
        except Exception:
            logger.error("", extra={"event": "request_failed"})
            if not started:
                await error_response("INTERNAL_ERROR", 500, "Internal service error")(scope, receive, safe_send)
            # Never rethrow raw exceptions to an HTTP server that may log credentials or inputs.
        finally:
            logger.info("", extra={"event": "request_completed", "status_code": status})
            trace_id.reset(token)


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else load_settings()
    logger = configure_logger(configuration.log_level)

    @asynccontextmanager
    async def lifespan(app):
        # Constructing an engine is lazy; startup performs no SQL, migration or background work.
        app.state.database = DatabaseReadiness(configuration)
        logger.info("", extra={"event": "application_started"})
        try:
            yield
        finally:
            app.state.database.close()
            logger.info("", extra={"event": "application_stopped"})

    app = FastAPI(title="Commerce Hub Foundation", version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None, debug=False)
    install_error_handlers(app)
    app.add_middleware(RequestBoundary)

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        connected = app.state.database.check()
        # A-03/A-04/A-05 and the Handler do not exist yet. Connectivity alone is never MVP readiness.
        components = {"database": "available" if connected else "unavailable", "persistence": "not_implemented",
                      "identity": "not_implemented", "worker": "not_implemented", "s01": "not_implemented"}
        return error_response("NOT_READY", 503, "Required capabilities are not ready", details=components, retryable=not connected)

    return app
