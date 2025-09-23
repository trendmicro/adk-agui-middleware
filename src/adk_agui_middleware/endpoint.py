# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""FastAPI endpoint registration for AGUI middleware service."""

from http.client import InvalidURL
from typing import Any

from ag_ui.core import RunAgentInput, StateSnapshotEvent
from fastapi import APIRouter, FastAPI, Request
from sse_starlette import EventSourceResponse

from .base_abc.sse_service import BaseSSEService
from .data_model.config import PathConfig
from .event.agui_event import CustomMessagesSnapshotEvent
from .loggers.exception import http_exception_handler
from .service.history_service import HistoryService


def register_agui_endpoint(  # noqa: C901
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
        :param app: FastAPI application instance to register the endpoint on
        :param sse_service: Service implementing BaseSSEService for handling SSE streams
        :param path_config: Configuration for endpoint paths (main, chat list, history)
        :param history_service: Optional service for handling conversation history endpoints

    Raises:
        Exception: Various exceptions are handled by exception_http_handler
    """

    @app.post(path_config.agui_main_path)
    async def run_agui_main(
        agui_content: RunAgentInput, request: Request
    ) -> EventSourceResponse:
        """Handle AGUI agent execution requests.

        Processes incoming agent requests and returns a streaming response
        with agent events encoded according to the request Accept header.
        Uses the SSE service to create an agent runner and generate events.

        Args:
            :param agui_content: Input containing agent execution parameters and configuration
            :param request: FastAPI request object containing headers and client information

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

    @app.get(path_config.agui_thread_list_path)
    async def get_agui_thread_list(request: Request) -> list[dict[str, str]]:
        """Get list of available conversation threads for the user.

        Retrieves all available conversation threads/sessions for the requesting
        user based on context extracted from the request.

        Args:
            :param request: FastAPI request object containing user context

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

    @app.delete(path_config.agui_thread_delete_path)
    async def delete_agui_thread(request: Request) -> dict[str, str]:
        """Delete a specific conversation thread for the user.

        Permanently removes a conversation thread identified by the thread_id
        in the request path. This operation deletes all associated messages
        and session data for the specified conversation.

        Args:
            :param request: FastAPI request object containing thread_id in path and user context

        Returns:
            Dictionary containing deletion status confirmation

        Raises:
            HTTPException: If history service is not configured or thread not found
        """
        async with http_exception_handler(request):
            if history_service is None:
                raise InvalidURL(
                    "History service not configured for chat list endpoint"
                )
            return await history_service.delete_thread(request)

    @app.patch(path_config.agui_patch_state_path)
    async def patch_agui_state(
        request: Request, state_patch: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Update session state with partial state modifications.

        Applies JSON patch operations to update session state, enabling
        partial updates without replacing the entire state dictionary.
        This endpoint supports incremental state changes for maintaining
        session context across multiple interactions.

        Args:
            :param request: FastAPI request object containing session context in path
            :param state_patch: List of JSON patch operations to apply to session state

        Returns:
            Dictionary containing operation status confirmation

        Raises:
            HTTPException: If history service is not configured or state update fails
        """
        async with http_exception_handler(request):
            if history_service is None:
                raise InvalidURL("History service not configured for state endpoint")
            return await history_service.patch_state(request, state_patch)

    @app.get(path_config.agui_message_snapshot_path)
    async def get_agui_message_snapshot(
        request: Request,
    ) -> CustomMessagesSnapshotEvent:
        """Get conversation history for a specific session.

        Retrieves the complete conversation history for a session specified
        in the request path, returning it as an AGUI messages snapshot.

        Args:
            :param request: FastAPI request object containing session context in path

        Returns:
            MessagesSnapshotEvent containing the conversation history

        Raises:
            HTTPException: If history service is not configured or session not found
        """
        async with http_exception_handler(request):
            if history_service is None:
                raise InvalidURL("History service not configured for history endpoint")
            return await history_service.get_message_snapshot(request)

    @app.get(path_config.agui_state_snapshot_path)
    async def get_agui_state_snapshot(request: Request) -> StateSnapshotEvent:
        """Get current state snapshot for a specific session.

        Retrieves the current state snapshot for a session specified
        in the request path, returning it as a StateSnapshotEvent.

        Args:
            :param request: FastAPI request object containing session context in path

        Returns:
            StateSnapshotEvent containing the current state snapshot

        Raises:
            HTTPException: If history service is not configured or session not found
        """
        async with http_exception_handler(request):
            if history_service is None:
                raise InvalidURL("History service not configured for state endpoint")
            return await history_service.get_state_snapshot(request)
