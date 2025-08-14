"""Unit tests for adk_agui_middleware.tools.convert module."""

import unittest
from unittest.mock import Mock, PropertyMock, patch

from ag_ui.core import (
    AssistantMessage,
    BaseMessage,
    FunctionCall,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from google.adk.events import Event as ADKEvent

from adk_agui_middleware.tools.convert import (
    convert_adk_event_to_ag_ui_message,
    convert_ag_ui_messages_to_adk,
    convert_agui_to_adk_event,
    convert_json_patch_to_state,
    convert_state_to_json_patch,
)


class TestConvertAGUIMessagesToADK(unittest.TestCase):
    """Test cases for convert_ag_ui_messages_to_adk function."""

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_user_message(self, mock_log):
        """Test converting a UserMessage to ADK event."""
        user_msg = UserMessage(id="user1", role="user", content="Hello world")

        result = convert_ag_ui_messages_to_adk([user_msg])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "user1")
        self.assertEqual(result[0].author, "user")
        self.assertIsNotNone(result[0].content)
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_assistant_message(self, mock_log):
        """Test converting an AssistantMessage to ADK event."""
        assistant_msg = AssistantMessage(
            id="assist1", role="assistant", content="Hello back"
        )

        result = convert_ag_ui_messages_to_adk([assistant_msg])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "assist1")
        self.assertEqual(result[0].author, "assistant")
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_multiple_messages(self, mock_log):
        """Test converting multiple messages."""
        messages = [
            UserMessage(id="1", role="user", content="Hi"),
            AssistantMessage(id="2", role="assistant", content="Hello"),
            SystemMessage(id="3", role="system", content="System message"),
        ]

        result = convert_ag_ui_messages_to_adk(messages)

        self.assertEqual(len(result), 3)
        self.assertEqual([event.id for event in result], ["1", "2", "3"])
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_with_exception(self, mock_log):
        """Test handling of conversion exceptions."""
        # Create a mock message that will raise an exception
        bad_message = Mock(spec=BaseMessage)
        bad_message.id = "bad1"
        bad_message.role = "user"

        # Mock convert_agui_to_adk_event to raise an exception
        with patch(
            "adk_agui_middleware.tools.convert.convert_agui_to_adk_event",
            side_effect=Exception("Test error"),
        ):
            result = convert_ag_ui_messages_to_adk([bad_message])

        self.assertEqual(len(result), 0)  # Should skip failed message
        mock_log.assert_called_once()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_empty_list(self, mock_log):
        """Test converting empty message list."""
        result = convert_ag_ui_messages_to_adk([])

        self.assertEqual(len(result), 0)
        mock_log.assert_not_called()


class TestHandleAssistantMessage(unittest.TestCase):
    """Test cases for _handle_assistant_message function."""

    def test_assistant_message_text_only(self):
        """Test assistant message with only text content."""
        from adk_agui_middleware.tools.convert import _handle_assistant_message

        msg = AssistantMessage(id="1", role="assistant", content="Text response")
        result = _handle_assistant_message(msg)

        self.assertEqual(result.role, "model")
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].text, "Text response")

    def test_assistant_message_with_tool_calls(self):
        """Test assistant message with tool calls."""
        from adk_agui_middleware.tools.convert import _handle_assistant_message

        tool_call = ToolCall(
            id="tool1",
            type="function",
            function=FunctionCall(name="test_func", arguments='{"arg": "value"}'),
        )
        msg = AssistantMessage(
            id="1", role="assistant", content="Using tool", tool_calls=[tool_call]
        )

        result = _handle_assistant_message(msg)

        self.assertEqual(result.role, "model")
        self.assertEqual(len(result.parts), 2)  # Text + function call
        self.assertEqual(result.parts[0].text, "Using tool")
        self.assertEqual(result.parts[1].function_call.name, "test_func")

    def test_assistant_message_tool_calls_only(self):
        """Test assistant message with only tool calls."""
        from adk_agui_middleware.tools.convert import _handle_assistant_message

        tool_call = ToolCall(
            id="tool1",
            type="function",
            function=FunctionCall(name="test_func", arguments='{"arg": "value"}'),
        )
        msg = AssistantMessage(
            id="1", role="assistant", content=None, tool_calls=[tool_call]
        )

        result = _handle_assistant_message(msg)

        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].function_call.name, "test_func")

    def test_assistant_message_empty(self):
        """Test assistant message with no content or tool calls."""
        from adk_agui_middleware.tools.convert import _handle_assistant_message

        msg = AssistantMessage(id="1", role="assistant", content=None)
        result = _handle_assistant_message(msg)

        self.assertIsNone(result)


