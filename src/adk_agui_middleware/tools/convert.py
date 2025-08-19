import uuid

from ag_ui.core import BaseEvent


def agui_to_sse(event: BaseEvent) -> dict[str, str]:
    return {
        "data": event.raw_event.model_dump_json(by_alias=True, exclude_none=True),
        "event": event.type.value,
        "id": str(uuid.uuid4()),
    }
