# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Session handler for managing user session state and tool call lifecycle."""

from typing import Any, cast

from google.adk.sessions import Session

from ..data_model.session import SessionParameter
from ..loggers.record_log import record_error_log, record_log, record_warning_log
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

    @staticmethod
    def get_pending_tool_calls_dict(pending_calls: list[str]) -> dict[str, list[str]]:
        """Create a dictionary for storing pending tool calls in session state.

        Formats pending tool call IDs into the standard session state structure
        used throughout the HITL (Human-in-the-Loop) workflow. This standardized
        format ensures consistent storage and retrieval of pending tool calls.

        Args:
            :param pending_calls: List of pending tool call IDs requiring human intervention

        Returns:
            Dictionary with 'pending_tool_calls' key for session state updates

        Note:
            This standardized format is crucial for HITL state persistence and
            enables consistent querying of pending human interventions across
            the middleware system.
        """
        return {"pending_tool_calls": pending_calls}

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

    async def check_and_remove_pending_tool_call(
        self, tool_call_ids: list[str]
    ) -> None:
        """Remove tool call IDs from the pending tool calls list.

        This method implements the core HITL (Human-in-the-Loop) pattern for tool execution.
        When an agent makes a tool call, it's added to pending_tool_calls in session state.
        When a human/user provides the tool result, this method removes the corresponding
        pending tool call ID, completing the HITL workflow.

        HITL Process:
        1. Agent calls tool → tool_call_id added to pending_tool_calls
        2. Agent execution pauses, waits for human intervention
        3. Human/user provides tool result via API
        4. This method removes tool_call_id from pending_tool_calls
        5. Agent execution resumes with tool result

        Args:
            :param tool_call_ids: List of tool call IDs to remove from pending list

        Note:
            This is essential for HITL workflows where tools require human approval
            or input before execution can continue.
        """
        pending_set = set(await self.get_pending_tool_calls())
        tool_call_set = set(tool_call_ids)
        remove_list = pending_set & tool_call_set
        if not remove_list:
            record_warning_log(
                f"No pending tool calls found for tool result {tool_call_ids} in thread {self.session_parameter.session_id}"
            )
            return
        success = await self.session_manager.update_session_state(
            session_parameter=self.session_parameter,
            state_updates=self.get_pending_tool_calls_dict(
                list(pending_set - tool_call_set)
            ),
        )
        record_log(
            f"Removed tool call {remove_list} from session {self.session_parameter.session_id} pending list is {success}."
        )

    async def add_pending_tool_call(self, tool_call_ids: list[str]) -> None:
        """Add tool call IDs to the pending tool calls list.

        This method initiates the HITL (Human-in-the-Loop) pattern by marking tool calls
        as pending human intervention. When an agent invokes tools that require human
        input or approval, this method stores the tool call IDs in session state, effectively
        pausing agent execution until human intervention is provided.

        HITL Pattern Initiation:
        1. Agent attempts to call tools requiring human input
        2. This method adds tool_call_ids to pending_tool_calls in session state
        3. Agent execution flow is paused/suspended
        4. Session persists the pending state for later retrieval
        5. External systems can query pending_tool_calls to show humans what needs attention

        Args:
            :param tool_call_ids: List of tool call IDs to add to pending list

        Note:
            This enables asynchronous HITL workflows where agent execution can be
            resumed later after human provides the necessary input or approval.
        """
        if not tool_call_ids:
            return
        record_log(
            f"Adding pending tool call {tool_call_ids} for session {self.session_parameter.session_id}, app_name={self.session_parameter.app_name}, user_id={self.session_parameter.user_id}"
        )
        try:
            # Get current pending calls using the dedicated method
            pending_calls = await self.get_pending_tool_calls()
            # Add tool call ID if not already in the list
            pending_calls.extend(set(tool_call_ids) - set(pending_calls))
            # Update session state with the new pending calls list
            if await self.session_manager.update_session_state(
                self.session_parameter,
                state_updates=self.get_pending_tool_calls_dict(pending_calls),
            ):
                record_log(
                    f"Added tool call {tool_call_ids} to session {self.session_parameter.session_id} pending list"
                )
        except Exception as e:
            record_error_log(
                f"Failed to add pending tool call {tool_call_ids} to session {self.session_parameter.session_id}.",
                e,
            )

    async def get_pending_tool_calls(self) -> list[str]:
        """Retrieve the list of pending tool calls for this session.

        This method provides visibility into active HITL (Human-in-the-Loop) workflows
        by returning all tool calls currently awaiting human intervention. External systems
        use this to display pending actions to users and manage HITL queue states.

        HITL State Query:
        - Returns tool_call_ids that are waiting for human input/approval
        - Used by UIs to show users what actions require their attention
        - Enables HITL workflow management and monitoring
        - Empty list indicates no pending human interventions

        Returns:
            List of pending tool call IDs currently awaiting human intervention,
            empty list if session not found or no pending calls exist

        Example:
            pending = await handler.get_pending_tool_calls()
            if pending:
                print(f"Pending HITL actions: {pending}")
        """
        try:
            # Get current session state dictionary
            session_state = await self.session_manager.get_session_state(
                self.session_parameter
            )
            # Return pending tool calls list or empty list if not found
            return cast(list[str], session_state.get("pending_tool_calls", []))
        except Exception as e:
            record_error_log(
                f"Failed to check pending tool calls for session {self.session_parameter.session_id}.",
                e,
            )
            return []
