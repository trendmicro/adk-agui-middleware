from typing import Any

from pydantic import BaseModel


class LogMessage(BaseModel):
    msg: str
    func_name: str
    error_message: str | None = None
    headers: dict | None = None
    request_body: str | None = None
    body: Any | None = None
    stack_message: Any | None = None
