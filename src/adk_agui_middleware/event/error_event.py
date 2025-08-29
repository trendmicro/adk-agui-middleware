"""Error event classes for handling encoding and execution errors in AGUI middleware."""

from ag_ui.core import EventType, RunErrorEvent

from ..loggers.record_log import record_error_log
from ..tools.convert import convert_agui_event_to_sse


class AGUIEncoderError(Exception):
    """Exception class providing static methods for encoding error events.

    Handles encoding errors and agent execution errors by creating appropriate
    error events and logging the issues.
    """

    @staticmethod
    def create_encoding_error_event(e: Exception) -> dict[str, str]:
        """Create an encoded error event for encoding failures.

        Args:
            e: Original exception that caused the encoding failure

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

        Args:
            e: Original exception that caused the agent failure

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
    error scenarios in AGUI middleware execution.
    """

    @staticmethod
    def create_execution_error_event(e: Exception) -> RunErrorEvent:
        """Create an error event for general execution failures.

        Args:
            e: Exception that caused the execution failure

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

        Args:
            thread_id: ID of the thread where tool results were expected

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
    def create_tool_processing_error_event(e: Exception) -> RunErrorEvent:
        """Create an error event for tool result processing failures.

        Args:
            e: Exception that occurred during tool result processing

        Returns:
            RunErrorEvent for the tool result processing error
        """
        record_error_log("Error handling tool results.", e)
        return RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Failed to process tool results: {repr(e)}",
            code="TOOL_RESULT_PROCESSING_ERROR",
        )
