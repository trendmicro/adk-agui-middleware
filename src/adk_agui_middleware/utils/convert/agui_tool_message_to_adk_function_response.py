# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Conversion utility for transforming AGUI tool messages to ADK function responses.

This module handles the conversion of AGUI tool result messages to ADK format
for resuming agent execution in HITL (Human-in-the-Loop) workflows.
"""

import json
from typing import Any, cast

from ag_ui.core import ToolMessage
from google.genai import types

from ...loggers.record_log import record_warning_log


def convert_agui_tool_message_to_adk_function_response(
    tool_message: ToolMessage, tool_call_name: str
) -> types.Part:
    """Convert AGUI tool message to ADK function response format.

    Transforms a tool result submission from AGUI format into the corresponding
    ADK FunctionResponse format for resuming agent execution. This is essential
    for HITL workflows where humans provide tool results to continue agent processing.

    The function handles empty content gracefully by providing a default success
    response, and parses JSON content to create proper function response objects.

    Args:
        :param tool_message: AGUI ToolMessage containing the tool execution result
        :param tool_call_name: Name of the function that was called

    Returns:
        ADK Part object containing the FunctionResponse for agent processing

    Raises:
        json.JSONDecodeError: If tool message content is not valid JSON (implicitly)
    """

    def parse_tool_content() -> dict[str, Any]:
        """Parse tool message content with error handling for empty content.

        Returns:
            Dictionary containing parsed tool result or default success response
        """
        if not tool_message.content or not tool_message.content.strip():
            record_warning_log(
                f"Empty tool result content for tool call {tool_message.tool_call_id}: {tool_call_name}, using empty success result"
            )
            return {"success": True, "result": None}
        return cast(dict[str, Any], json.loads(tool_message.content))

    return types.Part(
        function_response=types.FunctionResponse(
            id=tool_message.tool_call_id,
            name=tool_call_name,
            response=parse_tool_content(),
        )
    )
