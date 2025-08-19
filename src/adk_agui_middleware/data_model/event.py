from ag_ui.core import BaseEvent


class TranslateEvent:
    agui_event: BaseEvent | None = None
    is_retune: bool = True
    is_skip: bool = False
