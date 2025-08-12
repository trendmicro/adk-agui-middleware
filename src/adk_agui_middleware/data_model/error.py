"""Error data models for HTTP error responses in AGUI middleware."""

import time
from typing import Any

from pydantic import BaseModel


class ErrorModel(BaseModel):
    """Model for error information in HTTP responses.

    Contains error details, description, timestamp, and optional trace ID
    for error tracking and debugging.
    """

    error: str
    error_description: dict[str, Any] | str
    timestamp: int = int(time.time())
    trace_id: str = ""


class ErrorResponseModel(BaseModel):
    """HTTP error response model following FastAPI conventions.

    Wraps ErrorModel in a 'detail' field as expected by FastAPI
    error handling mechanisms.
    """

    detail: ErrorModel
