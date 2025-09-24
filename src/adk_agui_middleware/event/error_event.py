# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Error event classes for handling encoding and execution errors in AGUI middleware."""

from ag_ui.core import EventType, RunErrorEvent

from ..loggers.record_log import record_error_log
from ..utils.convert.agui_event_to_sse import convert_agui_event_to_sse


class AGUIEncoderError(Exception):
    """Exception class providing static methods for encoding error events.

    Handles encoding errors and agent execution errors by creating appropriate
    error events and logging the issues. This class provides centralized error
    handling for SSE event encoding failures and agent execution problems.
    """

    @staticmethod
    def create_encoding_error_event(e: Exception) -> dict[str, str]:
        """Create an encoded error event for encoding failures.

        Handles situations where AGUI events cannot be properly encoded
        to SSE format, creating a fallback error event that can be safely
        transmitted to clients.

        Args:
            :param e: Original exception that caused the encoding failure

        Returns:
            Encoded error event dictionary in SSE format
        """
        error_event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Event encoding failed: {repr(e)}",
            code="ENCODING_ERROR",
        )
        record_error_log("Event encoding failed", e)
        return convert_agui_event_to_sse(error_event)

    @staticmethod
    def create_agent_error_event(e: Exception) -> dict[str, str]:
        """Create an encoded error event for agent execution failures.

        Handles exceptions that occur during agent execution, creating
        a properly formatted error event that can be sent to clients
        to indicate the failure.

        Args:
            :param e: Original exception that caused the agent failure

        Returns:
            Encoded error event dictionary in SSE format
        """
        error_event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Agent execution failed: {repr(e)}",
            code="AGENT_ERROR",
        )
        record_error_log("AGUI Agent Error Handler", e)
        return convert_agui_event_to_sse(error_event)


class AGUIErrorEvent:
    """Utility class for creating specific types of AGUI error events.

    Provides static methods for creating RunErrorEvent objects for common
    error scenarios in AGUI middleware execution. Each method handles a
    specific error category with appropriate logging and error codes.
    """

    @staticmethod
    def create_execution_error_event(e: Exception) -> RunErrorEvent:
        """Create an error event for general execution failures.

        Handles general exceptions that occur during agent workflow execution,
        providing a standardized error event for client consumption.

        Args:
            :param e: Exception that caused the execution failure

        Returns:
            RunErrorEvent for the execution error
        """
        record_error_log("Error in new execution", e)
        return RunErrorEvent(
            type=EventType.RUN_ERROR, message=repr(e), code="EXECUTION_ERROR"
        )

    @staticmethod
    def create_no_tool_results_error(thread_id: str) -> RunErrorEvent:
        """Create an error event when tool results are missing.

        Handles HITL workflow errors where a tool result submission is detected
        but no actual tool results are found in the message content.

        Args:
            :param thread_id: ID of the thread where tool results were expected

        Returns:
            RunErrorEvent for missing tool results
        """
        record_error_log(
            f"Tool result submission without tool results for thread {thread_id}"
        )
        return RunErrorEvent(
            type=EventType.RUN_ERROR,
            message="No tool results found in submission",
            code="NO_TOOL_RESULTS",
        )

    @staticmethod
    def create_no_input_message_error(thread_id: str) -> RunErrorEvent:
        record_error_log(f"Input message missing for thread {thread_id}")
        return RunErrorEvent(
            type=EventType.RUN_ERROR,
            message="Input message is missing",
            code="NO_INPUT_MESSAGE",
        )

    @staticmethod
    def create_tool_processing_error_event(e: Exception) -> RunErrorEvent:
        """Create an error event for tool result processing failures.

        Handles exceptions that occur during the processing of tool results
        in HITL workflows, such as parsing errors or session state updates.

        Args:
            :param e: Exception that occurred during tool result processing

        Returns:
            RunErrorEvent for the tool result processing error
        """
        record_error_log("Error handling tool results.", e)
        return RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Failed to process tool results: {repr(e)}",
            code="TOOL_RESULT_PROCESSING_ERROR",
        )

    @staticmethod
    def create_is_locked_error(thread_id: str) -> RunErrorEvent:
        """Create an error event when a thread/session is locked.

        Handles scenarios where a session is currently locked by another request
        and cannot be accessed. This occurs in concurrent access scenarios where
        session locking is used to prevent data race conditions.

        Args:
            :param thread_id: ID of the thread/session that is locked

        Returns:
            RunErrorEvent indicating the thread is locked
        """
        record_error_log(
            f"Thread {thread_id} is currently locked and cannot be accessed"
        )
        return RunErrorEvent(
            type=EventType.RUN_ERROR,
            message="Thread is currently locked",
            code="THREAD_IS_LOCKED",
        )
