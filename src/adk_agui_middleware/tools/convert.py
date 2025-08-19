import time

from ag_ui.core import BaseEvent


def agui_to_sse(event: BaseEvent) -> dict[str, str]:
    return {
        "data": event.model_dump_json(
            by_alias=True, exclude_none=True, exclude={"type"}
        ),
        "event": event.type.value,
        "id": str(int(time.time() * 1000)),
    }
