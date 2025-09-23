# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Request logging utilities for HTTP request and error tracking."""

import traceback
from typing import Any

from starlette.requests import Request

from ..data_model.log import LogMessage
from ..tools.function_name import extract_caller_name
from . import logger


async def record_request_error_log(request: Request, e: Exception) -> dict[str, Any]:
    """Log an HTTP request that resulted in an error with full context.

    Captures comprehensive error information including request details,
    exception information, stack trace, and function context for debugging.

    Args:
        request: HTTP request that caused the error
        e: Exception that occurred during request processing

    Returns:
        Dictionary containing the logged error message data
    """
    # Create comprehensive error log with request context
    error_message = LogMessage(
        msg="record request error log",
        func_name=extract_caller_name(full_chain=True, max_depth=5),
        error_message=repr(e),
        headers=dict(request.headers),
        request_body=(await request.body()).decode(),
        stack_message=traceback.format_exc(),
    )

    # Log the error and return the message data
    error_message_dump = error_message.model_dump()
    logger.logging.error(error_message_dump)
    return error_message_dump


async def record_request_log(request: Request) -> dict[str, Any]:
    """Log an incoming HTTP request with headers and body for audit trail.

    Records basic request information including headers, body content,
    and function context for request tracking and debugging.

    Args:
        request: HTTP request to log

    Returns:
        Dictionary containing the logged request message data
    """
    # Create request log message with basic request information
    message = LogMessage(
        msg="record request log",
        func_name=extract_caller_name(full_chain=True, max_depth=5),
        headers=dict(request.headers),
        request_body=(await request.body()).decode(),
    )

    # Log the request and return the message data
    message_dump = message.model_dump(exclude_none=True)
    logger.logging.info(message_dump)
    return message_dump
