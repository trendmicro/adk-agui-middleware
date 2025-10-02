# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Comprehensive unit tests for adk_agui_middleware.utils.convert.agui_event_list_to_message_list module.

This test suite provides extensive coverage for the AGUIEventListToMessageListConverter class,
including edge cases, message accumulation, and complex conversation scenarios.
"""

from typing import Any, List
from unittest.mock import Mock

import pytest
from ag_ui.core import (
    BaseEvent,
    TextMessageContentEvent,
    ToolCallArgsEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.core.types import (
    AssistantMessage,
    FunctionCall,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)

from adk_agui_middleware.event.agui_event import CustomThinkingTextMessageContentEvent
from adk_agui_middleware.event.agui_type import Message, ThinkingMessage
from adk_agui_middleware.utils.convert.agui_event_list_to_message_list import (
    AGUIEventListToMessageListConverter,
)


class TestADKEventToAGUIMessageConverter:
    """Comprehensive tests for AGUIEventListToMessageListConverter class."""

    @pytest.fixture
    def converter(self) -> AGUIEventListToMessageListConverter:
        """Create a fresh converter instance for each test."""
        return AGUIEventListToMessageListConverter()

    # ========== Constructor and Basic Setup Tests ==========

    def test_init(self, converter: AGUIEventListToMessageListConverter):
        """Test converter initialization."""
        assert converter.accumulator == {}

    def test_accumulator_isolation(self):
        """Test that different converter instances have isolated accumulators."""
        converter1 = AGUIEventListToMessageListConverter()
        converter2 = AGUIEventListToMessageListConverter()

        converter1.accumulator["test"] = {"type": "message", "content": "test1"}
        assert "test" not in converter2.accumulator

    # ========== Content Appending Tests ==========

    def test_append_content_new_key(self, converter: AGUIEventListToMessageListConverter):
        """Test appending content to a new key."""
        converter._append_content("msg-1", "message", "Hello")

        assert "msg-1" in converter.accumulator
        assert converter.accumulator["msg-1"]["type"] == "message"
        assert converter.accumulator["msg-1"]["content"] == "Hello"

    def test_append_content_existing_key(self, converter: AGUIEventListToMessageListConverter):
        """Test appending content to an existing key."""
        converter._append_content("msg-1", "message", "Hello ")
        converter._append_content("msg-1", "message", "world!")

        assert converter.accumulator["msg-1"]["content"] == "Hello world!"

    def test_append_content_different_keys(self, converter: AGUIEventListToMessageListConverter):
        """Test appending content to different keys."""
        converter._append_content("msg-1", "message", "First message")
        converter._append_content("msg-2", "thinking", "Second message")

        assert len(converter.accumulator) == 2
        assert converter.accumulator["msg-1"]["content"] == "First message"
        assert converter.accumulator["msg-2"]["content"] == "Second message"
        assert converter.accumulator["msg-1"]["type"] == "message"
        assert converter.accumulator["msg-2"]["type"] == "thinking"

    def test_append_content_empty_delta(self, converter: AGUIEventListToMessageListConverter):
        """Test appending empty content delta."""
        converter._append_content("msg-1", "message", "")

        assert converter.accumulator["msg-1"]["content"] == ""

    def test_append_content_special_characters(self, converter: AGUIEventListToMessageListConverter):
        """Test appending content with special characters."""
        special_text = "测试🌟\n\t<>&\"'"
        converter._append_content("msg-1", "message", special_text)

        assert converter.accumulator["msg-1"]["content"] == special_text

    # ========== Tool Initialization Tests ==========

    def test_init_tool_new_key(self, converter: AGUIEventListToMessageListConverter):
        """Test initializing a new tool call."""
        converter._init_tool("tool-1")

        assert "tool-1" in converter.accumulator
        assert converter.accumulator["tool-1"]["type"] == "tool"
        assert converter.accumulator["tool-1"]["name"] == ""
        assert converter.accumulator["tool-1"]["arg"] == ""

    def test_init_tool_existing_key(self, converter: AGUIEventListToMessageListConverter):
        """Test initializing tool call for existing key (should not overwrite)."""
        converter.accumulator["tool-1"] = {"type": "tool", "name": "existing", "arg": "data"}
        converter._init_tool("tool-1")

        # Should not overwrite existing data
        assert converter.accumulator["tool-1"]["name"] == "existing"
        assert converter.accumulator["tool-1"]["arg"] == "data"

    def test_init_tool_multiple_tools(self, converter: AGUIEventListToMessageListConverter):
        """Test initializing multiple tool calls."""
        converter._init_tool("tool-1")
        converter._init_tool("tool-2")

        assert len(converter.accumulator) == 2
        assert "tool-1" in converter.accumulator
        assert "tool-2" in converter.accumulator

    # ========== Event Classification Tests ==========

    def test_classify_thinking_content_event(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying thinking content events."""
        thinking_event = CustomThinkingTextMessageContentEvent(
            thinking_id="think-123",
            delta="I need to think about this..."
        )

        converter._classify_and_merge([thinking_event])

        assert "think-123" in converter.accumulator
        assert converter.accumulator["think-123"]["type"] == "thinking"
        assert converter.accumulator["think-123"]["content"] == "I need to think about this..."

    def test_classify_text_message_content_event(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying text message content events."""
        text_event = TextMessageContentEvent(
            message_id="msg-456",
            delta="Hello, world!"
        )

        converter._classify_and_merge([text_event])

        assert "msg-456" in converter.accumulator
        assert converter.accumulator["msg-456"]["type"] == "message"
        assert converter.accumulator["msg-456"]["content"] == "Hello, world!"

    def test_classify_tool_call_args_event(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying tool call args events."""
        args_event = ToolCallArgsEvent(
            tool_call_id="tool-789",
            delta='{"param": "value"}'
        )

        converter._classify_and_merge([args_event])

        assert "tool-789" in converter.accumulator
        assert converter.accumulator["tool-789"]["type"] == "tool"
        assert converter.accumulator["tool-789"]["arg"] == '{"param": "value"}'

    def test_classify_tool_call_start_event(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying tool call start events."""
        start_event = ToolCallStartEvent(
            tool_call_id="tool-abc",
            tool_call_name="test_function"
        )

        converter._classify_and_merge([start_event])

        assert "tool-abc" in converter.accumulator
        assert converter.accumulator["tool-abc"]["type"] == "tool"
        assert converter.accumulator["tool-abc"]["name"] == "test_function"

    def test_classify_user_message(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying user messages."""
        user_msg = UserMessage(
            id="user-123",
            role="user",
            content="User's question"
        )

        converter._classify_and_merge([user_msg])

        assert "user-123" in converter.accumulator
        assert converter.accumulator["user-123"]["type"] == "user"
        assert converter.accumulator["user-123"]["content"] == user_msg

    def test_classify_system_message(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying system messages."""
        system_msg = SystemMessage(
            id="system-456",
            role="system",
            content="System instruction"
        )

        converter._classify_and_merge([system_msg])

        assert "system-456" in converter.accumulator
        assert converter.accumulator["system-456"]["type"] == "system"
        assert converter.accumulator["system-456"]["content"] == system_msg

    def test_classify_tool_call_result_event(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying tool call result events."""
        result_event = ToolCallResultEvent(
            tool_call_id="tool-result-123",
            message_id="msg-789",
            content="Function execution result"
        )

        converter._classify_and_merge([result_event])

        result_key = "tool-result-123_result"
        assert result_key in converter.accumulator
        assert converter.accumulator[result_key]["type"] == "tool_result"
        assert converter.accumulator[result_key]["content"] == "Function execution result"
        assert converter.accumulator[result_key]["tool_call_id"] == "tool-result-123"
        assert converter.accumulator[result_key]["message_id"] == "msg-789"

    # ========== Complex Event Sequences ==========

    def test_classify_streaming_text_message(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying a sequence of streaming text events."""
        events = [
            TextMessageContentEvent(message_id="stream-1", delta="Hello "),
            TextMessageContentEvent(message_id="stream-1", delta="streaming "),
            TextMessageContentEvent(message_id="stream-1", delta="world!")
        ]

        converter._classify_and_merge(events)

        assert converter.accumulator["stream-1"]["content"] == "Hello streaming world!"

    def test_classify_complete_tool_call_sequence(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying a complete tool call sequence."""
        events = [
            ToolCallStartEvent(tool_call_id="complete-tool", tool_call_name="calculate"),
            ToolCallArgsEvent(tool_call_id="complete-tool", delta='{"operation": "add", '),
            ToolCallArgsEvent(tool_call_id="complete-tool", delta='"numbers": [1, 2, 3]}'),
        ]

        converter._classify_and_merge(events)

        assert converter.accumulator["complete-tool"]["name"] == "calculate"
        assert converter.accumulator["complete-tool"]["arg"] == '{"operation": "add", "numbers": [1, 2, 3]}'

    def test_classify_mixed_event_types(self, converter: AGUIEventListToMessageListConverter):
        """Test classifying mixed event types in sequence."""
        user_msg = UserMessage(id="user-1", role="user", content="Calculate 2+2")

        events = [
            user_msg,
            TextMessageContentEvent(message_id="assistant-1", delta="I'll calculate that for you."),
            ToolCallStartEvent(tool_call_id="calc-1", tool_call_name="add"),
            ToolCallArgsEvent(tool_call_id="calc-1", delta='{"a": 2, "b": 2}'),
            ToolCallResultEvent(tool_call_id="calc-1", message_id="result-1", content="4"),
            CustomThinkingTextMessageContentEvent(thinking_id="think-1", delta="The result is 4"),
        ]

        converter._classify_and_merge(events)

        assert len(converter.accumulator) == 5
        assert "user-1" in converter.accumulator
        assert "assistant-1" in converter.accumulator
        assert "calc-1" in converter.accumulator
        assert "calc-1_result" in converter.accumulator
        assert "think-1" in converter.accumulator

    # ========== Message Creation Tests ==========

    def test_create_thinking_message(self, converter: AGUIEventListToMessageListConverter):
        """Test creating thinking message from accumulated data."""
        data = {"type": "thinking", "content": "Thinking content"}

        result = converter._create_message("think-id", data)

        assert isinstance(result, ThinkingMessage)
        assert result.role == "thinking"
        assert result.id == "think-id"
        assert result.content == "Thinking content"

    def test_create_assistant_message(self, converter: AGUIEventListToMessageListConverter):
        """Test creating assistant message from accumulated data."""
        data = {"type": "message", "content": "Assistant response"}

        result = converter._create_message("msg-id", data)

        assert isinstance(result, AssistantMessage)
        assert result.role == "assistant"
        assert result.id == "msg-id"
        assert result.content == "Assistant response"

    def test_create_user_message(self, converter: AGUIEventListToMessageListConverter):
        """Test creating user message from accumulated data."""
        original_msg = UserMessage(id="user-1", role="user", content="User content")
        data = {"type": "user", "content": original_msg}

        result = converter._create_message("user-id", data)

        assert result == original_msg
        assert isinstance(result, UserMessage)

    def test_create_system_message(self, converter: AGUIEventListToMessageListConverter):
        """Test creating system message from accumulated data."""
        original_msg = SystemMessage(id="sys-1", role="system", content="System content")
        data = {"type": "system", "content": original_msg}

        result = converter._create_message("sys-id", data)

        assert result == original_msg
        assert isinstance(result, SystemMessage)

    def test_create_tool_call_message(self, converter: AGUIEventListToMessageListConverter):
        """Test creating tool call message from accumulated data."""
        data = {
            "type": "tool",
            "name": "test_function",
            "arg": '{"param": "value"}'
        }

        result = converter._create_message("tool-id", data)

        assert isinstance(result, AssistantMessage)
        assert result.role == "assistant"
        assert result.id == "tool-id"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tool-id"
        assert result.tool_calls[0].function.name == "test_function"
        assert result.tool_calls[0].function.arguments == '{"param": "value"}'

    def test_create_tool_result_message(self, converter: AGUIEventListToMessageListConverter):
        """Test creating tool result message from accumulated data."""
        data = {
            "type": "tool_result",
            "content": "Tool execution result",
            "tool_call_id": "tool-123",
            "message_id": "msg-456"
        }

        result = converter._create_message("result-id", data)

        assert isinstance(result, ToolMessage)
        assert result.role == "tool"
        assert result.id == "msg-456"
        assert result.tool_call_id == "tool-123"
        assert result.content == "Tool execution result"

    def test_create_unknown_message_type(self, converter: AGUIEventListToMessageListConverter):
        """Test creating message with unknown type."""
        data = {"type": "unknown", "content": "Unknown content"}

        result = converter._create_message("unknown-id", data)

        assert result is None

    # ========== Full Conversion Tests ==========

    def test_convert_empty_list(self, converter: AGUIEventListToMessageListConverter):
        """Test converting empty event list."""
        result = converter.convert([])

        assert result == []
        assert converter.accumulator == {}

    def test_convert_single_text_event(self, converter: AGUIEventListToMessageListConverter):
        """Test converting single text message event."""
        events = [TextMessageContentEvent(message_id="single", delta="Single message")]

        result = converter.convert(events)

        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)
        assert result[0].content == "Single message"

    def test_convert_conversation_sequence(self, converter: AGUIEventListToMessageListConverter):
        """Test converting a complete conversation sequence."""
        user_msg = UserMessage(id="user-1", role="user", content="Hello")

        events = [
            user_msg,
            TextMessageContentEvent(message_id="assistant-1", delta="Hi there! "),
            TextMessageContentEvent(message_id="assistant-1", delta="How can I help?"),
            CustomThinkingTextMessageContentEvent(thinking_id="think-1", delta="User is greeting me")
        ]

        result = converter.convert(events)

        assert len(result) == 3

        # Check that we have user, assistant, and thinking messages
        message_types = {type(msg).__name__ for msg in result}
        assert "UserMessage" in message_types
        assert "AssistantMessage" in message_types
        assert "ThinkingMessage" in message_types

    def test_convert_tool_call_workflow(self, converter: AGUIEventListToMessageListConverter):
        """Test converting complete tool call workflow."""
        events = [
            ToolCallStartEvent(tool_call_id="workflow-1", tool_call_name="process_data"),
            ToolCallArgsEvent(tool_call_id="workflow-1", delta='{"input": "data"}'),
            ToolCallResultEvent(tool_call_id="workflow-1", message_id="result-1", content="Processed successfully")
        ]

        result = converter.convert(events)

        assert len(result) == 2

        # Should have an AssistantMessage with tool call and a ToolMessage with result
        tool_call_msg = next((msg for msg in result if hasattr(msg, 'tool_calls')), None)
        tool_result_msg = next((msg for msg in result if isinstance(msg, ToolMessage)), None)

        assert tool_call_msg is not None
        assert tool_result_msg is not None
        assert len(tool_call_msg.tool_calls) == 1
        assert tool_result_msg.content == "Processed successfully"

    # ========== Edge Cases and Error Handling ==========

    def test_convert_duplicate_message_ids(self, converter: AGUIEventListToMessageListConverter):
        """Test handling events with duplicate message IDs."""
        events = [
            TextMessageContentEvent(message_id="duplicate", delta="First "),
            TextMessageContentEvent(message_id="duplicate", delta="Second "),
            TextMessageContentEvent(message_id="duplicate", delta="Third")
        ]

        result = converter.convert(events)

        assert len(result) == 1
        assert result[0].content == "First Second Third"

    def test_convert_interleaved_events(self, converter: AGUIEventListToMessageListConverter):
        """Test converting interleaved events for different messages."""
        events = [
            TextMessageContentEvent(message_id="msg-1", delta="Message 1 part 1 "),
            TextMessageContentEvent(message_id="msg-2", delta="Message 2 part 1 "),
            TextMessageContentEvent(message_id="msg-1", delta="Message 1 part 2"),
            TextMessageContentEvent(message_id="msg-2", delta="Message 2 part 2")
        ]

        result = converter.convert(events)

        assert len(result) == 2

        # Find messages by content
        msg1 = next(msg for msg in result if "Message 1" in msg.content)
        msg2 = next(msg for msg in result if "Message 2" in msg.content)

        assert msg1.content == "Message 1 part 1 Message 1 part 2"
        assert msg2.content == "Message 2 part 1 Message 2 part 2"

    def test_convert_incomplete_tool_call(self, converter: AGUIEventListToMessageListConverter):
        """Test converting incomplete tool call (missing args or name)."""
        events = [
            ToolCallStartEvent(tool_call_id="incomplete", tool_call_name="incomplete_function")
            # Missing ToolCallArgsEvent
        ]

        result = converter.convert(events)

        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)
        assert len(result[0].tool_calls) == 1
        assert result[0].tool_calls[0].function.name == "incomplete_function"
        assert result[0].tool_calls[0].function.arguments == ""

    def test_convert_orphaned_tool_args(self, converter: AGUIEventListToMessageListConverter):
        """Test converting tool args without start event."""
        events = [
            ToolCallArgsEvent(tool_call_id="orphaned", delta='{"orphaned": "args"}')
            # Missing ToolCallStartEvent
        ]

        result = converter.convert(events)

        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)
        assert len(result[0].tool_calls) == 1
        assert result[0].tool_calls[0].function.name == ""  # No name set
        assert result[0].tool_calls[0].function.arguments == '{"orphaned": "args"}'

    def test_convert_large_message_content(self, converter: AGUIEventListToMessageListConverter):
        """Test converting very large message content."""
        large_content = "Large content " * 1000  # ~13k characters
        events = [TextMessageContentEvent(message_id="large", delta=large_content)]

        result = converter.convert(events)

        assert len(result) == 1
        assert len(result[0].content) == len(large_content)
        assert result[0].content == large_content

    def test_convert_special_characters_in_content(self, converter: AGUIEventListToMessageListConverter):
        """Test converting content with special characters."""
        special_content = "Special: 🌟测试\n\t<script>alert('xss')</script>"
        events = [TextMessageContentEvent(message_id="special", delta=special_content)]

        result = converter.convert(events)

        assert len(result) == 1
        assert result[0].content == special_content

    def test_convert_multiple_tool_calls_same_message(self, converter: AGUIEventListToMessageListConverter):
        """Test converting multiple tool calls for the same message."""
        events = [
            ToolCallStartEvent(tool_call_id="tool-1", tool_call_name="function_1"),
            ToolCallArgsEvent(tool_call_id="tool-1", delta='{"arg1": "val1"}'),
            ToolCallStartEvent(tool_call_id="tool-2", tool_call_name="function_2"),
            ToolCallArgsEvent(tool_call_id="tool-2", delta='{"arg2": "val2"}')
        ]

        result = converter.convert(events)

        assert len(result) == 2  # Two separate AssistantMessages for two tool calls

        # Verify both tool calls exist
        tool_names = []
        for msg in result:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_names.append(msg.tool_calls[0].function.name)

        assert "function_1" in tool_names
        assert "function_2" in tool_names

    # ========== State Management Tests ==========

    def test_accumulator_state_persistence(self, converter: AGUIEventListToMessageListConverter):
        """Test that accumulator state persists between operations."""
        # First operation
        converter._append_content("persistent", "message", "Part 1 ")

        # Check intermediate state
        assert converter.accumulator["persistent"]["content"] == "Part 1 "

        # Second operation
        converter._append_content("persistent", "message", "Part 2")

        # Check final state
        assert converter.accumulator["persistent"]["content"] == "Part 1 Part 2"

    def test_accumulator_independence_between_conversions(self):
        """Test that accumulator is independent between different conversions."""
        converter = AGUIEventListToMessageListConverter()

        # First conversion
        events1 = [TextMessageContentEvent(message_id="conv1", delta="Conversion 1")]
        result1 = converter.convert(events1)

        # Accumulator should contain data from first conversion
        assert "conv1" in converter.accumulator

        # Second conversion on same converter
        events2 = [TextMessageContentEvent(message_id="conv2", delta="Conversion 2")]
        result2 = converter.convert(events2)

        # Accumulator should now contain data from both conversions
        assert "conv1" in converter.accumulator
        assert "conv2" in converter.accumulator
        assert len(result2) == 2  # Both messages should be in result