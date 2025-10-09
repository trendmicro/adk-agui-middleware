"""Minimal FastAPI app that exposes an SSE endpoint for AGUI, using
google.adk's LLM agent (LlmAgent) as the underlying agent.

This example shows the smallest practical integration of the middleware:
- Creates an `SSEService` with in-memory services.
- Registers a single POST endpoint that streams Server-Sent Events.
- Extracts a simple `user_id` from the `X-User-Id` header (defaults to "guest").
- Instantiates an `LlmAgent` with a model name from environment variables.

Run locally:
    uvicorn app:app --reload

Environment variables (optional):
- `ADK_MODEL_NAME` (default: `gemini-1.5-flash`)

Note:
- Ensure `google-adk` and its model provider dependencies are installed.
- If your ADK version expects different constructor arguments for `LlmAgent`,
  adjust `build_llm_agent()` accordingly (the function is tiny on purpose).
"""

from __future__ import annotations

import os
from typing import Any

from ag_ui.core import RunAgentInput
from fastapi import FastAPI, Request

from adk_agui_middleware import SSEService, register_agui_endpoint
from adk_agui_middleware.data_model.config import PathConfig
from adk_agui_middleware.data_model.context import ConfigContext


def build_llm_agent() -> Any:
    """Create a simple LLM agent from google.adk.

    Tries a common import path first; if your ADK version differs, adjust the
    import below. The default model name is intentionally conservative.
    """
    try:  # Typical import path for recent ADK versions
        from google.adk.agents.llm_agent import LlmAgent  # type: ignore
    except Exception:  # Fallback for alternate package layouts
        try:
            from google.adk.agents import LlmAgent  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "google.adk LlmAgent not available. Please install google-adk."
            ) from e

    # Get model name from environment or use default Gemini Flash model
    model_name = os.getenv("ADK_MODEL_NAME", "gemini-1.5-flash")

    # The constructor signature can vary between ADK versions; we try the common ones first.
    try:
        # Try keyword argument approach (newer versions)
        return LlmAgent(model_name=model_name)  # type: ignore[call-arg]
    except TypeError:
        pass
    try:
        # Try positional argument approach (older versions)
        return LlmAgent(model_name)  # type: ignore[misc]
    except TypeError:
        pass

    # Final fallback—bare init; users can adapt to their version.
    return LlmAgent()  # type: ignore[call-arg]


def extract_user_id(_: RunAgentInput, request: Request) -> str:
    """Get user id from header (falls back to "guest")."""
    return request.headers.get("X-User-Id", "guest")


# Instantiate the LLM agent from google.adk for processing user requests
agent: Any = build_llm_agent()

# Minimal in-memory configuration suitable for local development
# This uses default in-memory services for history, state, and session management

# Configure how the middleware extracts request context from incoming requests
config_context = ConfigContext(
    app_name="demo-app",  # Application identifier for logging and state management
    user_id=extract_user_id,  # Function to extract user ID from request
    # session_id defaults to a safe generator; you can also supply your own.
)

# Build the SSE service that will run the agent and stream events to the client
# This service orchestrates the entire request-response pipeline
sse_service = SSEService(
    agent=agent,  # The LLM agent that processes user inputs
    config_context=config_context,  # Request context extraction configuration
)

# Create the FastAPI app and register the SSE endpoint at /agui
app = FastAPI(title="AGUI Minimal SSE")
# Register the main endpoint that accepts POST requests and streams SSE responses
register_agui_endpoint(
    app=app,
    sse_service=sse_service,
    path_config=PathConfig(
        agui_main_path="/agui"
    ),  # Endpoint will be available at POST /agui
)


if __name__ == "__main__":  # pragma: no cover - manual run helper
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
