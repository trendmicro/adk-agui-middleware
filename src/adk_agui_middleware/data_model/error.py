import time
from typing import Any

from pydantic import BaseModel


class ErrorModel(BaseModel):
    error: str
    error_description: dict[str, Any] | str
    timestamp: int = int(time.time())
    trace_id: str = ""


class ErrorResponseModel(BaseModel):
    detail: ErrorModel
