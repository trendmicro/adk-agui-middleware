# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
from typing import Any

from ag_ui.core import RunAgentInput
from fastapi import Request
from pydantic import BaseModel, ConfigDict


class SessionLockConfig(BaseModel):
    lock_timeout: int | None = 300
    lock_retry_times: int = 3
    lock_retry_interval: float = 10.0


class InputInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    agui_content: RunAgentInput
    request: Request
    app_name: str
    user_id: str
    session_id: str
    initial_state: dict[str, Any] | None = None


async def default_session_id(agui_content: RunAgentInput, request: Request) -> str:  # noqa: ARG001
    """Default session ID extractor that uses the thread ID from AGUI content.

    Provides a default implementation for extracting session identifiers from
    incoming AGUI requests. Uses the thread_id as the session identifier,
    enabling conversation continuity across multiple requests.

    Args:
        :param agui_content: Input containing agent execution parameters and thread information
        :param request: HTTP request object (unused in default implementation)

    Returns:
        Thread ID string to be used as session identifier
    """
    return agui_content.thread_id
