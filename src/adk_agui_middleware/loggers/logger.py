import json
import logging as log
from typing import Any

from config.log import log_config
from tools.json_encoder import DataclassesEncoder


class JsonFormatter(log.Formatter):
    def __init__(
        self,
        fmt_dict: dict[str, str] | None = None,
        time_format: str = "%Y-%m-%dT%H:%M:%S",
        msec_format: str = "%s.%03dZ",
        cls: type | None = None,
    ):
        super().__init__()
        self.cls = cls
        self.fmt_dict = fmt_dict if fmt_dict is not None else {"message": "message"}
        self.default_time_format = time_format
        self.default_msec_format = msec_format
        self.datefmt = None

    def uses_time(self) -> bool:
        return "asctime" in self.fmt_dict.values()

    def _format_message(self, record: log.LogRecord) -> dict[str, Any]:
        message_dict = {}
        for fmt_key, fmt_val in self.fmt_dict.items():
            if hasattr(record, fmt_val):
                message_dict[fmt_key] = getattr(record, fmt_val)
        return message_dict

    def format(self, record: log.LogRecord) -> str:
        if self.uses_time():
            record.asctime = self.formatTime(record, self.datefmt)

        message_dict = self._format_message(record)

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            message_dict["exc_info"] = record.exc_text

        if record.stack_info:
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        message_dict["message"] = record.msg
        return json.dumps(message_dict, default=str, cls=self.cls, ensure_ascii=False)


def create_logger(name: str, fmt_dict: dict[str, str] | None = None) -> log.Logger:
    log_level = log_config.LOG_LEVEL.upper()
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level = "INFO"

    logger = log.getLogger(name)
    handler = log.StreamHandler()

    logger.setLevel(log_level)
    handler.setLevel(log_level)

    handler.setFormatter(
        JsonFormatter(
            fmt_dict=fmt_dict,
            cls=DataclassesEncoder,
        )
    )
    logger.addHandler(handler)

    return logger


logging = create_logger(
    "generic",
    {
        "timestamp": "asctime",
        "level": "levelname",
    },
)
