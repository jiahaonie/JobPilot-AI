"""Domain exceptions and their HTTP translation."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for errors that are safe to expose to an API client."""

    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ResourceNotFoundError(DomainError):
    """Raised when a requested domain resource does not exist."""

    status_code = 404


class LLMAnalysisError(DomainError):
    """Raised when an LLM-powered analysis cannot produce a valid result."""

    status_code = 503


class JobRequirementNotFoundError(DomainError):
    """Raised when matching against a job that has no stored analysis."""

    status_code = 404


class GroundingValidationError(DomainError):
    """Raised when an answer cites evidence outside the retrieval context."""

    status_code = 502


def register_exception_handlers(application: FastAPI) -> None:
    """Register consistent responses for domain-level failures."""

    @application.exception_handler(DomainError)
    async def handle_domain_error(
        _request: Request,
        exc: DomainError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
