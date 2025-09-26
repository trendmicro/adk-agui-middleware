# Examples

This folder contains a small set of progressively richer FastAPI examples that demonstrate how to use `adk-agui-middleware` in a clear, minimal, and production‑friendly way. Each example is intentionally simple and self‑contained.

All examples are written in Python with type hints and inline comments. To run them, you will need the core dependencies used by this project (FastAPI, uvicorn, `google-adk`, and `ag-ui`).

Quick start for any example:

```bash
uvicorn app:app --reload
```

If the example lives in a subfolder (e.g., `examples/01_minimal_sse`), run the command from that folder.

Note: Replace the placeholder `agent` with your own ADK agent implementation that extends `google.adk.agents.BaseAgent`.

## 01_minimal_sse

What it shows:
- Minimal setup that streams Server‑Sent Events (SSE) from your ADK agent.
- In‑memory services for sessions, memory, artifacts, and credentials.
- Simple request context extraction from headers.

Files:
- `examples/01_minimal_sse/app.py`

## 02_context_history

What it shows:
- How to register history and state endpoints alongside the main SSE endpoint.
- How to customize thread listing output.
- How to extract `app_name`, `user_id`, and `session_id` from requests.

Files:
- `examples/02_context_history/app.py`

## 03_advanced_pipeline

What it shows:
- How to plug a custom input/output (I/O) recording handler into the pipeline.
- How to pre‑process incoming `RunAgentInput` (e.g., attach metadata) before the run.
- How to use custom URL paths for the main endpoint.

Files:
- `examples/03_advanced_pipeline/app.py`

## 04_lifecycle_handlers

What it shows:
- End-to-end request lifecycle in the middleware with concise comments.
- How to register and wire custom handlers via `HandlerContext`:
  - `adk_event_handler`, `adk_event_timeout_handler`, `agui_event_handler`,
    `agui_state_snapshot_handler`, `translate_handler`, `in_out_record_handler`, `session_lock_handler`.
- Handlers are simple and mostly pass‑through, focusing on observability and structure.

Files:
- `examples/04_lifecycle_handlers/app.py`

## Notes

- The examples avoid any project‑specific business logic. They illustrate the middleware’s public API in a generic way.
- Ensure you have a working ADK agent; the examples include a placeholder variable or a trivial agent stub for clarity.
- For production, consider replacing in‑memory services with durable implementations.
