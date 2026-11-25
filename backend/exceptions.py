"""
IoTSynth AI - Backend Centralized Exception Handling
Standardized application exceptions, RFC 7807-style error structures, and FastAPI handlers.
Guarantees zero physical path leakage and structured client error responses.
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class IoTSynthException(Exception):
    """Base exception for all IoTSynth AI domain and backend errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []


class ResourceNotFoundError(IoTSynthException):
    """Raised when an identified resource (device, profile, dataset, model) is missing."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        message = f"{resource_type} '{identifier}' was not found."
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidFeatureSchemaError(IoTSynthException):
    """Raised when an inference or evaluation payload does not match the 38 canonical features."""

    def __init__(
        self,
        missing_features: Optional[List[str]] = None,
        unexpected_features: Optional[List[str]] = None,
        details: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        missing = missing_features or []
        unexpected = unexpected_features or []
        message = (
            f"Feature schema mismatch. Missing features ({len(missing)}): {missing}. "
            f"Unexpected features ({len(unexpected)}): {unexpected}."
        )
        super().__init__(
            message=message,
            error_code="INVALID_FEATURE_SCHEMA",
            status_code=422,
            details=details,
        )


class JobExecutionError(IoTSynthException):
    """Raised when a background or batch asynchronous operation fails."""

    def __init__(self, job_id: str, reason: str) -> None:
        message = f"Asynchronous job '{job_id}' execution failed: {reason}"
        super().__init__(
            message=message,
            error_code="JOB_EXECUTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class BadRequestError(IoTSynthException):
    """Raised when client parameters violate domain validation constraints."""

    def __init__(self, message: str, details: Optional[List[Dict[str, Any]]] = None) -> None:
        super().__init__(
            message=message,
            error_code="BAD_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ModelNotLoadedError(IoTSynthException):
    """Raised when an ML inference request is made but model is not currently instantiated."""

    def __init__(self, model_id: str) -> None:
        message = (
            f"Model '{model_id}' is not loaded in memory. "
            f"Inference models are loaded on-demand via the Inference Service."
        )
        super().__init__(
            message=message,
            error_code="MODEL_NOT_LOADED",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class CapacityExceededError(IoTSynthException):
    """Raised when the background job queue capacity is saturated."""

    def __init__(self, message: str = "Background job queue capacity has been exceeded. Please retry later.") -> None:
        super().__init__(
            message=message,
            error_code="CAPACITY_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class ConflictError(IoTSynthException):
    """Raised when an operation conflicts with the current resource state."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )


def format_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Format standard RFC 7807-style error envelope without leaking paths or traces."""
    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "status_code": status_code,
        "details": details or [],
    }


async def iotsynth_exception_handler(
    request: Request, exc: IoTSynthException
) -> JSONResponse:
    """Handle domain-specific IoTSynthException instances."""
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle standard Pydantic and FastAPI request validation errors."""
    sanitized_errors = []
    for err in exc.errors():
        sanitized_errors.append(
            {
                "location": ".".join(str(loc) for loc in err.get("loc", [])),
                "issue": err.get("msg", "Validation error"),
                "type": err.get("type", "value_error"),
            }
        )
    return JSONResponse(
        status_code=422,
        content=format_error_response(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message="Request body or query parameters failed schema validation.",
            details=sanitized_errors,
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard Starlette / FastAPI HTTP exceptions (e.g. 404, 405)."""
    error_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "ENDPOINT_NOT_FOUND"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        error_code = "METHOD_NOT_ALLOWED"

    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            status_code=exc.status_code,
            error_code=error_code,
            message=str(exc.detail),
            details=[],
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled internal server exceptions."""
    # Never expose internal traceback or filesystem paths to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred during request processing.",
            details=[],
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers to the FastAPI app instance."""
    app.add_exception_handler(IoTSynthException, iotsynth_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
