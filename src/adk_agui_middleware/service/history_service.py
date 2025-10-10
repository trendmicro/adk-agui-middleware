# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""History service for managing conversation history and session retrieval."""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request

from ..data_model.config import HistoryConfig
from ..data_model.context import HandlerContext
from ..event.agui_event import CustomMessagesSnapshotEvent
from ..event.event_translator import EventTranslator
from ..handler.history import HistoryHandler
from ..handler.running import RunningHandler
from ..manager.session import SessionManager


class HistoryService:
    """Service for managing conversation history and session data retrieval.

    Provides high-level API for accessing user conversation history,
    session listing, and message snapshot generation with configurable
    context extraction.
    """

    def __init__(self, history_config: HistoryConfig):
        """Initialize the history service.

        Args:
            :param history_config: Configuration for history access and context extraction
        """
        self.history_config = history_config
        self.session_manager = SessionManager(
            session_service=self.history_config.session_service
        )

    async def _get_user_id_and_app_name(self, request: Request) -> dict[str, str]:
        """Extract user ID and application name from request context.

        Uses configured extractors to obtain user identity and application context
        from the HTTP request, providing the essential context for session operations.

        Args:
            :param request: HTTP request containing user and application context

        Returns:
            Dictionary containing 'app_name' and 'user_id' extracted from request
        """
        return {
            "app_name": await self._get_config_value("app_name", request),
            "user_id": await self._get_config_value("user_id", request),
        }

    async def _get_session_id(self, request: Request) -> str:
        """Extract session identifier from request context.

        Uses configured session ID extractor to obtain the session identifier
        from the HTTP request, essential for conversation persistence and
        session-specific operations.

        Args:
            :param request: HTTP request containing session context

        Returns:
            Session identifier string extracted from request context
        """
        return await self._get_config_value("session_id", request)

    async def _create_history_handler(self, request: Request) -> HistoryHandler:
        """Create a history handler for the specified app and user.

        Args:
            :param request: HTTP request containing user context required for handler creation

        Returns:
            Configured HistoryHandler instance
        """
        return HistoryHandler(
            session_manager=self.session_manager,
            running_handler=RunningHandler(
                handler_context=HandlerContext(
                    adk_event_handler=self.history_config.adk_event_handler,
                    agui_event_handler=self.history_config.agui_event_handler,
                    translate_handler=self.history_config.translate_handler,
                ),
                event_translator=EventTranslator(
                    self.history_config.retune_on_stream_complete
                ),
            ),
            **await self._get_user_id_and_app_name(request),
        )

    async def _get_config_value(self, config_attr: str, request: Request) -> str:
        """Extract configuration value from context config.

        Handles both static string values and dynamic callable configurations
        that can extract values from the request context.

        Args:
            :param config_attr: Name of the configuration attribute to retrieve
            :param request: HTTP request for context extraction

        Returns:
            Configuration value as string
        """
        value: Callable[[Request], Awaitable[str]] | str = getattr(
            self.history_config, config_attr
        )
        if callable(value):
            return await value(request)
        return value

    async def list_threads(self, request: Request) -> list[dict[str, Any]]:
        """List conversation threads for the requesting user.

        Extracts user context from the request and returns a list of
        available conversation threads formatted for client consumption.

        Args:
            :param request: HTTP request containing user context

        Returns:
            List of dictionaries containing thread information
        """
        session_list = await (
            await self._create_history_handler(request)
        ).list_sessions()
        if self.history_config.get_thread_list:
            return await self.history_config.get_thread_list(session_list)
        return [{"threadId": session.id} for session in session_list]

    async def delete_thread(self, request: Request) -> dict[str, str]:
        """Delete a specific conversation thread for the user.

        Extracts session context from the request and deletes the specified
        conversation thread, returning a status confirmation payload.

        Args:
            :param request: HTTP request containing session context

        Returns:
            Dictionary containing deletion status confirmation
        """
        await (await self._create_history_handler(request)).delete_session(
            await self._get_session_id(request)
        )
        return {"status": "deleted"}

    async def get_message_snapshot(
        self, request: Request
    ) -> CustomMessagesSnapshotEvent:
        """Get conversation history for a specific session.

        Extracts session context from the request and returns the complete
        conversation history as an AGUI messages snapshot.

        Args:
            :param request: HTTP request containing session context

        Returns:
            MessagesSnapshotEvent containing the conversation history
        """

        message_snapshot = await (
            await self._create_history_handler(request)
        ).get_message_snapshot(await self._get_session_id(request))
        if message_snapshot is None:
            raise ValueError("Session not found")
        return message_snapshot
