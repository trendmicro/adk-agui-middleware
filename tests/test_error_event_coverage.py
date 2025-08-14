"""Additional tests for error_event.py to boost coverage."""

from unittest.mock import Mock, patch

from ag_ui.core import EventType, RunErrorEvent
from ag_ui.encoder import EventEncoder

from adk_agui_middleware.event.error_event import AGUIEncoderError, AGUIErrorEvent

from .test_utils import BaseTestCase


class TestErrorEventCoverage(BaseTestCase):
    """Additional tests for error event handling to improve coverage."""

    def test_agui_encoder_error_encoding_error(self):
        """Test AGUIEncoderError.encoding_error method."""
        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.encode.return_value = "encoded_error_response"

        test_exception = RuntimeError("Encoding failed")

        with patch(
            "adk_agui_middleware.event.error_event.record_error_log"
        ) as mock_log:
            result = AGUIEncoderError.encoding_error(mock_encoder, test_exception)

            assert result == "encoded_error_response"
            mock_log.assert_called_once_with("Event encoding failed", test_exception)

            # Verify encoder was called with correct event
            mock_encoder.encode.assert_called_once()
            call_args = mock_encoder.encode.call_args[0]
            error_event = call_args[0]

            assert isinstance(error_event, RunErrorEvent)
            assert error_event.type == EventType.RUN_ERROR
            assert "Event encoding failed" in error_event.message
            assert "RuntimeError" in error_event.message
            assert error_event.code == "ENCODING_ERROR"

    def test_agui_encoder_error_agent_error(self):
        """Test AGUIEncoderError.agent_error method."""
        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.encode.return_value = "encoded_agent_error"

        test_exception = ValueError("Agent execution failed")

        with patch(
            "adk_agui_middleware.event.error_event.record_error_log"
        ) as mock_log:
            result = AGUIEncoderError.agent_error(mock_encoder, test_exception)

            assert result == "encoded_agent_error"
            mock_log.assert_called_once_with("AGUI Agent Error Handler", test_exception)

            # Verify encoder was called with correct event
            mock_encoder.encode.assert_called_once()
            call_args = mock_encoder.encode.call_args[0]
            error_event = call_args[0]

            assert isinstance(error_event, RunErrorEvent)
            assert error_event.type == EventType.RUN_ERROR
            assert "Agent execution failed" in error_event.message
            assert "ValueError" in error_event.message
            assert error_event.code == "AGENT_ERROR"

    def test_agui_error_event_execution_error(self):
        """Test AGUIErrorEvent.execution_error method."""
        test_exception = ConnectionError("Network connection failed")

        with patch(
            "adk_agui_middleware.event.error_event.record_error_log"
        ) as mock_log:
            result = AGUIErrorEvent.execution_error(test_exception)

            assert isinstance(result, RunErrorEvent)
            assert result.type == EventType.RUN_ERROR
            assert "ConnectionError" in result.message
            assert "Network connection failed" in result.message
            assert result.code == "EXECUTION_ERROR"

            mock_log.assert_called_once_with("Error in new execution", test_exception)

    def test_agui_error_event_no_tool_results(self):
        """Test AGUIErrorEvent.no_tool_results method."""
        thread_id = "test_thread_12345"

        with patch(
            "adk_agui_middleware.event.error_event.record_error_log"
        ) as mock_log:
            result = AGUIErrorEvent.no_tool_results(thread_id)

            assert isinstance(result, RunErrorEvent)
            assert result.type == EventType.RUN_ERROR
            assert "No tool results found in submission" in result.message
            assert result.code == "NO_TOOL_RESULTS"

            expected_log_message = (
                f"Tool result submission without tool results for thread {thread_id}"
            )
            mock_log.assert_called_once_with(expected_log_message)

    def test_agui_error_event_tool_result_processing_error(self):
        """Test AGUIErrorEvent.tool_result_processing_error method."""
        test_exception = KeyError("Missing tool result key")

        with patch(
            "adk_agui_middleware.event.error_event.record_error_log"
        ) as mock_log:
            result = AGUIErrorEvent.tool_result_processing_error(test_exception)

            assert isinstance(result, RunErrorEvent)
            assert result.type == EventType.RUN_ERROR
            assert "Failed to process tool results" in result.message
            assert "KeyError" in result.message
            assert "Missing tool result key" in result.message
            assert result.code == "TOOL_RESULT_PROCESSING_ERROR"

            mock_log.assert_called_once_with(
                "Error handling tool results.", test_exception
            )

    def test_encoder_error_with_complex_exception(self):
        """Test encoder error with complex exception structure."""
        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.encode.return_value = "complex_error_encoded"

        # Create nested exception
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        except RuntimeError as complex_exception:
            with patch("adk_agui_middleware.event.error_event.record_error_log"):
                result = AGUIEncoderError.encoding_error(
                    mock_encoder, complex_exception
                )

                assert result == "complex_error_encoded"
                # Should handle complex exception representations
                call_args = mock_encoder.encode.call_args[0]
                error_event = call_args[0]
                assert "RuntimeError" in error_event.message

    def test_agent_error_with_custom_exception(self):
        """Test agent error with custom exception class."""

        class CustomAgentException(Exception):
            def __init__(self, code, message):
                self.code = code
                self.message = message
                super().__init__(f"{code}: {message}")

        mock_encoder = Mock(spec=EventEncoder)
        mock_encoder.encode.return_value = "custom_error_encoded"

        custom_exception = CustomAgentException(
            "AGENT_TIMEOUT", "Agent took too long to respond"
        )

        with patch("adk_agui_middleware.event.error_event.record_error_log"):
            result = AGUIEncoderError.agent_error(mock_encoder, custom_exception)

            assert result == "custom_error_encoded"
            call_args = mock_encoder.encode.call_args[0]
            error_event = call_args[0]
            assert "CustomAgentException" in error_event.message
            assert "AGENT_TIMEOUT" in error_event.message

    def test_execution_error_with_none_exception(self):
        """Test execution error handling with None exception."""
        with patch(
            "adk_agui_middleware.event.error_event.record_error_log"
        ) as mock_log:
            result = AGUIErrorEvent.execution_error(None)

            assert isinstance(result, RunErrorEvent)
            assert result.type == EventType.RUN_ERROR
            assert result.message == "None"
            assert result.code == "EXECUTION_ERROR"

            mock_log.assert_called_once_with("Error in new execution", None)

    def test_tool_result_processing_with_unicode_error(self):
        """Test tool result processing error with unicode characters."""
        unicode_exception = UnicodeDecodeError(
            "utf-8", b"\xff\xfe", 0, 2, "invalid start byte"
        )

        with patch(
            "adk_agui_middleware.event.error_event.record_error_log"
        ) as mock_log:
            result = AGUIErrorEvent.tool_result_processing_error(unicode_exception)

            assert isinstance(result, RunErrorEvent)
            assert result.type == EventType.RUN_ERROR
            assert "Failed to process tool results" in result.message
            assert "UnicodeDecodeError" in result.message
            assert result.code == "TOOL_RESULT_PROCESSING_ERROR"

            mock_log.assert_called_once_with(
                "Error handling tool results.", unicode_exception
            )

    def test_no_tool_results_with_various_thread_ids(self):
        """Test no_tool_results with various thread ID formats."""
        test_cases = [
            "simple_thread",
            "thread-with-dashes",
            "thread_with_underscores",
            "thread123with456numbers",
            "thread.with.dots",
            "thread/with/slashes",
        ]

        for thread_id in test_cases:
            with patch(
                "adk_agui_middleware.event.error_event.record_error_log"
            ) as mock_log:
                result = AGUIErrorEvent.no_tool_results(thread_id)

                assert isinstance(result, RunErrorEvent)
                assert result.type == EventType.RUN_ERROR
                assert result.code == "NO_TOOL_RESULTS"

                # Verify thread_id is included in log message
                expected_log = f"Tool result submission without tool results for thread {thread_id}"
                mock_log.assert_called_once_with(expected_log)

    def test_error_message_formatting(self):
        """Test error message formatting consistency."""
        test_exception = FileNotFoundError("config.json not found")

        with patch("adk_agui_middleware.event.error_event.record_error_log"):
            # Test execution error formatting
            execution_result = AGUIErrorEvent.execution_error(test_exception)
            assert execution_result.message == repr(test_exception)

            # Test tool processing error formatting
            processing_result = AGUIErrorEvent.tool_result_processing_error(
                test_exception
            )
            assert (
                f"Failed to process tool results: {repr(test_exception)}"
                == processing_result.message
            )

    def test_event_type_consistency(self):
        """Test that all error events use consistent event type."""
        test_exception = RuntimeError("Test error")

        with patch("adk_agui_middleware.event.error_event.record_error_log"):
            execution_event = AGUIErrorEvent.execution_error(test_exception)
            no_results_event = AGUIErrorEvent.no_tool_results("test_thread")
            processing_event = AGUIErrorEvent.tool_result_processing_error(
                test_exception
            )

            # All should use RUN_ERROR type
            assert execution_event.type == EventType.RUN_ERROR
            assert no_results_event.type == EventType.RUN_ERROR
            assert processing_event.type == EventType.RUN_ERROR

    def test_error_codes_uniqueness(self):
        """Test that different error types have unique codes."""
        test_exception = RuntimeError("Test error")

        with patch("adk_agui_middleware.event.error_event.record_error_log"):
            execution_event = AGUIErrorEvent.execution_error(test_exception)
            no_results_event = AGUIErrorEvent.no_tool_results("test_thread")
            processing_event = AGUIErrorEvent.tool_result_processing_error(
                test_exception
            )

            # All should have different codes
            codes = {execution_event.code, no_results_event.code, processing_event.code}
            assert len(codes) == 3  # All unique

            expected_codes = {
                "EXECUTION_ERROR",
                "NO_TOOL_RESULTS",
                "TOOL_RESULT_PROCESSING_ERROR",
            }
            assert codes == expected_codes
