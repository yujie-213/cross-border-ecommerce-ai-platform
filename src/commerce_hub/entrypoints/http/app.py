from contextlib import asynccontextmanager
import logging
import re
from uuid import uuid4

from fastapi import FastAPI

from commerce_hub import __version__
from commerce_hub.bootstrap.database import DatabaseReadiness
from commerce_hub.bootstrap.logging import configure_logger, trace_id
from commerce_hub.bootstrap.settings import Settings, load_settings
from commerce_hub.bootstrap.composition import task_service
from commerce_hub.entrypoints.http.errors import error_response, install_error_handlers
from commerce_hub.entrypoints.http.tasks import register_task_routes


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
            request_receive = receive
            if scope.get("method") in {"POST", "PUT", "PATCH"}:
                chunks, size = [], 0
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > 65536:
                        await error_response("REQUEST_TOO_LARGE", 413, "Request body exceeds the configured limit")(scope, receive, safe_send)
                        return
                    chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
                buffered = b"".join(chunks)
                consumed = False
                async def request_receive():
                    nonlocal consumed
                    if not consumed:
                        consumed = True
                        return {"type": "http.request", "body": buffered, "more_body": False}
                    return await receive()
            await self.app(scope, request_receive, safe_send)
        except Exception:
            logger.error("", extra={"event": "request_failed"})
            if not started:
                await error_response("INTERNAL_ERROR", 500, "Internal service error")(scope, receive, safe_send)
            # Never rethrow raw exceptions to an HTTP server that may log credentials or inputs.
        finally:
            logger.info("", extra={"event": "request_completed", "status_code": status})
            trace_id.reset(token)


def create_app(settings: Settings | None = None, registry=None) -> FastAPI:
    configuration = settings if settings is not None else load_settings()
    logger = configure_logger(configuration.log_level)

    @asynccontextmanager
    async def lifespan(app):
        # Constructing an engine is lazy; startup performs no SQL, migration or background work.
        app.state.database = DatabaseReadiness(configuration)
        app.state.settings = configuration
        app.state.tasks = task_service(app.state.database, configuration, registry)
        logger.info("", extra={"event": "application_started"})
        try:
            yield
        finally:
            app.state.database.close()
            logger.info("", extra={"event": "application_stopped"})

    app = FastAPI(title="Commerce Hub Foundation", version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None, debug=False)
    install_error_handlers(app)
    register_task_routes(app)
    app.add_middleware(RequestBoundary)

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        connected = app.state.database.check()
        migrated = connected and configuration.auth_configured and app.state.database.schema_ready()
        components = {"database": "available" if connected else "unavailable", "persistence": "available" if migrated else "not_ready",
                      "identity": "configured" if configuration.auth_configured else "not_configured", "worker": "independent_process", "s01": "not_implemented"}
        if migrated:
            return {"status": "ready", "scope": "ENGINEERING_FOUNDATION_ONLY", "components": components}
        return error_response("NOT_READY", 503, "Required capabilities are not ready", details=components, retryable=not connected)

    return app
