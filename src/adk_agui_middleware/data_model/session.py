"""Data model for session parameters in AGUI middleware."""

from pydantic import BaseModel


class SessionParameter(BaseModel):
    """Parameter model for session identification and management.

    Contains the essential identifiers needed to manage user sessions
    across the AGUI middleware system. These parameters uniquely identify
    a session within the context of a specific application and user.

    Attributes:
        app_name: Name of the application owning the session
        user_id: Unique identifier for the user associated with the session
        session_id: Unique identifier for the specific conversation/session
    """

    app_name: str  # Name of the application owning the session
    user_id: str  # Unique identifier for the user associated with the session
    session_id: str  # Unique identifier for the specific conversation/session
