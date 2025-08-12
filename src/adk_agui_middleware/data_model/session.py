from pydantic import BaseModel


class SessionParameter(BaseModel):
    app_name: str
    user_id: str
    session_id: str
