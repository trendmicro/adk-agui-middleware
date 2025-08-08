import asyncio
import inspect
import json
import uuid
from typing import Any

from ag_ui.core import (
    EventType,
    Tool as AGUITool,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from google.adk.tools import BaseTool, LongRunningFunctionTool
from google.genai import types

from loggers.record_log import record_debug_log, record_error_log, record_warning_log


class ClientProxyTool(BaseTool):
    def __init__(self, ag_ui_tool: AGUITool, event_queue: asyncio.Queue):
        super().__init__(
            name=ag_ui_tool.name,
            description=ag_ui_tool.description,
            is_long_running=True,
        )

        self.ag_ui_tool = ag_ui_tool
        self.event_queue = event_queue

        sig_params = []

        parameters = ag_ui_tool.parameters
        if isinstance(parameters, dict) and "properties" in parameters:
            for param_name in parameters["properties"].keys():
                sig_params.append(
                    inspect.Parameter(
                        param_name,
                        inspect.Parameter.KEYWORD_ONLY,
                        default=None,
                        annotation=Any,
                    )
                )

        async def proxy_tool_func(**kwargs) -> Any:
            original_args = getattr(self, "_current_args", kwargs)
            original_tool_context = getattr(self, "_current_tool_context", None)
            return await self._execute_proxy_tool(original_args, original_tool_context)

        proxy_tool_func.__name__ = ag_ui_tool.name
        proxy_tool_func.__doc__ = ag_ui_tool.description

        if sig_params:
            proxy_tool_func.__signature__ = inspect.Signature(sig_params)

        self._long_running_tool = LongRunningFunctionTool(proxy_tool_func)

    def _get_declaration(self) -> types.FunctionDeclaration | None:
        record_debug_log(f"_get_declaration called for {self.name}")
        record_debug_log(f"AG-UI tool parameters: {self.ag_ui_tool.parameters}")
        parameters = self.ag_ui_tool.parameters
        if not isinstance(parameters, dict):
            parameters = {"type": "object", "properties": {}}
            record_warning_log(
                f"Tool {self.name} had non-dict parameters, using empty schema"
            )

        function_declaration = types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(parameters),
        )
        record_debug_log(
            f"Created FunctionDeclaration for {self.name}: {function_declaration}"
        )
        return function_declaration

    async def run_async(self, *, args: dict[str, Any], tool_context: Any) -> Any:
        self._current_args = args
        self._current_tool_context = tool_context
        return await self._long_running_tool.run_async(
            args=args, tool_context=tool_context
        )

    async def _execute_proxy_tool(self, args: dict[str, Any], tool_context: Any) -> Any:
        record_debug_log(f"Proxy tool execution: {self.ag_ui_tool.name}")
        record_debug_log(f"Arguments received: {args}")
        record_debug_log(f"Tool context type: {type(tool_context)}")
        adk_function_call_id = None
        if tool_context and hasattr(tool_context, "function_call_id"):
            adk_function_call_id = tool_context.function_call_id
            record_debug_log(f"Using ADK function_call_id: {adk_function_call_id}")

        tool_call_id = adk_function_call_id or f"call_{uuid.uuid4().hex[:8]}"
        if not adk_function_call_id:
            record_warning_log(
                f"ADK function_call_id not available, generated: {tool_call_id}"
            )

        try:
            start_event = ToolCallStartEvent(
                type=EventType.TOOL_CALL_START,
                tool_call_id=tool_call_id,
                tool_call_name=self.ag_ui_tool.name,
            )
            await self.event_queue.put(start_event)
            record_debug_log(f"Emitted TOOL_CALL_START for {tool_call_id}")

            args_json = json.dumps(args)
            args_event = ToolCallArgsEvent(
                type=EventType.TOOL_CALL_ARGS,
                tool_call_id=tool_call_id,
                delta=args_json,
            )
            await self.event_queue.put(args_event)
            record_debug_log(f"Emitted TOOL_CALL_ARGS for {tool_call_id}")

            end_event = ToolCallEndEvent(
                type=EventType.TOOL_CALL_END, tool_call_id=tool_call_id
            )
            await self.event_queue.put(end_event)
            record_debug_log(f"Emitted TOOL_CALL_END for {tool_call_id}")

            record_debug_log(f"Returning None for long-running tool {tool_call_id}")
            return None

        except Exception as e:
            record_error_log(f"Error in proxy tool execution for {tool_call_id}: {e}")
            raise

    def __repr__(self) -> str:
        return (
            f"ClientProxyTool(name='{self.name}', ag_ui_tool='{self.ag_ui_tool.name}')"
        )
