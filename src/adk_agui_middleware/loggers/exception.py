import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from ag_ui.core import EventType, RunErrorEvent
from data_model.error import ErrorModel
from fastapi import HTTPException, Request, status
from loggers.record_log import record_error_log
from loggers.record_request_log import record_request_error_log, record_request_log


def get_common_http_exception(
    status_code: int,
    error_message: str,
    error_description: dict[str, Any],
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorModel(
            error=error_message,
            error_description=error_description,
            timestamp=int(time.time()),
        ).model_dump(),
    )


def get_http_internal_server_error_exception(error_description: dict[str, Any]) -> HTTPException:
    return get_common_http_exception(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal Server Error.",
        error_description,
    )


@asynccontextmanager
async def exception_http_handler(request: Request) -> AsyncGenerator[None, Any]:
    try:
        await record_request_log(request)
        yield
    except HTTPException as e:
        await record_request_error_log(request, e)
        raise
    except Exception as e:
        await record_request_error_log(request, e)
        raise get_http_internal_server_error_exception(
            {"error_message": repr(e)}
        ) from e


@asynccontextmanager
async def exception_agui_handler(
    event_queue: asyncio.Queue[Any],
) -> AsyncGenerator[None, Any]:
    try:
        yield
    except Exception as e:
        record_error_log("AGUI Exception Handler", e)
        await event_queue.put(
            RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
                code="BACKGROUND_EXECUTION_ERROR",
            )
        )
        await event_queue.put(None)
