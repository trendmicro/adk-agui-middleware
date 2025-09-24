# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
from typing import Any

from ag_ui.core import RunAgentInput
from fastapi import Request
from pydantic import BaseModel, ConfigDict


class SessionLockConfig(BaseModel):
    """Configuration for session locking behavior and timeout settings.

    Defines the parameters for session lock acquisition, retry logic, and timeout
    handling to prevent concurrent access to session data. This configuration
    ensures proper session isolation and prevents race conditions in multi-request
    scenarios while providing graceful handling of lock contention.

    Attributes:
        lock_timeout: Maximum time in seconds to hold a session lock before automatic release
        lock_retry_times: Number of retry attempts when lock acquisition fails
        lock_retry_interval: Time in seconds to wait between lock acquisition retries
    """

    lock_timeout: int | None = 300  # Maximum lock duration in seconds
    lock_retry_times: int = 3  # Number of retry attempts for lock acquisition
    lock_retry_interval: float = 10.0  # Interval between retry attempts in seconds


class InputInfo(BaseModel):
    """Container for processed input information and extracted context.

    Holds all the necessary information extracted from incoming requests and
    processed through context extractors. This model serves as a standardized
    container for passing request context throughout the middleware components,
    enabling consistent access to session identifiers, user context, and
    optional initial state data.

    This model is central to the middleware's operation as it carries the
    essential context needed for session management, agent execution, and
    HITL workflow orchestration.

    Attributes:
        agui_content: Original AGUI input containing messages and execution parameters
        request: HTTP request object containing headers and client information
        app_name: Application name extracted from request context for multi-tenant support
        user_id: User identifier extracted from request context for session isolation
        session_id: Session identifier for conversation persistence and state management
        initial_state: Optional initial state dictionary for new session initialization
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agui_content: RunAgentInput  # Original AGUI input request
    request: Request  # HTTP request object with headers and context
    app_name: str  # Application name for multi-tenant support
    user_id: str  # User identifier for session isolation
    session_id: str  # Session identifier for conversation persistence
    initial_state: dict[str, Any] | None = None  # Optional initial session state
