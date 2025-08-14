"""Logging configuration settings for AGUI middleware."""

from pydantic_settings import BaseSettings


class LogConfig(BaseSettings):
    """Configuration settings for application logging.

    Uses Pydantic BaseSettings to manage logging configuration with
    environment variable support and validation.
    """

    LOG_LEVEL: str = "INFO"
    """Logging level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
    LOG_EVENT: bool = False
    """Enable or disable logging level setting."""
    LOG_AGUI: bool = False
    """Enable or disable AGUI-specific logging."""


# Global log configuration instance
log_config = LogConfig()