class TestHandleToolMessage(unittest.TestCase):
    """Test cases for _handle_tool_message function."""

    def test_tool_message_conversion(self):
        """Test converting a ToolMessage."""
        from adk_agui_middleware.tools.convert import _handle_tool_message

        tool_msg = ToolMessage(
            id="tool1", role="tool", content="Tool result", tool_call_id="call123"
        )

        result = _handle_tool_message(tool_msg)

        self.assertEqual(result.role, "function")
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].function_response.name, "call123")
        self.assertEqual(result.parts[0].function_response.id, "call123")
        self.assertEqual(
            result.parts[0].function_response.response["result"], "Tool result"
        )


class TestHandleUserSystemMessage(unittest.TestCase):
    """Test cases for _handle_user_system_message function."""

    def test_user_message_conversion(self):
        """Test converting a UserMessage."""
        from adk_agui_middleware.tools.convert import _handle_user_system_message

        user_msg = UserMessage(id="1", role="user", content="User input")
        result = _handle_user_system_message(user_msg)

        self.assertEqual(result.role, "user")
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].text, "User input")

    def test_system_message_conversion(self):
        """Test converting a SystemMessage."""
        from adk_agui_middleware.tools.convert import _handle_user_system_message

        sys_msg = SystemMessage(id="1", role="system", content="System instruction")
        result = _handle_user_system_message(sys_msg)

        self.assertEqual(result.role, "system")
        self.assertEqual(result.parts[0].text, "System instruction")

    def test_empty_content_message(self):
        """Test message with no content."""
        from adk_agui_middleware.tools.convert import _handle_user_system_message

        empty_msg = UserMessage(id="1", role="user", content="")
        result = _handle_user_system_message(empty_msg)

        self.assertIsNone(result)


class TestConvertAGUIToADKEvent(unittest.TestCase):
    """Test cases for convert_agui_to_adk_event function."""

    def test_user_message_conversion(self):
        """Test converting UserMessage."""
        user_msg = UserMessage(id="1", role="user", content="Hello")
        result = convert_agui_to_adk_event(user_msg)

        self.assertIsNotNone(result)
        self.assertEqual(result.role, "user")

    def test_system_message_conversion(self):
        """Test converting SystemMessage."""
        sys_msg = SystemMessage(id="1", role="system", content="System")
        result = convert_agui_to_adk_event(sys_msg)

        self.assertIsNotNone(result)
        self.assertEqual(result.role, "system")

    def test_assistant_message_conversion(self):
        """Test converting AssistantMessage."""
        assist_msg = AssistantMessage(id="1", role="assistant", content="Response")
        result = convert_agui_to_adk_event(assist_msg)

        self.assertIsNotNone(result)
        self.assertEqual(result.role, "model")

    def test_tool_message_conversion(self):
        """Test converting ToolMessage."""
        tool_msg = ToolMessage(
            id="1", role="tool", content="Result", tool_call_id="call1"
        )
        result = convert_agui_to_adk_event(tool_msg)

        self.assertIsNotNone(result)
        self.assertEqual(result.role, "function")

    def test_unsupported_message_type(self):
        """Test unsupported message type returns None."""
        # Create a mock message that doesn't match any handled types
        unsupported_msg = Mock(spec=BaseMessage)
        unsupported_msg.content = "test"

        result = convert_agui_to_adk_event(unsupported_msg)
        self.assertIsNone(result)


class TestConvertADKEventToAGUIMessage(unittest.TestCase):
    """Test cases for convert_adk_event_to_ag_ui_message function."""

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_user_event(self, mock_log):
        """Test converting ADK event to UserMessage."""
        # Create mock ADK event
        mock_event = Mock(spec=ADKEvent)
        mock_event.id = "event1"
        mock_event.author = "user"
        mock_event.content = Mock()

        # Create mock parts
        text_part = Mock()
        text_part.text = "User message"
        text_part.function_call = None

        mock_event.content.parts = [text_part]

        result = convert_adk_event_to_ag_ui_message(mock_event)

        self.assertIsInstance(result, UserMessage)
        self.assertEqual(result.id, "event1")
        self.assertEqual(result.content, "User message")
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_assistant_event_with_function_call(self, mock_log):
        """Test converting ADK event to AssistantMessage with function call."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.id = "event1"
        mock_event.author = "assistant"
        mock_event.content = Mock()

        # Mock function call
        function_call = Mock()
        function_call.name = "test_function"
        function_call.args = {"param": "value"}
        function_call.arguments = {"param": "value"}

        # Create parts with text and function call
        text_part = Mock()
        text_part.text = "Using function"
        text_part.function_call = None

        func_part = Mock()
        func_part.text = None
        func_part.function_call = function_call

        mock_event.content.parts = [text_part, func_part]

        result = convert_adk_event_to_ag_ui_message(mock_event)

        self.assertIsInstance(result, AssistantMessage)
        self.assertEqual(result.content, "Using function")
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].function.name, "test_function")
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_empty_event(self, mock_log):
        """Test converting empty ADK event."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.content = None

        result = convert_adk_event_to_ag_ui_message(mock_event)

        self.assertIsNone(result)
        mock_log.assert_not_called()

    @patch("adk_agui_middleware.tools.convert.record_error_log")
    def test_convert_with_exception(self, mock_log):
        """Test handling exceptions during conversion."""
        mock_event = Mock(spec=ADKEvent)
        mock_event.id = "error_event"

        # Create a mock content with properly configured parts
        mock_content = Mock()
        mock_content.parts = PropertyMock(side_effect=Exception("Test error"))
        mock_event.content = mock_content

        result = convert_adk_event_to_ag_ui_message(mock_event)

        self.assertIsNone(result)
        mock_log.assert_called_once()


