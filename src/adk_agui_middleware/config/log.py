from pydantic_settings import BaseSettings


class LogConfig(BaseSettings):
    LOG_LEVEL: str = "INFO"


log_config = LogConfig()
