"""Data model for session parameters in AGUI middleware."""

from pydantic import BaseModel


class SessionParameter(BaseModel):
    """Parameter model for session identification and management.

    Contains the essential identifiers needed to manage user sessions
    across the AGUI middleware system.
    """

    app_name: str
    user_id: str
    session_id: str
