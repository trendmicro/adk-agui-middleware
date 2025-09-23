# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Data model for session parameters in AGUI middleware."""

from pydantic import BaseModel


class SessionParameter(BaseModel):
    """Parameter model for session identification and management.

    Contains the essential identifiers needed to manage user sessions
    across the AGUI middleware system. These parameters uniquely identify
    a session within the context of a specific application and user,
    enabling multi-tenant session management and conversation persistence.

    This model ensures consistent session identification across all
    middleware components and provides the key structure for session
    state management and HITL (Human-in-the-Loop) workflows.

    Attributes:
        app_name: Name of the application owning the session
        user_id: Unique identifier for the user associated with the session
        session_id: Unique identifier for the specific conversation/session
    """

    app_name: str  # Name of the application owning the session
    user_id: str  # Unique identifier for the user associated with the session
    session_id: str  # Unique identifier for the specific conversation/session
