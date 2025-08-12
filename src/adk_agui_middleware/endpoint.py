from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from base_abc.sse_service import BaseSSEService
from fastapi import FastAPI, Request
from loggers.exception import exception_http_handler
from starlette.responses import StreamingResponse


def register_agui_endpoint(
    app: FastAPI, sse_service: BaseSSEService, path: str = "/"
) -> None:
    @app.post(path)
    async def agui_endpoint(
        agui_content: RunAgentInput, request: Request
    ) -> StreamingResponse:
        async with exception_http_handler(request):
            encoder = EventEncoder(accept=request.headers.get("accept"))
            return StreamingResponse(
                await sse_service.event_generator(
                    await sse_service.get_runner(agui_content, request), encoder
                ),
                media_type=encoder.get_content_type(),
            )
