"""Logging configuration settings for AGUI middleware."""

from pydantic_settings import BaseSettings


class LogConfig(BaseSettings):
    """Configuration settings for application logging.

    Uses Pydantic BaseSettings to manage logging configuration with
    environment variable support and validation.
    """

    LOG_LEVEL: str = "INFO"
    """Logging level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""


# Global log configuration instance
log_config = LogConfig()
