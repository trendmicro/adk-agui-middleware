# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Error data models for HTTP error responses in AGUI middleware."""

import time
from typing import Any

from pydantic import BaseModel


class ErrorModel(BaseModel):
    """Model for error information in HTTP responses.

    Contains comprehensive error details including error type, description,
    timestamp, and optional trace ID for error tracking and debugging.
    Provides structured error information for client consumption and
    system monitoring.

    Attributes:
        error: Error type or category identifier
        error_description: Detailed error description (string or structured dict)
        timestamp: Unix timestamp when the error occurred (default: current time)
        trace_id: Optional trace identifier for error correlation across systems
    """

    error: str
    error_description: dict[str, Any] | str
    timestamp: int = int(time.time())
    trace_id: str = ""


class ErrorResponseModel(BaseModel):
    """HTTP error response model following FastAPI conventions.

    Wraps ErrorModel in a 'detail' field as expected by FastAPI
    error handling mechanisms. This standardized format ensures
    consistent error responses across all API endpoints and enables
    proper error handling by client applications.

    Attributes:
        detail: ErrorModel containing the complete error information
    """

    detail: ErrorModel
