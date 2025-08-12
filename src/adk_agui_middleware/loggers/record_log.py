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
) -> dict:
    message_data = LogMessage(
        msg=msg,
        func_name=get_function_name(full_chain=True, max_depth=5),
        body=json.loads(json.dumps(body, cls=DataclassesEncoder)),
    )
    if error is not None:
        message_data.error_message = repr(error)
        message_data.stack_message = traceback.format_exc()
    message_dump = message_data.model_dump(exclude_none=True)
    log_level(message_dump)
    return message_dump


def record_debug_log(msg: str, body: Any = None) -> dict:
    return _create_and_log_message(msg, logger.logging.debug, body)


def record_log(msg: str, body: Any = None) -> dict:
    return _create_and_log_message(msg, body=body)


def record_warning_log(msg: str, body: Any = None) -> dict:
    return _create_and_log_message(msg, logger.logging.warning, body)


def record_error_log(msg: str, e: Exception | None = None, body: Any = None) -> dict:
    return _create_and_log_message(msg, logger.logging.error, body, e)
