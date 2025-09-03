"""FastAPI endpoint registration for AGUI middleware service."""

from http.client import InvalidURL

from ag_ui.core import MessagesSnapshotEvent, RunAgentInput
from fastapi import APIRouter, FastAPI, Request
from sse_starlette import EventSourceResponse

from .base_abc.sse_service import BaseSSEService
from .data_model.context import PathConfig
from .loggers.exception import http_exception_handler
from .service.history_service import HistoryService


def register_agui_endpoint(
    app: FastAPI | APIRouter,
    sse_service: BaseSSEService,
    path_config: PathConfig = PathConfig(),  # noqa: B008
    history_service: HistoryService | None = None,
) -> None:
    """Register AGUI endpoint for handling agent interactions via Server-Sent Events.

    Creates a POST endpoint that processes RunAgentInput requests and returns
    streaming responses containing agent events. The endpoint handles the complete
    lifecycle from request processing to stream generation with proper error handling.

    Args:
        app: FastAPI application instance to register the endpoint on
        sse_service: Service implementing BaseSSEService for handling SSE streams
        path_config: Configuration for endpoint paths (main, chat list, history)
        history_service: Optional service for handling conversation history endpoints

    Raises:
        Exception: Various exceptions are handled by exception_http_handler
    """

    @app.post(path_config.agui_main_path)
    async def agui_endpoint(
        agui_content: RunAgentInput, request: Request
    ) -> EventSourceResponse:
        """Handle AGUI agent execution requests.

        Processes incoming agent requests and returns a streaming response
        with agent events encoded according to the request Accept header.
        Uses the SSE service to create an agent runner and generate events.

        Args:
            agui_content: Input containing agent execution parameters and configuration
            request: FastAPI request object containing headers and client information

        Returns:
            EventSourceResponse containing encoded agent events with appropriate media type

        Raises:
            Exception: Handled by exception_http_handler context manager
        """
        async with http_exception_handler(request):
            # Get configured runner for this specific request and content
            # Generate streaming response with encoded events
            return EventSourceResponse(
                await sse_service.event_generator(
                    *await sse_service.get_runner(agui_content, request)
                ),
            )

    @app.get(path_config.agui_chat_list_path)
    async def get_chat_list(request: Request) -> list[dict[str, str]]:
        """Get list of available conversation threads for the user.

        Retrieves all available conversation threads/sessions for the requesting
        user based on context extracted from the request.

        Args:
            request: FastAPI request object containing user context

        Returns:
            List of dictionaries containing thread information

        Raises:
            HTTPException: If history service is not configured or other errors occur
        """
        async with http_exception_handler(request):
            if history_service is None:
                raise InvalidURL(
                    "History service not configured for chat list endpoint"
                )
            return await history_service.list_threads(request)

    @app.get(path_config.agui_history_path)
    async def get_history(request: Request) -> MessagesSnapshotEvent:
        """Get conversation history for a specific session.

        Retrieves the complete conversation history for a session specified
        in the request path, returning it as an AGUI messages snapshot.

        Args:
            request: FastAPI request object containing session context in path

        Returns:
            MessagesSnapshotEvent containing the conversation history

        Raises:
            HTTPException: If history service is not configured or session not found
        """
        async with http_exception_handler(request):
            if history_service is None:
                raise InvalidURL("History service not configured for history endpoint")
            return await history_service.get_history(request)
