# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Frontend tool adapter for exposing client-side tools through ADK agent framework."""

import uuid
from collections.abc import Callable, Coroutine
from typing import Any, cast

from ag_ui.core import Tool
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, LongRunningFunctionTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
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

    def __init__(self, agui_tool: Tool, agui_queue: QueueManager) -> None:
        """Initialize the frontend tool from AGUI tool definition.

        Args:
            :param agui_tool: AGUI Tool definition containing name, description, and parameters
            :param agui_queue: Queue manager for sending function call events to clients
        """
        super().__init__(
            name=agui_tool.name,
            description=agui_tool.description,
            is_long_running=True,
        )
        self.parameters = agui_tool.parameters
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
        """Create an async function used to proxy an AGUI tool invocation.

        Generates a coroutine function with a dynamic name and docstring that
        delegates to ``self._execute``. This allows the ADK tool system to
        expose the frontend tool with the expected metadata.

        Args:
            :param name: Function name to expose to the tool system
            :param description: Human-readable description used as the docstring

        Returns:
            A coroutine function that forwards execution to ``_execute``
        """

        async def dynamic_func(args: dict[str, Any], tool_context: ToolContext) -> Any:
            """Proxy execution that forwards to the tool's internal executor.

            Args:
                :param args: Tool invocation arguments
                :param tool_context: Execution context with function call metadata

            Returns:
                The result of ``_execute`` (typically None; result arrives via HITL)
            """
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
    """Toolset adapter that exposes frontend/client tools to the agent.

    Wraps a collection of FrontendTool adapters and optionally filters or
    prefixes tool names. This toolset integrates with the ADK agent tool
    mechanism, enabling HITL by forwarding tool calls to the client.

    Attributes:
        frontend_tools: Materialized list of FrontendTool instances
        agui_queue: Queue manager used by tools to emit AGUI events
    """

    def __init__(
        self,
        tool_filter: ToolPredicate | list[str] | None = None,
        tool_name_prefix: str | None = None,
    ) -> None:
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self.frontend_tools: list[FrontendTool] = []
        self.agui_queue: QueueManager | None = None

    def _get_filter_func(self) -> Callable[[BaseTool], bool] | None:
        """Return a predicate function derived from the configured filter.

        Converts the optional ``tool_filter`` into a callable predicate. If a list
        of tool names is provided, a simple membership test is used; if a callable
        is provided, it is returned as-is.

        Returns:
            Callable that returns True if a tool should be included; otherwise None
        """
        if not self.tool_filter:
            return None
        if callable(self.tool_filter):
            return self.tool_filter
        if isinstance(self.tool_filter, list):
            tool_names = set(self.tool_filter)
            return lambda tool: tool.name in tool_names
        return None

    def set_frontend_tools(
        self, agui_queue: QueueManager, agui_tools: list[Tool]
    ) -> None:
        """Create and store FrontendTool adapters from AGUI tool definitions.

        Builds FrontendTool instances for the provided AGUI tools, applies an
        optional name prefix and filter predicate, and stores the resulting list.

        Args:
            :param agui_queue: Queue manager used by tools to emit AGUI events
            :param agui_tools: List of AGUI Tool schemas from the client
        """
        self.agui_queue = agui_queue
        filter_func = self._get_filter_func()
        frontend_tools = []
        for agui_tool in agui_tools:
            try:
                tool = FrontendTool(agui_tool=agui_tool, agui_queue=self.agui_queue)
                if self.tool_name_prefix:
                    tool.name = f"{self.tool_name_prefix}{tool.name}"
                if filter_func is None or filter_func(tool):
                    frontend_tools.append(tool)
            except Exception as e:
                record_error_log(
                    f"Failed to create proxy tool for '{agui_tool.name}'.", e
                )
        self.frontend_tools = frontend_tools

    async def get_tools(self, _: ReadonlyContext | None = None) -> list[BaseTool]:
        """Return the list of frontend tools for the agent runtime.

        Returns:
            List of BaseTool instances backed by frontend/client tools
        """
        return cast(list[BaseTool], self.frontend_tools)

    def __repr__(self) -> str:
        """Return string representation of the frontend toolset.

        Returns:
            String describing the toolset and its tools
        """
        return f"ClientProxyToolset(tools={[tool.name for tool in self.frontend_tools]}, all_long_running=True)"
