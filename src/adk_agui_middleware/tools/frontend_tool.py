import uuid
from typing import Any

from ag_ui.core import Tool
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, LongRunningFunctionTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset
from google.genai import types

from ..loggers.record_log import record_error_log
from ..manager.queue import QueueManager
from ..utils.translate import FunctionCallEventUtil
from .create_function_with_params import create_function_with_params


class FrontendTool(BaseTool):
    def __init__(self, ag_ui_tool: Tool, agui_queue: QueueManager) -> None:
        super().__init__(
            name=ag_ui_tool.name,
            description=ag_ui_tool.description,
            is_long_running=True,
        )
        self.parameters = ag_ui_tool.parameters
        self.agui_queue = agui_queue
        if not isinstance(self.parameters, dict):
            self.parameters = {"type": "object", "properties": {}}
        self._long_running_tool = LongRunningFunctionTool(
            create_function_with_params(
                self._execute,
                self.name,
                self.description,
                list(self.parameters.get("properties", {}).keys()),
            )
        )

    def _get_declaration(self) -> types.FunctionDeclaration | None:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(self.parameters),
        )

    async def _execute(self, args: dict[str, Any], tool_context: ToolContext) -> Any:
        try:
            async for (
                agui_event
            ) in FunctionCallEventUtil().generate_function_call_event(
                tool_call_id=tool_context.function_call_id or str(uuid.uuid4()),
                tool_call_name=self.name,
                tool_call_args=args,
            ):
                await self.agui_queue.put(agui_event)
        except Exception as e:
            record_error_log(
                f"Error in proxy tool execution for {tool_context.function_call_id}.", e
            )
            raise

    def __repr__(self) -> str:
        return f"tool_name: {self.name}, description: {self.description}, parameters: {self.parameters}."

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        return await self._long_running_tool.run_async(
            args=args, tool_context=tool_context
        )


class FrontendToolset(BaseToolset):
    def __init__(self, agui_queue: QueueManager, ag_ui_tools: list[Tool]) -> None:
        super().__init__()
        self.ag_ui_tools = ag_ui_tools
        self.agui_queue = agui_queue

    async def get_tools(self, _: ReadonlyContext | None = None) -> list[BaseTool]:
        proxy_tools: list[BaseTool] = []
        for ag_ui_tool in self.ag_ui_tools:
            try:
                proxy_tools.append(
                    FrontendTool(ag_ui_tool=ag_ui_tool, agui_queue=self.agui_queue)
                )
            except Exception as e:
                record_error_log(
                    f"Failed to create proxy tool for '{ag_ui_tool.name}'.", e
                )
        return proxy_tools

    def __repr__(self) -> str:
        return f"ClientProxyToolset(tools={[tool.name for tool in self.ag_ui_tools]}, all_long_running=True)"
