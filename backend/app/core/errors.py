"""Error envelope, AppError, exception handlers and IntegrityError -> error-code mapping (plan 4.2)."""

import logging
import re
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


# ---- convenience constructors -------------------------------------------------------------------
def bad_request(message: str = "Bad request", code: str = "BAD_REQUEST", details=None) -> AppError:
    return AppError(400, code, message, details)


def unauthenticated(message: str = "Authentication required", code: str = "UNAUTHENTICATED") -> AppError:
    return AppError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


def forbidden(message: str = "You do not have permission to perform this action", code: str = "FORBIDDEN") -> AppError:
    return AppError(403, code, message)


def not_found(message: str = "Resource not found") -> AppError:
    return AppError(404, "NOT_FOUND", message)


def conflict(message: str, code: str = "CONFLICT", details=None) -> AppError:
    return AppError(409, code, message, details)


def unprocessable(message: str, code: str = "VALIDATION_ERROR", details=None) -> AppError:
    return AppError(422, code, message, details)


def rate_limited(retry_after: int) -> AppError:
    return AppError(
        429,
        "RATE_LIMITED",
        "Too many requests. Please try again later.",
        headers={"Retry-After": str(max(1, retry_after))},
    )


# ---- IntegrityError mapping ---------------------------------------------------------------------
# constraint name -> (status, code, message)
CONSTRAINT_ERRORS: dict[str, tuple[int, str, str]] = {
    "uq_users_email": (409, "DUPLICATE_EMAIL", "An account with this email already exists"),
    "uq_applications_student_internship": (
        409,
        "DUPLICATE_APPLICATION",
        "You have already applied to this internship",
    ),
    "uq_companies_registration_number": (
        409,
        "DUPLICATE_REGISTRATION_NUMBER",
        "A company with this registration number already exists",
    ),
    "uq_students_enrollment_no": (409, "CONFLICT", "This enrollment number is already registered"),
    "uq_faculty_employee_id": (409, "CONFLICT", "This employee id is already registered"),
    "uq_student_feedback_application_id": (409, "DUPLICATE_FEEDBACK", "Feedback has already been submitted"),
    "uq_company_feedback_application_author": (409, "DUPLICATE_FEEDBACK", "Feedback has already been submitted"),
    "uq_evaluations_application_evaluator_form": (
        409,
        "DUPLICATE_EVALUATION",
        "You have already evaluated this application with this form",
    ),
}

_CONSTRAINT_RE = re.compile(r'constraint "([^"]+)"')


def constraint_name_of(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    for c in (orig, getattr(orig, "__cause__", None)):
        name = getattr(c, "constraint_name", None)
        if name:
            return name
    m = _CONSTRAINT_RE.search(str(orig))
    return m.group(1) if m else None


def sqlstate_of(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    for c in (orig, getattr(orig, "__cause__", None)):
        code = getattr(c, "sqlstate", None) or getattr(c, "pgcode", None)
        if code:
            return code
    return None


def map_integrity_error(exc: IntegrityError) -> AppError:
    name = constraint_name_of(exc)
    if name and name in CONSTRAINT_ERRORS:
        status, code, message = CONSTRAINT_ERRORS[name]
        return AppError(status, code, message)
    state = sqlstate_of(exc)
    if state == "23514":  # check_violation
        return AppError(
            422,
            "VALIDATION_ERROR",
            f"Value violates constraint {name or 'check'}",
            [{"field": name or "", "message": "Invalid value"}],
        )
    if state == "23503":  # foreign_key_violation
        return AppError(409, "CONFLICT", "The operation conflicts with related data")
    if state == "23502":  # not_null_violation
        return AppError(422, "VALIDATION_ERROR", "A required value is missing")
    return AppError(409, "CONFLICT", "The request conflicts with existing data")


# ---- envelope + handlers ------------------------------------------------------------------------
def request_id_of(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def envelope(code: str, message: str, details: list[dict[str, str]] | None, request: Request) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if details:
        err["details"] = details
    rid = request_id_of(request)
    if rid:
        err["request_id"] = rid
    return {"error": err}


def app_error_response(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope(exc.code, exc.message, exc.details, request),
        headers=exc.headers,
    )


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return app_error_response(request, exc)


def _loc_to_field(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts)


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = []
    for e in exc.errors():
        msg = str(e.get("msg", "Invalid value"))
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        details.append({"field": _loc_to_field(tuple(e.get("loc", ()))), "message": msg})
    return JSONResponse(
        status_code=422,
        content=envelope("VALIDATION_ERROR", "Request validation failed", details, request),
    )


_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "BAD_REQUEST",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_CODES.get(exc.status_code, "INTERNAL_ERROR" if exc.status_code >= 500 else "BAD_REQUEST")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope(code, message, None, request),
        headers=getattr(exc, "headers", None),
    )


async def _integrity_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, IntegrityError)
    return app_error_response(request, map_integrity_error(exc))


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=envelope("INTERNAL_ERROR", "An unexpected error occurred", None, request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(IntegrityError, _integrity_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
