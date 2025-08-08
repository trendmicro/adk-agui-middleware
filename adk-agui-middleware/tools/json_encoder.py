import json
from typing import Any

from pydantic import BaseModel


class DataclassesEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, BaseModel):
            return o.model_dump()
        if isinstance(o, bytes):
            return o.decode()
        return super().default(o)