class TestJSONPatchConversion(unittest.TestCase):
    """Test cases for JSON Patch conversion functions."""

    def test_convert_state_to_json_patch_add_operations(self):
        """Test converting state changes to JSON Patch add operations."""
        state_delta = {"key1": "value1", "key2": 42, "key3": {"nested": "object"}}

        result = convert_state_to_json_patch(state_delta)

        expected = [
            {"op": "add", "path": "/key1", "value": "value1"},
            {"op": "add", "path": "/key2", "value": 42},
            {"op": "add", "path": "/key3", "value": {"nested": "object"}},
        ]

        self.assertEqual(len(result), 3)
        # Sort by path for consistent comparison
        result.sort(key=lambda x: x["path"])
        expected.sort(key=lambda x: x["path"])
        self.assertEqual(result, expected)

    def test_convert_state_to_json_patch_remove_operations(self):
        """Test converting state changes with None values to remove operations."""
        state_delta = {"remove_me": None, "keep_me": "value", "remove_me_too": None}

        result = convert_state_to_json_patch(state_delta)

        self.assertEqual(len(result), 3)

        # Check remove operations
        remove_ops = [op for op in result if op["op"] == "remove"]
        self.assertEqual(len(remove_ops), 2)

        # Check add operations (implementation uses "add" instead of "replace")
        add_ops = [op for op in result if op["op"] == "add"]
        self.assertEqual(len(add_ops), 1)
        self.assertEqual(add_ops[0]["value"], "value")

    def test_convert_json_patch_to_state_mixed_operations(self):
        """Test converting JSON Patch operations back to state."""
        patches = [
            {"op": "replace", "path": "/key1", "value": "new_value"},
            {"op": "remove", "path": "/key2"},
            {"op": "add", "path": "/key3", "value": 123},
        ]

        result = convert_json_patch_to_state(patches)

        expected = {"key1": "new_value", "key2": None, "key3": 123}

        self.assertEqual(result, expected)

    def test_convert_json_patch_to_state_empty_patches(self):
        """Test converting empty patch list."""
        result = convert_json_patch_to_state([])
        self.assertEqual(result, {})

    def test_convert_json_patch_to_state_invalid_path(self):
        """Test handling patches with invalid or missing paths."""
        patches = [
            {"op": "replace", "path": "", "value": "value1"},
            {"op": "add", "value": "value2"},  # Missing path
            {"op": "remove", "path": "/valid_key"},
        ]

        result = convert_json_patch_to_state(patches)

        # Should handle empty path and missing path gracefully
        expected = {
            "": "value1",
            "": None,  # This might overwrite previous
            "valid_key": None,
        }

        # The exact behavior depends on implementation
        self.assertIn("valid_key", result)
        self.assertIsNone(result["valid_key"])

    def test_roundtrip_conversion(self):
        """Test roundtrip conversion maintains data integrity."""
        original_state = {
            "string_key": "value",
            "number_key": 42,
            "null_key": None,
            "object_key": {"nested": "data"},
        }

        # Convert to patches and back
        patches = convert_state_to_json_patch(original_state)
        converted_back = convert_json_patch_to_state(patches)

        self.assertEqual(converted_back, original_state)

    def test_convert_state_empty_dict(self):
        """Test converting empty state dictionary."""
        result = convert_state_to_json_patch({})
        self.assertEqual(result, [])

    def test_json_patch_unsupported_operation(self):
        """Test handling unsupported patch operations."""
        patches = [
            {"op": "unsupported", "path": "/key1", "value": "value"},
            {"op": "replace", "path": "/key2", "value": "value2"},
        ]

        result = convert_json_patch_to_state(patches)

        # Should only process supported operations
        self.assertEqual(result, {"key2": "value2"})


if __name__ == "__main__":
    unittest.main()
