"""Data model for structured log messages in AGUI middleware."""

from typing import Any

from pydantic import BaseModel


class LogMessage(BaseModel):
    """Structured log message model for consistent logging format.

    Contains all fields needed for comprehensive logging including context,
    error information, request details, and stack traces.
    """

    msg: str
    """Primary log message content."""

    func_name: str
    """Function name or call chain where the log originated."""

    error_message: str | None = None
    """String representation of any exception that occurred."""

    headers: dict[str, Any] | None = None
    """HTTP request headers when logging request-related events."""

    request_body: str | None = None
    """HTTP request body content for request logging."""

    body: Any | None = None
    """Additional structured data related to the log event."""

    stack_message: Any | None = None
    """Stack trace information when an exception occurred."""
