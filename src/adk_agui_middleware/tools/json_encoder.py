# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Custom JSON encoder for handling Pydantic models and special data types."""

import json
from typing import Any

from pydantic import BaseModel


class PydanticJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Pydantic models and bytes objects.

    Extends the standard JSONEncoder to properly serialize Pydantic BaseModel
    instances and bytes objects that are commonly used in the middleware.
    """

    def default(self, o: Any) -> Any:
        """Override default serialization for custom object types.

        Handles serialization of objects that the standard JSON encoder
        cannot process, including Pydantic models and bytes.

        Args:
            :param o: Object to serialize

        Returns:
            JSON-serializable representation of the object

        Raises:
            TypeError: If object type is not supported by this encoder or base encoder
        """
        # Handle Pydantic BaseModel instances
        if isinstance(o, BaseModel):
            return o.model_dump()
        if isinstance(o, set):
            return list(o)
        if isinstance(o, bytes):
            try:
                return o.decode()
            except UnicodeDecodeError:
                return "[Binary Data]"

        # Fall back to default JSON encoder behavior
        return super().default(o)
