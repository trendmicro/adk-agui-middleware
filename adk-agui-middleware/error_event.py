from ag_ui.core import EventType, RunErrorEvent
from ag_ui.encoder import EventEncoder

from loggers.record_log import record_error_log


class AGUIEncoderError(Exception):
    @staticmethod
    def encoding_error(encoder: EventEncoder, e: Exception) -> str:
        error_event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Event encoding failed: {repr(e)}",
            code="ENCODING_ERROR",
        )
        record_error_log("Event encoding failed", e)
        return encoder.encode(error_event)

    @staticmethod
    def agent_error(encoder: EventEncoder, e: Exception) -> str:
        error_event = RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Agent execution failed: {repr(e)}",
            code="AGENT_ERROR",
        )
        record_error_log("AGUI Agent Error Handler", e)
        return encoder.encode(error_event)


class AGUIErrorEvent:
    @staticmethod
    def execution_error(e: Exception) -> RunErrorEvent:
        record_error_log("Error in new execution", e)
        return RunErrorEvent(
            type=EventType.RUN_ERROR, message=repr(e), code="EXECUTION_ERROR"
        )

    @staticmethod
    def no_tool_results(thread_id: str) -> RunErrorEvent:
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
        record_error_log("Error handling tool results.", e)
        return RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=f"Failed to process tool results: {repr(e)}",
            code="TOOL_RESULT_PROCESSING_ERROR",
        )
