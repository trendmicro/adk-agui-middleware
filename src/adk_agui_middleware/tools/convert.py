import time
import uuid

from ag_ui.core import BaseEvent


def agui_to_sse(event: BaseEvent) -> dict[str, str]:
    event.timestamp = int(time.time() * 1000)
    return {
        "data": event.model_dump_json(
            by_alias=True, exclude_none=True, exclude={"type"}
        ),
        "event": event.type.value,
        "id": str(uuid.uuid4()),
    }
