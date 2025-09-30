# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""State service for managing session state operations and state snapshots."""

from collections.abc import Awaitable, Callable
from typing import Any

import jsonpatch  # type: ignore
from ag_ui.core import StateSnapshotEvent
from fastapi import Request

from ..data_model.config import StateConfig
from ..data_model.session import SessionParameter
from ..handler.session import SessionHandler
from ..manager.session import SessionManager
from ..utils.translate import StateEventUtil


class StateService:
    """Service for managing session state operations and state snapshot generation.

    Provides high-level API for session state management including state retrieval,
    partial state updates via JSON patch operations, and state snapshot generation.
    Enables flexible state manipulation with configurable context extraction.

    Key Responsibilities:
    - Retrieve current session state as snapshots
    - Apply JSON patch operations for partial state updates
    - Transform state data through configurable processors
    - Extract context from HTTP requests for session identification
    """

    def __init__(self, state_config: StateConfig):
        """Initialize the state service with configuration.

        Args:
            :param state_config: Configuration for state operations and context extraction
        """
        self.state_config = state_config
        self.session_manager = SessionManager(
            session_service=self.state_config.session_service
        )
        self.state_event_util = StateEventUtil()

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
            self.state_config, config_attr
        )
        if callable(value):
            return await value(request)
        return value

    async def _get_session_parameter(self, request: Request) -> SessionParameter:
        """Extract session parameter from request context.

        Uses configured extractors to build a complete session parameter
        object from the HTTP request, providing the essential identifiers
        for session operations.

        Args:
            :param request: HTTP request containing session context

        Returns:
            SessionParameter containing app name, user ID, and session ID
        """
        return SessionParameter(
            app_name=await self._get_config_value("app_name", request),
            user_id=await self._get_config_value("user_id", request),
            session_id=await self._get_config_value("session_id", request),
        )

    async def _create_session_handler(self, request: Request) -> SessionHandler:
        """Create a session handler configured for the specified request.

        Creates a session handler instance configured with the session manager
        and parameters extracted from the HTTP request context.

        Args:
            :param request: HTTP request containing session context

        Returns:
            Configured SessionHandler instance for state operations
        """
        return SessionHandler(
            session_manager=self.session_manager,
            session_parameter=await self._get_session_parameter(request),
        )

    async def get_state_snapshot(self, request: Request) -> StateSnapshotEvent:
        """Retrieve state snapshot for a session.

        Extracts session context from the request, retrieves the session state,
        applies optional state transformation, and returns a state snapshot event.

        Args:
            :param request: HTTP request containing session context in path

        Returns:
            StateSnapshotEvent containing the current state snapshot

        Raises:
            ValueError: If session is not found or does not exist
        """
        session_handler = await self._create_session_handler(request)
        state = (
            session.state if (session := await session_handler.get_session()) else None
        )
        if state is None:
            raise ValueError("Session not found")
        if self.state_config.get_state:
            state = await self.state_config.get_state(state)
        return self.state_event_util.create_state_snapshot_event(state)

    async def patch_state(
        self, request: Request, state_patch: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Apply JSON patch operations to update session state.

        Extracts session context from the request, retrieves the current state,
        applies JSON patch operations, and updates the session with the modified state.
        This enables partial state updates without replacing the entire state dictionary.

        Args:
            :param request: HTTP request containing session context in path
            :param state_patch: List of JSON patch operations to apply to session state

        Returns:
            Dictionary containing operation status confirmation

        Raises:
            ValueError: If session is not found or does not exist
        """
        session_handler = await self._create_session_handler(request)
        session = await session_handler.get_session()
        if session is None:
            raise ValueError("Session not found")
        await session_handler.update_session_state(
            jsonpatch.apply_patch(session.state, state_patch)
        )
        return {"status": "updated"}
