# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
import json
from typing import Any, cast

from ag_ui.core import ToolMessage
from google.genai import types

from ...loggers.record_log import record_warning_log


def convert_agui_tool_message_to_adk_function_response(
    tool_message: ToolMessage, tool_call_name: str
) -> types.Part:
    def parse_tool_content() -> dict[str, Any]:
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
