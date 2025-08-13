"""FastAPI endpoint registration for AGUI middleware service."""

from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, FastAPI, Request
from starlette.responses import StreamingResponse

from .base_abc.sse_service import BaseSSEService
from .loggers.exception import exception_http_handler


def register_agui_endpoint(
    app: FastAPI | APIRouter, sse_service: BaseSSEService, path: str = "/"
) -> None:
    """Register AGUI endpoint for handling agent interactions via Server-Sent Events.

    Creates a POST endpoint that processes RunAgentInput requests and returns
    streaming responses containing agent events. The endpoint handles the complete
    lifecycle from request processing to stream generation with proper error handling.

    Args:
        app: FastAPI application instance to register the endpoint on
        sse_service: Service implementing BaseSSEService for handling SSE streams
        path: URL path for the endpoint, defaults to "/"

    Raises:
        Exception: Various exceptions are handled by exception_http_handler
    """

    @app.post(path)
    async def agui_endpoint(
        agui_content: RunAgentInput, request: Request
    ) -> StreamingResponse:
        """Handle AGUI agent execution requests.

        Processes incoming agent requests and returns a streaming response
        with agent events encoded according to the request Accept header.
        Uses the SSE service to create an agent runner and generate events.

        Args:
            agui_content: Input containing agent execution parameters and configuration
            request: FastAPI request object containing headers and client information

        Returns:
            StreamingResponse containing encoded agent events with appropriate media type

        Raises:
            Exception: Handled by exception_http_handler context manager
        """
        async with exception_http_handler(request):
            # Create encoder based on client's Accept header preferences
            encoder = EventEncoder(accept=request.headers.get("accept"))
            # Get configured runner for this specific request and content
            runner = await sse_service.get_runner(agui_content, request)
            # Generate streaming response with encoded events
            return StreamingResponse(
                await sse_service.event_generator(runner, encoder),
                media_type=encoder.get_content_type(),
            )
