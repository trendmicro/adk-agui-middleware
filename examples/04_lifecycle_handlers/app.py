"""Lifecycle-focused example showing HandlerContext hooks and processing stages.

This app demonstrates how custom handlers plug into the middleware event pipeline,
with extensive inline comments outlining the end-to-end request lifecycle.

Key ideas illustrated:
- Where session locking happens and how to customize it.
- How ADK events flow through optional pre-processing and timeouts.
- How translation to AGUI events works (and how a translate handler can intercept).
- How AGUI events can be post-processed.
- Where state snapshot transformation occurs.
- Where input/output recording fits in.

Run locally:
    uvicorn app:app --reload

Environment variables (optional):
- `ADK_MODEL_NAME` (default: `gemini-1.5-flash`)

Note: Handlers here are intentionally simple and pass-through oriented to keep
the example focused on structure and lifecycle, not business logic.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

from ag_ui.core import BaseEvent, RunAgentInput
from fastapi import FastAPI, Request
from google.adk.events import Event

from adk_agui_middleware import SSEService, register_agui_endpoint
from adk_agui_middleware.base_abc.handler import (
    BaseADKEventHandler,
    BaseADKEventTimeoutHandler,
    BaseAGUIEventHandler,
    BaseAGUIStateSnapshotHandler,
    BaseInOutHandler,
    BaseTranslateHandler,
    SessionLockHandler,
)
from adk_agui_middleware.data_model.common import InputInfo, SessionLockConfig
from adk_agui_middleware.data_model.config import PathConfig
from adk_agui_middleware.data_model.context import ConfigContext, HandlerContext
from adk_agui_middleware.data_model.event import TranslateEvent


def build_llm_agent() -> Any:
    """Create an LlmAgent from google.adk using a model name from env."""
    # Try to import LlmAgent with different import paths for compatibility
    try:
        from google.adk.agents.llm_agent import LlmAgent  # type: ignore
    except Exception:  # pragma: no cover - fallback path
        from google.adk.agents import LlmAgent  # type: ignore

    # Get model name from environment or use default
    model_name = os.getenv("ADK_MODEL_NAME", "gemini-1.5-flash")
    try:
        # Try keyword argument constructor (newer versions)
        return LlmAgent(model_name=model_name)  # type: ignore[call-arg]
    except TypeError:
        # Fall back to positional argument constructor
        return LlmAgent(model_name)  # type: ignore[misc]


class InMemorySessionLock(SessionLockHandler):
    """Simple in-memory session lock for demonstration.

    This prevents concurrent runs on the same (app, user, session) triple.
    Keep it minimal for local demos; for production, consider Redis or DB-backed locks.
    """

    # Global registry of locks keyed by a composite session key
    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, lock_config: SessionLockConfig) -> None:
        """Initialize lock handler with configuration parameters."""
        self.lock_timeout = lock_config.lock_timeout
        self.retry_interval = lock_config.retry_interval
        self.retry_count = lock_config.retry_count

    @staticmethod
    def _key(info: InputInfo) -> str:
        """Generate a unique key for session identification."""
        return f"{info.app_name}:{info.user_id}:{info.session_id}"

    async def lock(self, input_info: InputInfo) -> bool:
        """Attempt to acquire a lock for the session."""
        key = self._key(input_info)
        # Get or create a lock for this session
        lock = self._locks.setdefault(key, asyncio.Lock())
        attempt = 0
        # Retry logic with configurable attempts
        while attempt <= self.retry_count:
            if not lock.locked():
                await lock.acquire()  # Acquire the lock
                return True
            attempt += 1
            await asyncio.sleep(self.retry_interval)  # Wait before retry
        return False  # Failed to acquire lock

    async def unlock(self, input_info: InputInfo) -> None:
        """Release the lock for the session."""
        key = self._key(input_info)
        lock = self._locks.get(key)
        if lock and lock.locked():
            lock.release()  # Release the acquired lock

    async def get_locked_message(self, input_info: InputInfo):  # returns RunErrorEvent
        """Generate error message when session is locked."""
        from ag_ui.core import RunErrorEvent

        return RunErrorEvent(
            id="session-locked",
            message=f"Session {self._key(input_info)} is locked by another request.",
        )


class LifecycleADKEventHandler(BaseADKEventHandler):
    """ADK event pre-processor.

    Use cases:
    - Filter internal roles
    - Modify metadata
    - Implement custom event routing
    Here, we simply pass through and print a short trace to illustrate placement.
    """

    def __init__(self, input_info: InputInfo | None) -> None:
        """Initialize handler with optional input context."""
        self.info = input_info

    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        """Process ADK events before translation to AGUI format."""
        print("[Lifecycle] ADK event ->", getattr(event, "author", None))
        # Yield the event as-is; return None to filter it out.
        # This is where you could filter, modify, or route events
        yield event


class LifecycleTimeoutHandler(BaseADKEventTimeoutHandler):
    """Timeout policy for ADK event processing.

    Keep generous timeouts for demos to avoid unexpected fallbacks.
    """

    def __init__(self, input_info: InputInfo | None) -> None:  # noqa: D401
        """Initialize timeout handler with optional input context."""
        self.info = input_info

    async def get_timeout(self) -> int:
        """Return timeout duration in seconds for ADK event processing."""
        # 30 seconds demo timeout - adjust based on your needs
        return 30

    async def process_timeout_fallback(self) -> AsyncGenerator[Event | None]:
        """Handle timeout scenarios by providing fallback events."""
        print("[Lifecycle] Timeout fallback invoked")
        # In a real app, emit an ADK error event or a synthetic explanation event.
        # We yield None here to keep the example neutral.
        if False:  # pragma: no cover - placeholder
            yield None
        return


class LifecycleTranslateHandler(BaseTranslateHandler):
    """Intercept translation stage.

    You can retune or replace events here. We demonstrate a no-op that
    traces when the hook runs without altering the pipeline.
    """

    def __init__(self, input_info: InputInfo | None) -> None:
        """Initialize translate handler with optional input context."""
        self.info = input_info

    async def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        """Intercept and potentially modify event translation."""
        print("[Lifecycle] Translate hook for event")
        # No-op: do not yield any TranslateEvent so the default translator runs.
        # This is where you could provide custom event translation logic
        if False:  # pragma: no cover - sample structure
            yield TranslateEvent()
        return


class LifecycleAGUIEventHandler(BaseAGUIEventHandler):
    """AGUI event post-processor.

    Perfect place to filter or reshape AGUI events right before SSE encoding.
    Here, we log and pass through.
    """

    def __init__(self, input_info: InputInfo | None) -> None:
        """Initialize AGUI event handler with optional input context."""
        self.info = input_info

    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        """Process AGUI events after translation from ADK events."""
        print("[Lifecycle] AGUI event ->", type(event).__name__)
        # This is where you could filter or modify AGUI events before SSE output
        yield event


class LifecycleStateHandler(BaseAGUIStateSnapshotHandler):
    """Filter or enrich the final state snapshot.

    For example, you might drop sensitive server-only keys.
    """

    def __init__(self, input_info: InputInfo | None) -> None:  # noqa: D401
        """Initialize state handler with optional input context."""
        self.info = input_info

    async def process(self, state_snapshot: dict[str, Any]) -> dict[str, Any] | None:
        """Filter or transform the state snapshot before sending to client."""
        # Example: Remove private/internal keys that start with underscore
        filtered = {k: v for k, v in state_snapshot.items() if not k.startswith("_")}
        return filtered


class LifecycleIORecorder(BaseInOutHandler):
    """Record incoming context and outgoing SSE frames.

    Keep output minimal to avoid noise in development.
    """

    async def input_record(self, input_info: InputInfo) -> None:
        """Record incoming request context for monitoring/debugging."""
        print(
            "[Lifecycle] INPUT",
            {
                "app": input_info.app_name,  # Application name
                "user": input_info.user_id,  # User identifier
                "session": input_info.session_id,  # Session/thread ID
            },
        )

    async def output_record(self, agui_event: dict[str, str]) -> None:
        """Record outgoing SSE events for monitoring/debugging."""
        print("[Lifecycle] OUTPUT", {k: agui_event.get(k) for k in ("event", "id")})

    async def output_catch_and_change(
        self, agui_event: dict[str, str]
    ) -> dict[str, str]:
        """Transform outgoing SSE events if needed (use with caution)."""
        # Pass through without modification - be careful with changes here
        return agui_event


def extract_user_id(_: RunAgentInput, request: Request) -> str:
    """Minimal user id extraction."""
    return request.headers.get("X-User-Id", "guest")


# Agent and middleware wiring with full lifecycle handlers
agent: Any = build_llm_agent()  # Create the LLM agent

# Basic configuration context
config_context = ConfigContext(
    app_name="demo-app",  # Application identifier
    user_id=extract_user_id,  # User ID extraction function
)

# Handler context with all lifecycle hooks configured
handler_context = HandlerContext(
    # Session lock to prevent concurrent runs on the same conversation
    session_lock_handler=InMemorySessionLock,
    # ADK-side hooks for event processing
    adk_event_handler=LifecycleADKEventHandler,  # Pre-process ADK events
    adk_event_timeout_handler=LifecycleTimeoutHandler,  # Handle timeouts
    # Translation intercept hook
    translate_handler=LifecycleTranslateHandler,  # Custom event translation
    # AGUI-side hooks for final processing
    agui_event_handler=LifecycleAGUIEventHandler,  # Post-process AGUI events
    agui_state_snapshot_handler=LifecycleStateHandler,  # Filter state snapshots
    # Input/output recorder for monitoring
    in_out_record_handler=LifecycleIORecorder,  # Record I/O for debugging
)

# SSE service with comprehensive lifecycle handling
sse_service = SSEService(
    agent=agent,  # The LLM agent
    config_context=config_context,  # Request context configuration
    handler_context=handler_context,  # All lifecycle handlers
)

# Create FastAPI application for lifecycle demonstration
app = FastAPI(title="AGUI Lifecycle + Handlers")

# Register the main SSE endpoint with custom path
register_agui_endpoint(
    app=app,
    sse_service=sse_service,
    path_config=PathConfig(agui_main_path="/lifecycle/agui"),  # Custom endpoint path
)


if __name__ == "__main__":  # pragma: no cover - manual run helper
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8003, reload=True)
