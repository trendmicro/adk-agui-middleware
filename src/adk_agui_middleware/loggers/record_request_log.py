import traceback
from typing import Any

from data_model.log import LogMessage
from starlette.requests import Request
from tools.function_name import get_function_name

from loggers import logger


async def record_request_error_log(request: Request, e: Exception) -> dict[str, Any]:
    error_message = LogMessage(
        msg="record request error log",
        func_name=get_function_name(full_chain=True, max_depth=5),
        error_message=repr(e),
        headers=dict(request.headers),
        request_body=(await request.body()).decode(),
        stack_message=traceback.format_exc(),
    )
    error_message_dump = error_message.model_dump()
    logger.logging.error(error_message_dump)
    return error_message_dump


async def record_request_log(request: Request) -> dict[str, Any]:
    message = LogMessage(
        msg="record request log",
        func_name=get_function_name(full_chain=True, max_depth=5),
        headers=dict(request.headers),
        request_body=(await request.body()).decode(),
    )
    message_dump = message.model_dump(exclude_none=True)
    logger.logging.info(message_dump)
    return message_dump
