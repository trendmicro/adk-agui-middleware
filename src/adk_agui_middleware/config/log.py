# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Logging configuration settings for AGUI middleware."""

from pydantic_settings import BaseSettings


class LogConfig(BaseSettings):
    """Configuration settings for application logging.

    Uses Pydantic BaseSettings to manage logging configuration with
    environment variable support and validation.
    """

    LOG_LEVEL: str = "INFO"
    """Logging level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
    LOG_ADK_EVENTS: bool = False
    """Enable or disable raw ADK event logging for debugging."""
    LOG_AGUI_EVENTS: bool = False
    """Enable or disable raw AGUI event logging for debugging."""


# Global log configuration instance
log_config = LogConfig()
