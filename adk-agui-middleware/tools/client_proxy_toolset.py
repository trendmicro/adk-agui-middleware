import asyncio

from ag_ui.core import Tool as AGUITool
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from loggers.record_log import record_debug_log, record_error_log, record_log

from .client_proxy_tool import ClientProxyTool


class ClientProxyToolset(BaseToolset):
    def __init__(self, ag_ui_tools: list[AGUITool], event_queue: asyncio.Queue):
        super().__init__()
        self.ag_ui_tools = ag_ui_tools
        self.event_queue = event_queue
        record_log(
            f"Initialized ClientProxyToolset with {len(ag_ui_tools)} tools (all long-running)"
        )

    async def get_tools(
        self, readonly_context: ReadonlyContext | None = None
    ) -> list[BaseTool]:
        proxy_tools = []
        for ag_ui_tool in self.ag_ui_tools:
            try:
                proxy_tool = ClientProxyTool(
                    ag_ui_tool=ag_ui_tool, event_queue=self.event_queue
                )
                proxy_tools.append(proxy_tool)
                record_debug_log(
                    f"Created proxy tool for '{ag_ui_tool.name}' (long-running)"
                )
            except Exception as e:
                record_error_log(
                    f"Failed to create proxy tool for '{ag_ui_tool.name}': {e}"
                )
        return proxy_tools

    async def close(self) -> None:
        record_log("Closing ClientProxyToolset")

    def __repr__(self) -> str:
        tool_names = [tool.name for tool in self.ag_ui_tools]
        return f"ClientProxyToolset(tools={tool_names}, all_long_running=True)"
