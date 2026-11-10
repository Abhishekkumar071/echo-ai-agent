"""
Centralized exception types for ECHO.
All domain errors inherit from EchoError so handlers can catch them uniformly.
"""
from fastapi import HTTPException, status


class EchoError(Exception):
    """Base class for all application errors."""


class SessionNotFoundError(EchoError):
    """Raised when a session token is missing or expired."""


class ConversationNotFoundError(EchoError):
    """Raised when a conversation does not exist for the requesting user."""


class SearchUnavailableError(EchoError):
    """Raised when Tavily is unreachable or returns an error."""


class SearchTimeoutError(SearchUnavailableError):
    """Raised when Tavily call exceeds the configured timeout."""


class EmbeddingError(EchoError):
    """Raised when embedding generation fails. Memory row is still saved."""


class LLMError(EchoError):
    """Raised when the Gemini API call fails."""


# ── HTTP shortcuts ────────────────────────────────────────────────────────────

def http_401(detail: str = "Invalid or expired session") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def http_403(detail: str = "Access denied") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def http_404(detail: str = "Not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def http_500(detail: str = "Internal server error") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
    )
