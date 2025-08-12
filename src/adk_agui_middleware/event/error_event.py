"""Error event classes for handling encoding and execution errors in AGUI middleware."""

from ag_ui.core import EventType, RunErrorEvent
from ag_ui.encoder import EventEncoder
from loggers.record_log import record_error_log


class AGUIEncoderError(Exception):
    """Exception class providing static methods for encoding error events.

    Handles encoding errors and agent execution errors by creating appropriate
    error events and logging the issues.
    """

    @staticmethod
    def encoding_error(encoder: EventEncoder, e: Exception) -> str:
        """Create an encoded error event for encoding failures.

        Args:
            encoder: Event encoder to use for encoding the error event
            e: Original exception that caused the encoding failure

        Returns:
            Encoded error event string
        """
        error_event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Event encoding failed: {repr(e)}",
            code="ENCODING_ERROR",
        )
        record_error_log("Event encoding failed", e)
        return encoder.encode(error_event)

    @staticmethod
    def agent_error(encoder: EventEncoder, e: Exception) -> str:
        """Create an encoded error event for agent execution failures.

        Args:
            encoder: Event encoder to use for encoding the error event
            e: Original exception that caused the agent failure

        Returns:
            Encoded error event string
        """
        error_event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Agent execution failed: {repr(e)}",
            code="AGENT_ERROR",
        )
        record_error_log("AGUI Agent Error Handler", e)
        return encoder.encode(error_event)


class AGUIErrorEvent:
    """Utility class for creating specific types of AGUI error events.

    Provides static methods for creating RunErrorEvent objects for common
    error scenarios in AGUI middleware execution.
    """

    @staticmethod
    def execution_error(e: Exception) -> RunErrorEvent:
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
    def no_tool_results(thread_id: str) -> RunErrorEvent:
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
    def tool_result_processing_error(e: Exception) -> RunErrorEvent:
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
