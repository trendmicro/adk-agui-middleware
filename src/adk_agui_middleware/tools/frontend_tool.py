# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Frontend tool adapter for exposing client-side tools through ADK agent framework."""

import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from ag_ui.core import Tool
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, LongRunningFunctionTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset
from google.genai import types

from ..loggers.record_log import record_error_log
from ..manager.queue import QueueManager
from ..utils.translate import FunctionCallEventUtil


class FrontendTool(BaseTool):
    """ADK tool wrapper for frontend-defined tools enabling HITL workflows.

    Bridges client-defined tools (from AGUI Tool schema) into the ADK tool system,
    allowing agents to invoke frontend/client-side operations. When executed, this
    tool generates AGUI function call events and places them in the event queue for
    client transmission, then pauses agent execution until the client provides results.

    This is a core component of the Human-in-the-Loop (HITL) workflow, where:
    1. Agent decides to call a frontend tool
    2. FrontendTool generates a function call event for the client
    3. Agent execution pauses (long-running tool pattern)
    4. Client receives the call, executes it, and returns results
    5. Agent resumes with the tool results

    Attributes:
        parameters: JSON Schema dict defining the tool's input parameters
        agui_queue: Queue manager for sending AGUI events to clients
    """

    def __init__(self, ag_ui_tool: Tool, agui_queue: QueueManager) -> None:
        """Initialize the frontend tool from AGUI tool definition.

        Args:
            :param ag_ui_tool: AGUI Tool definition containing name, description, and parameters
            :param agui_queue: Queue manager for sending function call events to clients
        """
        super().__init__(
            name=ag_ui_tool.name,
            description=ag_ui_tool.description,
            is_long_running=True,
        )
        self.parameters = ag_ui_tool.parameters
        self.agui_queue = agui_queue
        # Ensure parameters is a valid JSON Schema dict
        if not isinstance(self.parameters, dict):
            self.parameters = {"type": "object", "properties": {}}
        # Create the underlying long-running tool with dynamic signature
        self._long_running_tool = LongRunningFunctionTool(
            self._create_agui_function_call(
                self.name,
                self.description,
            )
        )

    def _create_agui_function_call(
        self,
        name: str,
        description: str,
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        async def dynamic_func(args: dict[str, Any], tool_context: ToolContext) -> Any:
            return await self._execute(args, tool_context)

        dynamic_func.__name__ = name
        dynamic_func.__doc__ = description
        return dynamic_func

    def _get_declaration(self) -> types.FunctionDeclaration | None:
        """Get the function declaration for this tool.

        Returns:
            FunctionDeclaration with tool metadata and parameter schema
        """
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema.model_validate(self.parameters),
        )

    async def _execute(self, args: dict[str, Any], tool_context: ToolContext) -> Any:
        """Execute the frontend tool by generating a function call event.

        Generates AGUI function call events and sends them to the client through
        the event queue. This does not execute the tool locally - it sends the
        invocation to the client and relies on the long-running pattern to pause
        agent execution until the client provides results.

        Args:
            :param args: Tool invocation arguments from the agent
            :param tool_context: Execution context containing function call ID and metadata

        Raises:
            Exception: Re-raises any errors after logging for proper error handling
        """
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
        return None

    def __repr__(self) -> str:
        """Return string representation of the frontend tool.

        Returns:
            String describing the tool's name, description, and parameters
        """
        return f"tool_name: {self.name}, description: {self.description}, parameters: {self.parameters}."

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        """Run the frontend tool asynchronously through the long-running tool pattern.

        Delegates to the underlying long-running tool implementation which handles
        the HITL pause/resume workflow.

        Args:
            :param args: Tool invocation arguments
            :param tool_context: Execution context for this tool invocation

        Returns:
            Tool execution results (provided by client after HITL completion)
        """
        return await self._long_running_tool.run_async(
            args=args, tool_context=tool_context
        )


class FrontendToolset(BaseToolset):
    """Toolset for dynamically creating frontend tools from AGUI Tool definitions.

    Provides a collection of frontend tools that are all marked as long-running
    for HITL workflows. This toolset converts AGUI Tool schemas into ADK-compatible
    tools and handles creation errors gracefully by logging and skipping problematic
    tool definitions.

    Attributes:
        ag_ui_tools: List of AGUI Tool definitions to convert
        agui_queue: Queue manager for sending events to clients
    """

    def __init__(self, agui_queue: QueueManager, ag_ui_tools: list[Tool]) -> None:
        """Initialize the frontend toolset with tool definitions and event queue.

        Args:
            :param agui_queue: Queue manager for sending function call events to clients
            :param ag_ui_tools: List of AGUI Tool definitions to expose to the agent
        """
        super().__init__()
        self.ag_ui_tools = ag_ui_tools
        self.agui_queue = agui_queue

    async def get_tools(self, _: ReadonlyContext | None = None) -> list[BaseTool]:
        """Get all frontend tools wrapped as ADK BaseTool instances.

        Converts each AGUI Tool definition into a FrontendTool, logging and skipping
        any that fail to convert. This enables graceful degradation when tool schemas
        are invalid or incompatible.

        Args:
            :param _: ReadonlyContext (unused, required by BaseToolset interface)

        Returns:
            List of successfully created FrontendTool instances
        """
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
        """Return string representation of the frontend toolset.

        Returns:
            String describing the toolset and its tools
        """
        return f"ClientProxyToolset(tools={[tool.name for tool in self.ag_ui_tools]}, all_long_running=True)"
