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
