from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from commerce_hub.bootstrap.logging import trace_id


class ApiError(Exception):
    def __init__(self, code: str, status: int, message: str, *, retryable=False, details=None):
        self.code, self.status, self.message = code, status, message
        self.retryable, self.details = retryable, details


def error_response(code: str, status: int, message: str, *, details=None, retryable=False):
    current = trace_id.get() or uuid4().hex
    return JSONResponse(status_code=status, content={"code": code, "message": message, "details": details,
                                                    "traceId": current, "retryable": retryable},
                        headers={"X-Trace-Id": current, "Cache-Control": "no-store"})


def install_error_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def application_error(_: Request, exc: ApiError):
        return error_response(exc.code, exc.status, exc.message, details=exc.details, retryable=exc.retryable)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        messages = {401: ("UNAUTHENTICATED", "Authentication required"),
                    403: ("POLICY_DENIED", "Access denied"), 404: ("NOT_FOUND", "Resource unavailable"),
                    405: ("METHOD_NOT_ALLOWED", "Method not allowed"), 409: ("CONFLICT", "State conflict")}
        code, message = messages.get(exc.status_code, ("HTTP_ERROR", "Request could not be completed"))
        return error_response(code, exc.status_code, message)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, __: RequestValidationError):
        # Do not serialize exc.errors(): it can contain passwords, headers and request inputs.
        return error_response("INVALID_REQUEST", 422, "Invalid request parameters")
