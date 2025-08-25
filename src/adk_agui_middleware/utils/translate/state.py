from typing import Any

from ag_ui.core import EventType, StateDeltaEvent, StateSnapshotEvent


class StateEventUtil:
    @staticmethod
    def state_delta_event_with_json_patch(
        delta: list[dict[str, Any]],
    ) -> StateDeltaEvent:
        return StateDeltaEvent(type=EventType.STATE_DELTA, delta=delta)

    @staticmethod
    def state_snapshot_event(state_snapshot: dict[str, Any]) -> StateSnapshotEvent:
        return StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT, snapshot=state_snapshot
        )
