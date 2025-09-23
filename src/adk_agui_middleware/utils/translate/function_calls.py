# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Utility functions for handling function call events in AGUI format.

This module provides utilities for converting function calls and responses
between Google GenAI and AGUI event formats, managing tool call sequences
and result event creation.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import (
    BaseEvent,
    EventType,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from google.genai import types


class FunctionCallEventUtil:
    """Utility class for converting function calls to AGUI tool call events.

    Provides static methods for generating sequences of AGUI tool call events
    from Google GenAI function calls, including start, args, end, and result events.
    """

    @staticmethod
    def create_function_result_event(
        tool_call_id: str, content: dict[str, Any] | None
    ) -> ToolCallResultEvent:
        """Create a tool call result event from function response content.

        Converts function execution results into AGUI ToolCallResultEvent format,
        serializing the content as JSON and generating a unique message ID.

        Args:
            tool_call_id: Unique identifier for the tool call
            content: Function response content to include in the result

        Returns:
            ToolCallResultEvent containing the function result
        """
        return ToolCallResultEvent(
            message_id=str(uuid.uuid4()),
            type=EventType.TOOL_CALL_RESULT,
            tool_call_id=tool_call_id,
            content=json.dumps(content) if content else "",
        )

    @staticmethod
    async def generate_function_call_event(
        tool_call_id: str,
        tool_call_name: str,
        tool_call_args: dict[str, Any] | str | None,
    ) -> AsyncGenerator[BaseEvent]:
        """Generate a complete sequence of tool call events.

        Creates the full sequence of AGUI events for a single tool call:
        start event, optional args event (if arguments provided), and end event.

        Args:
            tool_call_id: Unique identifier for the tool call
            tool_call_name: Name of the tool being called
            tool_call_args: Arguments for the tool call (dict or string)

        Yields:
            BaseEvent objects representing the tool call sequence
        """
        yield ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_call_name=tool_call_name,
        )
        if tool_call_args:
            args_str = (
                json.dumps(tool_call_args)
                if isinstance(tool_call_args, dict)
                else str(tool_call_args)
            )
            yield ToolCallArgsEvent(
                type=EventType.TOOL_CALL_ARGS,
                tool_call_id=tool_call_id,
                delta=args_str,
            )
        yield ToolCallEndEvent(type=EventType.TOOL_CALL_END, tool_call_id=tool_call_id)

    async def generate_function_calls_event(
        self,
        function_calls: list[types.FunctionCall],
    ) -> AsyncGenerator[BaseEvent]:
        """Generate AGUI events for multiple Google GenAI function calls.

        Processes a list of Google GenAI function calls and generates
        the complete sequence of AGUI tool call events for each one.

        Args:
            function_calls: List of Google GenAI function calls to process

        Yields:
            BaseEvent objects for all function calls in sequence
        """
        for func_call in function_calls:
            tool_call_id = func_call.id or str(uuid.uuid4())
            if not func_call.name:
                continue
            async for agui_event in self.generate_function_call_event(
                tool_call_id=tool_call_id,
                tool_call_name=func_call.name,
                tool_call_args=func_call.args,
            ):
                yield agui_event
