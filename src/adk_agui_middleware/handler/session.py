"""Session handler for managing user session state and tool call lifecycle."""

from typing import Any

from data_model.session import SessionParameter
from google.adk.sessions import Session
from loggers.record_log import record_error_log, record_log, record_warning_log
from manager.session import SessionManager


class SessionHandler:
    """Handles session operations including state management and tool call tracking.

    Provides a high-level interface for session operations, managing pending tool calls,
    session state updates, and session lifecycle. Acts as a bridge between the AGUI
    handler layer and the underlying session management infrastructure.
    """

    def __init__(
        self, session_manager: SessionManager, session_parameter: SessionParameter
    ):
        """Initialize the session handler.

        Args:
            session_manager: Manager for session operations
            session_parameter: Parameters identifying the session (app, user, session ID)
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

    @staticmethod
    def get_pending_tool_calls_dict(pending_calls: Any) -> dict[str, Any]:
        """Create a dictionary for storing pending tool calls in session state.

        Args:
            pending_calls: List or collection of pending tool call IDs

        Returns:
            Dictionary with 'pending_tool_calls' key for session state updates
        """
        return {"pending_tool_calls": pending_calls}

    async def get_session(self) -> Session | None:
        """Retrieve the session object for this handler's parameters.

        Returns:
            Session object if found, None otherwise
        """
        return await self.session_manager.get_session(self.session_parameter)

    async def get_session_state(self) -> dict[str, Any]:
        """Get the current state dictionary for this session.

        Returns:
            Dictionary containing session state key-value pairs
        """
        return await self.session_manager.get_session_state(self.session_parameter)

    async def check_and_create_session(
        self, initial_state: dict[str, Any] | None = None
    ) -> Session:
        """Create session if it doesn't exist, otherwise return existing session.

        Args:
            initial_state: Optional initial state to set when creating a new session

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

        Args:
            initial_state: Dictionary of state updates to apply

        Returns:
            True if update was successful, False otherwise
        """
        return await self.session_manager.update_session_state(
            session_parameter=self.session_parameter,
            state_updates=initial_state,
        )

    async def check_and_remove_pending_tool_call(self, tool_call_id: str) -> None:
        """Remove a tool call ID from the pending tool calls list.

        Checks if the tool call ID exists in pending calls, removes it if found,
        and updates the session state. Logs warnings if the tool call is not found.

        Args:
            tool_call_id: ID of the tool call to remove from pending list
        """
        pending_calls = await self.get_pending_tool_calls()
        if tool_call_id not in pending_calls:
            record_warning_log(
                f"No pending tool calls found for tool result {tool_call_id} in thread {self.session_parameter.session_id}"
            )
            return
        record_log(
            f"Processing tool result {tool_call_id} for thread {self.session_parameter.session_id} with pending tools"
        )
        # Remove the tool call ID from the pending list
        pending_calls.remove(tool_call_id)
        # Update session state with the modified pending calls list
        success = await self.session_manager.update_session_state(
            session_parameter=self.session_parameter,
            state_updates=self.get_pending_tool_calls_dict(pending_calls),
        )
        record_log(
            f"Removed tool call {tool_call_id} from session {self.session_parameter.session_id} pending list is {success}."
        )

    async def add_pending_tool_call(self, tool_call_id: str) -> None:
        """Add a tool call ID to the pending tool calls list.

        Retrieves current pending calls, adds the new tool call ID if not already present,
        and updates the session state. Handles errors gracefully with logging.

        Args:
            tool_call_id: ID of the tool call to add to pending list
        """
        record_log(
            f"Adding pending tool call {tool_call_id} for session {self.session_parameter.session_id}, app_name={self.session_parameter.app_name}, user_id={self.session_parameter.user_id}"
        )
        try:
            # Get current pending calls from session state
            pending_calls = (
                await self.session_manager.get_session_state(
                    self.session_parameter,
                )
            ).get("pending_tool_calls", [])
            # Add tool call ID if not already in the list
            if tool_call_id not in pending_calls:
                pending_calls.append(tool_call_id)
                # Update session state with the new pending calls list
                if await self.session_manager.update_session_state(
                    self.session_parameter,
                    state_updates=self.get_pending_tool_calls_dict(pending_calls),
                ):
                    record_log(
                        f"Added tool call {tool_call_id} to session {self.session_parameter.session_id} pending list"
                    )
        except Exception as e:
            record_error_log(
                f"Failed to add pending tool call {tool_call_id} to session {self.session_parameter.session_id}.",
                e,
            )

    async def get_pending_tool_calls(self) -> Any | None:
        """Retrieve the list of pending tool calls for this session.

        Gets the current session state and extracts the pending tool calls list.
        Handles errors and missing sessions gracefully.

        Returns:
            List of pending tool call IDs, or None if session not found or error occurred
        """
        try:
            # Get current session state
            session_history = await self.session_manager.get_session_state(
                self.session_parameter
            )
            # Check if session exists in the state
            if self.session_parameter.session_id not in session_history:
                record_warning_log(
                    f"Session {self.session_parameter.session_id} not found for user {self.session_parameter.user_id}."
                )
                return None
            # Return pending tool calls list or empty list if not found
            return session_history.get("pending_tool_calls", [])
        except Exception as e:
            record_error_log(
                f"Failed to check pending tool calls for session {self.session_parameter.session_id}.",
                e,
            )
        return None
