from ag_ui.core import StateDeltaEvent, EventType

# Create a test event to see its attributes
event = StateDeltaEvent(type=EventType.STATE_DELTA, delta={"test": "value"})
print("StateDeltaEvent attributes:", dir(event))
print("Event:", event)
print("Event dict:", event.model_dump())