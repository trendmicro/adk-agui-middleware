# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Data model for structured log messages in AGUI middleware."""

from typing import Any

from pydantic import BaseModel


class LogMessage(BaseModel):
    """Structured log message model for consistent logging format.

    Contains all fields needed for comprehensive logging including context,
    error information, request details, and stack traces. Provides a
    standardized structure for logging across the middleware system,
    enabling consistent log aggregation and analysis.

    This model supports both operational logging and debugging scenarios
    with structured fields for different types of log data.

    Attributes:
        msg: Primary log message content describing the event
        func_name: Function name or call chain where the log originated
        error_message: String representation of any exception that occurred
        headers: HTTP request headers when logging request-related events
        request_body: HTTP request body content for request logging
        body: Additional structured data related to the log event
        stack_message: Stack trace information when an exception occurred
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
