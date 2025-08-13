"""Structured logging functions for recording application events and errors."""

import json
import traceback
from typing import Any

from data_model.log import LogMessage
from loggers import logger
from tools.function_name import get_function_name
from tools.json_encoder import DataclassesEncoder


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
    # Create structured log message with function context
    message_data = LogMessage(
        msg=msg,
        func_name=get_function_name(full_chain=True, max_depth=5),
        body=json.loads(json.dumps(body, cls=DataclassesEncoder)),
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
