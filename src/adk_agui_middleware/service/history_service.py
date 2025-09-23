# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""History service for managing conversation history and session retrieval."""

from collections.abc import Awaitable, Callable
from typing import Any

from ag_ui.core import StateSnapshotEvent
from fastapi import Request

from ..data_model.config import HistoryConfig
from ..data_model.context import HandlerContext
from ..event.agui_event import CustomMessagesSnapshotEvent
from ..handler.history import HistoryHandler
from ..handler.running import RunningHandler
from ..manager.session import SessionManager
from ..utils.translate import StateEventUtil


class HistoryService:
    """Service for managing conversation history and session data retrieval.

    Provides high-level API for accessing user conversation history,
    session listing, and message snapshot generation with configurable
    context extraction.
    """

    def __init__(self, history_config: HistoryConfig):
        """Initialize the history service.

        Args:
            history_config: Configuration for history access and context extraction
        """
        self.history_config = history_config
        self.session_manager = SessionManager(
            session_service=self.history_config.session_service
        )
        self.state_event_util = StateEventUtil()

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
                )
            ),
            **await self._get_user_id_and_app_name(request),
        )

    async def _get_config_value(self, config_attr: str, request: Request) -> str:
        """Extract configuration value from context config.

        Handles both static string values and dynamic callable configurations
        that can extract values from the request context.

        Args:
            config_attr: Name of the configuration attribute to retrieve
            request: HTTP request for context extraction

        Returns:
            Configuration value as string
        """
        value: Callable[[Request], Awaitable[str]] | str = getattr(
            self.history_config, config_attr
        )
        if callable(value):
            return await value(request)
        return value

    async def list_threads(self, request: Request) -> list[dict[str, str]]:
        """List conversation threads for the requesting user.

        Extracts user context from the request and returns a list of
        available conversation threads formatted for client consumption.

        Args:
            request: HTTP request containing user context

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
        conversation thread, returning the updated list of available threads.

        Args:
            request: HTTP request containing session context

        Returns:
            Updated list of dictionaries containing thread information
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
            request: HTTP request containing session context

        Returns:
            MessagesSnapshotEvent containing the conversation history
        """

        message_snapshot = await (
            await self._create_history_handler(request)
        ).get_message_snapshot(await self._get_session_id(request))
        if message_snapshot is None:
            raise ValueError("Session not found")
        return message_snapshot

    async def get_state_snapshot(self, request: Request) -> StateSnapshotEvent:
        """Get current state snapshot for a specific session.

        Extracts session context from the request and returns the current
        state snapshot as a dictionary.

        Args:
            request: HTTP request containing session context

        Returns:
            Dictionary containing the current state snapshot
        """
        state = await (await self._create_history_handler(request)).get_state_snapshot(
            await self._get_session_id(request)
        )
        if state is None:
            raise ValueError("Session not found")
        if self.history_config.get_state:
            state = await self.history_config.get_state(state)
        return self.state_event_util.create_state_snapshot_event(state)

    async def patch_state(
        self, request: Request, state_patch: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Apply JSON patch operations to update session state.

        Extracts session context from the request and applies the provided JSON patch
        operations to update the session state incrementally. This enables partial
        state updates without replacing the entire state dictionary.

        Args:
            :param request: HTTP request containing session context
            :param state_patch: List of JSON Patch operations to apply to the session state

        Returns:
            Dictionary containing operation status confirmation

        Raises:
            ValueError: If the specified session is not found
        """
        result = await (await self._create_history_handler(request)).patch_state(
            session_id=await self._get_session_id(request), state_patch=state_patch
        )
        if result is None:
            raise ValueError("Session not found")
        return result
