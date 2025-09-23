# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Session manager for handling ADK session operations and state management."""

import time
from typing import Any

from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService, Session

from ..data_model.session import SessionParameter
from ..loggers.record_log import record_error_log, record_warning_log


class SessionManager:
    """Manages ADK session operations including creation, retrieval, and state updates.

    Provides a layer of abstraction over the ADK session service, handling session
    lifecycle management, state updates through events, and error handling.
    Encapsulates the complexity of session state management.
    """

    def __init__(self, session_service: BaseSessionService):
        """Initialize the session manager with an ADK session service.

        Args:
            :param session_service: ADK session service implementation for session operations
        """
        self.session_service = session_service

    async def list_sessions(self, app_name: str, user_id: str) -> list[Session]:
        """List all sessions for a given app and user.

        Retrieves all session objects associated with the specified application
        and user, useful for conversation history and session management.

        Args:
            :param app_name: Name of the application
            :param user_id: Identifier for the user

        Returns:
            List of Session objects
        """
        return (
            await self.session_service.list_sessions(app_name=app_name, user_id=user_id)
        ).sessions

    async def get_session(self, session_parameter: SessionParameter) -> Session | None:
        """Retrieve a session using the provided session parameters.

        Fetches a specific session identified by the complete session parameters,
        returning None if the session doesn't exist.

        Args:
            :param session_parameter: Parameters identifying the session (app, user, session ID)

        Returns:
            Session object if found, None otherwise
        """
        return await self.session_service.get_session(
            session_id=session_parameter.session_id,
            app_name=session_parameter.app_name,
            user_id=session_parameter.user_id,
        )

    async def check_and_create_session(
        self,
        session_parameter: SessionParameter,
        initial_state: dict[str, Any] | None = None,
    ) -> Session:
        """Get existing session or create a new one if it doesn't exist.

        Implements the "get or create" pattern for sessions, ensuring a session
        always exists after this call.

        Args:
            :param session_parameter: Parameters identifying the session
            :param initial_state: Optional initial state for new sessions

        Returns:
            Session object (either existing or newly created)
        """
        # Try to get existing session first
        session = await self.get_session(session_parameter)
        if not session:
            # Create new session if none exists
            session = await self.session_service.create_session(
                session_id=session_parameter.session_id,
                user_id=session_parameter.user_id,
                app_name=session_parameter.app_name,
                state=initial_state or {},
            )
        return session

    async def delete_session(self, session_parameter: SessionParameter) -> None:
        """Delete a session using the provided session parameters.

        Permanently removes the session and all associated data from the session service.
        This operation cannot be undone and will remove all conversation history
        and state data for the specified session.

        Args:
            :param session_parameter: Parameters identifying the session to delete (app, user, session ID)
        """
        await self.session_service.delete_session(
            session_id=session_parameter.session_id,
            app_name=session_parameter.app_name,
            user_id=session_parameter.user_id,
        )

    async def update_session_state(
        self,
        session_parameter: SessionParameter,
        state_updates: dict[str, Any] | None,
    ) -> bool:
        """Update session state by appending a state delta event.

        Creates an ADK Event with state delta actions and appends it to the session,
        which triggers state updates in the session service. This is the primary
        mechanism for persisting state changes including HITL workflow data.

        Args:
            :param session_parameter: Parameters identifying the session to update
            :param state_updates: Dictionary of state changes to apply

        Returns:
            True if update was successful, False if session not found or no updates
        """
        session = await self.get_session(session_parameter)
        if not (session and state_updates):
            record_warning_log(
                f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
            )
            return False

        # Create system event with state delta for the update
        event = Event(
            invocation_id=f"state_update_{int(time.time())}",
            author="system",
            actions=EventActions(state_delta=state_updates),
            timestamp=time.time(),
        )
        # Append event to session to trigger state update
        await self.session_service.append_event(session, event)
        return True

    async def get_session_state(
        self, session_parameter: SessionParameter
    ) -> dict[str, Any]:
        """Retrieve the current state dictionary for a session.

        Gets the session and returns its state dictionary. Handles missing
        sessions and errors gracefully by returning empty dictionary. This
        provides access to all persistent session data including HITL state.

        Args:
            :param session_parameter: Parameters identifying the session

        Returns:
            Dictionary containing session state, empty dict if session not found or error
        """
        try:
            if session := await self.get_session(session_parameter):
                return session.state
            record_warning_log(
                f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
            )
        except Exception as e:
            record_error_log(f"Failed to get session state: {e}")
            return {}
        return {}

    async def get_state_value(
        self,
        session_parameter: SessionParameter,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a specific value from the session state by key.

        Convenience method for retrieving individual state values without
        getting the entire state dictionary. Useful for checking specific
        state flags or values like pending tool calls.

        Args:
            :param session_parameter: Parameters identifying the session
            :param key: State key to retrieve
            :param default: Default value to return if key not found or session missing

        Returns:
            Value for the specified key, or default if not found
        """
        try:
            session = await self.get_session(session_parameter)
            if not session:
                record_warning_log(
                    f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
                )
                return default
            return session.state.get(key, default)
        except Exception as e:
            record_error_log(f"Failed to get state value: {e}")
            return default
