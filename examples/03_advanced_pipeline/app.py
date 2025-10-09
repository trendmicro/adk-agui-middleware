"""Advanced wiring with a custom I/O recorder and input preprocessing.

This example demonstrates how to:
- Register the main SSE endpoint on a custom path.
- Inject a custom input/output (I/O) recorder to log request/response flow.
- Preprocess incoming `RunAgentInput` to attach lightweight metadata when tools are involved.

Run locally:
    uvicorn app:app --reload

Replace `DemoAgent` with your real ADK agent implementation.
"""

from __future__ import annotations

from typing import Any

from ag_ui.core import RunAgentInput
from fastapi import FastAPI, Request

from adk_agui_middleware import SSEService, register_agui_endpoint
from adk_agui_middleware.base_abc.handler import BaseInOutHandler
from adk_agui_middleware.data_model.common import InputInfo
from adk_agui_middleware.data_model.config import PathConfig
from adk_agui_middleware.data_model.context import ConfigContext, HandlerContext


# Optional ADK imports for local type clarity
try:  # pragma: no cover - optional at example time
    from ag_ui.core import ToolMessage  # type: ignore
    from google.adk.agents import BaseAgent  # type: ignore
except Exception:  # pragma: no cover - dev convenience
    ToolMessage = None  # type: ignore[misc]
    BaseAgent = object  # type: ignore[misc,assignment]


class DemoAgent(BaseAgent):  # type: ignore[valid-type]
    """Placeholder agent.

    Replace with a concrete agent that emits ADK events.
    This demonstrates the agent integration pattern.
    """

    def __init__(self) -> None:  # noqa: D401 - minimal stub
        # Initialize the base agent with default configuration
        super().__init__()  # type: ignore[misc]


class ConsoleIORecorder(BaseInOutHandler):
    """Minimal example of a custom I/O recorder.

    Records input context and outgoing SSE events. In production, this could
    write to structured logs or observability systems. Keep transformations
    in `output_catch_and_change` conservative to avoid breaking SSE format.
    """

    async def input_record(self, input_info: InputInfo) -> None:
        """Record incoming request information for monitoring/debugging."""
        print(
            "[I/O] input:",
            {
                "app": input_info.app_name,  # Application identifier
                "user": input_info.user_id,  # User making the request
                "session": input_info.session_id,  # Session/thread ID
                "has_initial_state": bool(
                    input_info.initial_state
                ),  # Whether state was provided
            },
        )

    async def output_record(self, agui_event: dict[str, str]) -> None:
        """Record outgoing SSE events for monitoring/debugging."""
        # Keep it short to avoid noisy logs in development
        print("[I/O] event:", {k: agui_event.get(k) for k in ("event", "id")})

    async def output_catch_and_change(
        self, agui_event: dict[str, str]
    ) -> dict[str, str]:
        """Transform outgoing events if needed (use with caution)."""
        # For safety, do not mutate the core fields; simply pass through.
        # You may add custom fields if your client explicitly supports them.
        return agui_event


def extract_user_id(_: RunAgentInput, request: Request) -> str:
    """Extract a user id for the main SSE endpoint."""
    return request.headers.get("X-User-Id", "guest")


async def preprocess_run_input(
    run_agent_input: RunAgentInput, function_call_info: dict[str, str]
) -> RunAgentInput:
    """Attach lightweight metadata when tools are in play.

    If a tool call is about to be executed, we append a short `ToolMessage` with
    metadata so your agent can react accordingly. This is intentionally minimal
    and safe; adapt to your needs.
    """
    # Check if ToolMessage is available (might not be in some environments)
    if ToolMessage is None:
        # If AGUI's ToolMessage is not available at import time, just return the input.
        return run_agent_input

    # Process tool call information if any tools are being invoked
    if function_call_info:
        # Take one entry as a compact hint; adapt as needed.
        tool_call_id, tool_name = next(iter(function_call_info.items()))
        # Create metadata about the tool call for the agent
        meta = {
            "note": "Tool execution requested",
            "tool": tool_name,
            "callId": tool_call_id,
        }
        # Append a metadata ToolMessage so your agent can use it downstream
        # This allows the agent to be aware of tool execution context
        run_agent_input.messages.append(
            ToolMessage(
                role="tool",
                id=run_agent_input.messages[-1].id
                if run_agent_input.messages
                else tool_call_id,
                tool_call_id=tool_call_id,
                content=str(meta),  # Tool metadata as string content
            )
        )
    return run_agent_input


# Build the app with advanced pipeline configuration
agent: Any = DemoAgent()  # Replace with your BaseAgent implementation

# Configuration context with input preprocessing enabled
config_context = ConfigContext(
    app_name="demo-app",  # Application identifier
    user_id=extract_user_id,  # User ID extraction function
    convert_run_agent_input=preprocess_run_input,  # Input preprocessing for tool calls
)

# Handler context configures custom pipeline handlers
handler_context = HandlerContext(
    in_out_record_handler=ConsoleIORecorder,  # I/O recording for monitoring
)

# SSE service with advanced pipeline features enabled
sse_service = SSEService(
    agent=agent,  # The agent implementation
    config_context=config_context,  # Request context and preprocessing
    handler_context=handler_context,  # Custom pipeline handlers
)

# Create FastAPI application for advanced pipeline demonstration
app = FastAPI(title="AGUI Advanced Pipeline")

# Expose the main SSE endpoint on a custom path
# This demonstrates custom endpoint configuration
register_agui_endpoint(
    app=app,
    sse_service=sse_service,
    path_config=PathConfig(agui_main_path="/api/v1/agui"),  # Custom API path
)


if __name__ == "__main__":  # pragma: no cover - manual run helper
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8002, reload=True)
