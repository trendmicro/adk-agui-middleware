# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Session handler for managing user session state and tool call lifecycle."""

from typing import Any, cast

from google.adk.sessions import Session

from ..data_model.session import SessionParameter
from ..loggers.record_log import record_error_log, record_log
from ..manager.session import SessionManager


class SessionHandler:
    """Handles session operations including state management and tool call tracking.

    Provides a high-level interface for session operations, managing pending tool calls,
    session state updates, and session lifecycle. Acts as a bridge between the AGUI
    handler layer and the underlying session management infrastructure.

    Key Responsibilities:
    - Manage session lifecycle (creation, retrieval, state updates)
    - Track pending tool calls for HITL (Human-in-the-Loop) workflows
    - Provide session state access and manipulation
    - Handle session-related error conditions and logging
    """

    def __init__(
        self, session_manager: SessionManager, session_parameter: SessionParameter
    ):
        """Initialize the session handler.

        Sets up the handler with the session manager and parameters needed
        to identify and manage the specific session for this interaction.

        Args:
            :param session_manager: Manager for low-level session operations
            :param session_parameter: Parameters identifying the session (app, user, session ID)
        """
        self.session_manager = session_manager
        self.session_parameter = session_parameter

    @property
    def app_name(self) -> str:
        """Get the application name from session parameters.

        Returns:
            Application name string
        """
        return self.session_parameter.app_name

    @property
    def user_id(self) -> str:
        """Get the user ID from session parameters.

        Returns:
            User identifier string
        """
        return self.session_parameter.user_id

    @property
    def session_id(self) -> str:
        """Get the session ID from session parameters.

        Returns:
            Session identifier string
        """
        return self.session_parameter.session_id

    async def get_session(self) -> Session | None:
        """Retrieve the session object for this handler's parameters.

        Delegates to the session manager to retrieve the session identified
        by the current session parameters.

        Returns:
            Session object if found, None otherwise
        """
        return await self.session_manager.get_session(self.session_parameter)

    async def get_session_state(self) -> dict[str, Any]:
        """Get the current state dictionary for this session.

        Retrieves the complete state dictionary from the session,
        which includes all persistent data for the session.

        Returns:
            Dictionary containing session state key-value pairs
        """
        return await self.session_manager.get_session_state(self.session_parameter)

    async def check_and_create_session(
        self, initial_state: dict[str, Any] | None = None
    ) -> Session:
        """Create session if it doesn't exist, otherwise return existing session.

        Implements the "get or create" pattern for sessions, ensuring a session
        always exists after this call. This is essential for session-based workflows.

        Args:
            :param initial_state: Optional initial state to set when creating a new session

        Returns:
            Session object (either existing or newly created)
        """
        return await self.session_manager.check_and_create_session(
            session_parameter=self.session_parameter, initial_state=initial_state
        )

    async def update_session_state(
        self, initial_state: dict[str, Any] | None = None
    ) -> bool:
        """Update the session state with new values.

        Applies the provided state updates to the current session,
        merging them with existing state data.

        Args:
            :param initial_state: Dictionary of state updates to apply

        Returns:
            True if update was successful, False otherwise
        """
        return await self.session_manager.update_session_state(
            session_parameter=self.session_parameter,
            state_updates=initial_state,
        )

    async def overwrite_pending_tool_calls(
        self, tool_call_info: dict[str, str]
    ) -> None:
        """Update the session state with current pending tool calls.

        Stores the current list of pending tool calls in the session state,
        which is essential for HITL workflow management. These pending calls
        are used to resume agent execution after human tool result submission.

        Args:
            :param tool_call_info: Dictionary mapping tool call IDs to function names
        """
        if not tool_call_info:
            return
        record_log(
            f"Adding pending tool call {tool_call_info} for session {self.session_parameter.session_id}, app_name={self.session_parameter.app_name}, user_id={self.session_parameter.user_id}"
        )
        try:
            if await self.session_manager.update_session_state(
                self.session_parameter,
                state_updates={"pending_tool_calls": tool_call_info},
            ):
                record_log(
                    f"Added tool call {tool_call_info} to session {self.session_parameter.session_id} pending list"
                )
        except Exception as e:
            record_error_log(
                f"Failed to add pending tool call {tool_call_info} to session {self.session_parameter.session_id}.",
                e,
            )

    async def get_pending_tool_calls(self) -> dict[str, str]:
        """Retrieve pending tool calls from session state.

        Gets the list of tool calls that are awaiting human results, which
        is crucial for resuming HITL workflows correctly. These pending calls
        represent long-running operations that have been submitted to humans
        for completion.

        Returns:
            Dictionary mapping tool call IDs to function names for pending tools
        """
        try:
            session_state = await self.session_manager.get_session_state(
                self.session_parameter
            )
            return cast(dict[str, str], session_state.get("pending_tool_calls", {}))
        except Exception as e:
            record_error_log(
                f"Failed to check pending tool calls for session {self.session_parameter.session_id}.",
                e,
            )
            return {}
