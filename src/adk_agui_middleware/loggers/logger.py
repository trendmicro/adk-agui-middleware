# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""JSON logging formatter and logger configuration for AGUI middleware."""

import json
import logging as log
from typing import Any

from ..config.log import log_config
from ..tools.json_encoder import PydanticJsonEncoder


class JsonFormatter(log.Formatter):
    """Custom JSON formatter for structured logging.

    Formats log records as JSON objects with configurable field mapping,
    timestamp formatting, and support for exception information.
    """

    def __init__(
        self,
        fmt_dict: dict[str, str] | None = None,
        time_format: str = "%Y-%m-%dT%H:%M:%S",
        msec_format: str = "%s.%03dZ",
        cls: type | None = None,
    ):
        """Initialize the JSON formatter.

        Args:
            :param fmt_dict: Mapping of JSON field names to LogRecord attributes
            :param time_format: Format string for timestamp formatting
            :param msec_format: Format string for millisecond precision
            :param cls: JSON encoder class for custom serialization
        """
        super().__init__()
        self.cls = cls
        self.fmt_dict = fmt_dict if fmt_dict is not None else {"message": "message"}
        self.default_time_format = time_format
        self.default_msec_format = msec_format
        self.datefmt = None

    def uses_time(self) -> bool:
        """Check if the formatter requires timestamp formatting.

        Returns:
            True if 'asctime' is used in the format dictionary
        """
        return "asctime" in self.fmt_dict.values()

    def _format_message(self, record: log.LogRecord) -> dict[str, Any]:
        """Format log record into a dictionary based on format configuration.

        Args:
            :param record: Log record to format

        Returns:
            Dictionary containing formatted log fields
        """
        message_dict = {}
        for fmt_key, fmt_val in self.fmt_dict.items():
            if hasattr(record, fmt_val):
                message_dict[fmt_key] = getattr(record, fmt_val)
        return message_dict

    def format(self, record: log.LogRecord) -> str:
        """Format a log record as a JSON string.

        Processes the log record to include timestamps, exception information,
        stack traces, and formats everything as a JSON object.

        Args:
            :param record: Log record to format

        Returns:
            JSON string representation of the log record
        """
        # Add timestamp if required
        if self.uses_time():
            record.asctime = self.formatTime(record, self.datefmt)

        # Build the base message dictionary
        message_dict = self._format_message(record)

        # Add exception information if present
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            message_dict["exc_info"] = record.exc_text

        # Add stack trace information if present
        if record.stack_info:
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        # Add the main message
        message_dict["message"] = record.msg

        # Serialize to JSON with custom encoder
        return json.dumps(message_dict, default=str, cls=self.cls, ensure_ascii=False)


def create_logger(name: str, fmt_dict: dict[str, str] | None = None) -> log.Logger:
    """Create a logger with JSON formatting and configured log level.

    Creates a logger instance with a stream handler that outputs JSON-formatted
    log messages. The log level is determined from configuration.

    Args:
        :param name: Name for the logger instance
        :param fmt_dict: Optional format dictionary for JSON field mapping

    Returns:
        Configured logger instance with JSON formatter
    """
    # Get and validate log level from configuration
    log_level = log_config.LOG_LEVEL.upper()
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level = "INFO"

    # Create logger and handler
    logger = log.getLogger(name)
    handler = log.StreamHandler()

    # Set log levels
    logger.setLevel(log_level)
    handler.setLevel(log_level)

    # Configure JSON formatter with dataclass encoder
    handler.setFormatter(
        JsonFormatter(
            fmt_dict=fmt_dict,
            cls=PydanticJsonEncoder,
        )
    )
    logger.addHandler(handler)

    return logger


# Create the default logger instance for the application
logging = create_logger(
    "generic",
    {
        "timestamp": "asctime",
        "level": "levelname",
    },
)
