# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Structured logging functions for recording application events and errors."""

import json
import traceback
from typing import Any

from ..config.log import log_config
from ..data_model.log import LogMessage
from ..tools.function_name import extract_caller_name
from ..tools.json_encoder import PydanticJsonEncoder
from . import logger


def _create_and_log_message(
    msg: str,
    log_level: Any = logger.logging.info,
    body: Any = None,
    error: Exception | None = None,
) -> dict[str, Any]:
    """Create a structured log message and log it at the specified level.

    Internal function that creates a LogMessage with function context,
    optional body data, and error information, then logs it.

    Args:
        msg: Primary log message
        log_level: Logging function to use (debug, info, warning, error)
        body: Optional additional data to include in the log
        error: Optional exception to include with error details

    Returns:
        Dictionary representation of the logged message
    """
    try:
        log_str = json.loads(json.dumps(body, cls=PydanticJsonEncoder))
    except Exception as e:
        log_str = f"Can't convert body to json: {repr(e)}"

    # Create structured log message with function context
    message_data = LogMessage(
        msg=msg,
        func_name=extract_caller_name(full_chain=True, max_depth=5),
        body=log_str,
    )

    # Add error information if exception provided
    if error is not None:
        message_data.error_message = repr(error)
        message_data.stack_message = traceback.format_exc()

    # Convert to dictionary and log at specified level
    message_dump = message_data.model_dump(exclude_none=True)
    log_level(message_dump)
    return message_dump


def record_debug_log(msg: str, body: Any = None) -> dict[str, Any]:
    """Record a debug-level log message.

    Args:
        msg: Debug message to log
        body: Optional additional data to include

    Returns:
        Dictionary representation of the logged message
    """
    return _create_and_log_message(msg, logger.logging.debug, body)


def record_log(msg: str, body: Any = None) -> dict[str, Any]:
    """Record an info-level log message.

    Default logging function for general application events.

    Args:
        msg: Information message to log
        body: Optional additional data to include

    Returns:
        Dictionary representation of the logged message
    """
    return _create_and_log_message(msg, body=body)


def record_warning_log(msg: str, body: Any = None) -> dict[str, Any]:
    """Record a warning-level log message.

    Used for non-critical issues that should be noted but don't prevent operation.

    Args:
        msg: Warning message to log
        body: Optional additional data to include

    Returns:
        Dictionary representation of the logged message
    """
    return _create_and_log_message(msg, logger.logging.warning, body)


def record_error_log(
    msg: str, e: Exception | None = None, body: Any = None
) -> dict[str, Any]:
    """Record an error-level log message with optional exception details.

    Used for error conditions that need attention. Includes full stack trace
    and exception information when an exception is provided.

    Args:
        msg: Error message to log
        e: Optional exception that caused the error
        body: Optional additional data to include

    Returns:
        Dictionary representation of the logged message with error details
    """
    return _create_and_log_message(msg, logger.logging.error, body, e)


def record_agui_raw_log(raw_data: Any) -> None:
    """Record raw AGUI event data for debugging purposes.

    Conditionally logs AGUI events based on LOG_AGUI configuration setting.
    Used for debugging and development to trace AGUI event flow.

    Args:
        raw_data: Raw AGUI event data to log
    """
    if log_config.LOG_AGUI_EVENTS:
        _create_and_log_message("[RAW_DATA: AGUI] record AGUI raw log", body=raw_data)


def record_event_raw_log(raw_data: Any) -> None:
    """Record raw ADK event data for debugging purposes.

    Conditionally logs ADK events based on LOG_EVENT configuration setting.
    Used for debugging and development to trace ADK event processing.

    Args:
        raw_data: Raw ADK event data to log
    """
    if log_config.LOG_ADK_EVENTS:
        _create_and_log_message("[RAW_DATA: EVENT] record EVENT raw log", body=raw_data)
