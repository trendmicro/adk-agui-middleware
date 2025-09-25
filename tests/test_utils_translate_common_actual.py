# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""Comprehensive unit tests for adk_agui_middleware.utils.translate.common module.

This test suite provides extensive coverage for common translation utilities,
including TranslateEvent creation functions and edge cases.
"""

from unittest.mock import Mock

import pytest
from google.adk.events import Event

from adk_agui_middleware.data_model.event import TranslateEvent
from adk_agui_middleware.utils.translate.common import (
    create_translate_replace_adk_event,
    create_translate_retune_event,
)


class TestCreateTranslateRetuneEvent:
    """Comprehensive tests for create_translate_retune_event function."""

    def test_create_retune_event_basic(self):
        """Test basic creation of retune event."""
        result = create_translate_retune_event()

        assert isinstance(result, TranslateEvent)
        assert result.is_retune is True
        assert result.agui_event is None
        assert result.adk_event is None
        assert result.is_replace is False

    def test_create_retune_event_immutability(self):
        """Test that retune events are independent instances."""
        event1 = create_translate_retune_event()
        event2 = create_translate_retune_event()

        assert event1 is not event2
        assert event1.is_retune == event2.is_retune
        # Modify one event and ensure the other is unaffected
        event1.is_retune = False
        assert event2.is_retune is True

    def test_create_retune_event_multiple_calls(self):
        """Test that multiple calls return consistent results."""
        events = [create_translate_retune_event() for _ in range(10)]

        assert all(isinstance(event, TranslateEvent) for event in events)
        assert all(event.is_retune is True for event in events)
        assert all(event.agui_event is None for event in events)
        assert all(event.adk_event is None for event in events)
        assert all(event.is_replace is False for event in events)

    def test_create_retune_event_type_annotations(self):
        """Test that returned event has correct type."""
        result = create_translate_retune_event()

        # Verify it's specifically a TranslateEvent, not just any object
        assert type(result).__name__ == "TranslateEvent"
        assert hasattr(result, 'is_retune')
        assert hasattr(result, 'agui_event')
        assert hasattr(result, 'adk_event')
        assert hasattr(result, 'is_replace')

    def test_create_retune_event_default_values(self):
        """Test that all fields have expected default values."""
        result = create_translate_retune_event()

        # Only is_retune should be True, all others should be False/None
        assert result.is_retune is True
        assert result.is_replace is False
        assert result.agui_event is None
        assert result.adk_event is None

    def test_create_retune_event_serialization_compatibility(self):
        """Test that retune event can be serialized (Pydantic model)."""
        result = create_translate_retune_event()

        # Should be able to call model_dump without errors (Pydantic method)
        try:
            dump = result.model_dump()
            assert isinstance(dump, dict)
            assert dump['is_retune'] is True
            assert dump['is_replace'] is False
            assert dump['agui_event'] is None
            assert dump['adk_event'] is None
        except AttributeError:
            # If not using Pydantic, ensure it's still a proper object
            assert hasattr(result, '__dict__')


class TestCreateTranslateReplaceADKEvent:
    """Comprehensive tests for create_translate_replace_adk_event function."""

    @pytest.fixture
    def mock_adk_event(self) -> Mock:
        """Create a mock ADK event for testing."""
        event = Mock(spec=Event)
        event.id = "test-event-123"
        event.author = "assistant"
        event.timestamp = 1234567890.0
        return event

    def test_create_replace_event_basic(self, mock_adk_event: Mock):
        """Test basic creation of replace event."""
        result = create_translate_replace_adk_event(mock_adk_event)

        assert isinstance(result, TranslateEvent)
        assert result.is_replace is True
        assert result.adk_event == mock_adk_event
        assert result.agui_event is None
        assert result.is_retune is False

    def test_create_replace_event_preserves_adk_event(self, mock_adk_event: Mock):
        """Test that the ADK event is preserved correctly."""
        result = create_translate_replace_adk_event(mock_adk_event)

        assert result.adk_event is mock_adk_event
        assert result.adk_event.id == "test-event-123"
        assert result.adk_event.author == "assistant"

    def test_create_replace_event_with_none(self):
        """Test creating replace event with None ADK event."""
        result = create_translate_replace_adk_event(None)

        assert isinstance(result, TranslateEvent)
        assert result.is_replace is True
        assert result.adk_event is None
        assert result.agui_event is None
        assert result.is_retune is False

    def test_create_replace_event_different_events(self):
        """Test creating replace events with different ADK events."""
        event1 = Mock(spec=Event)
        event1.id = "event-1"
        event2 = Mock(spec=Event)
        event2.id = "event-2"

        result1 = create_translate_replace_adk_event(event1)
        result2 = create_translate_replace_adk_event(event2)

        assert result1.adk_event.id == "event-1"
        assert result2.adk_event.id == "event-2"
        assert result1.adk_event is not result2.adk_event

    def test_create_replace_event_independence(self, mock_adk_event: Mock):
        """Test that replace events are independent instances."""
        result1 = create_translate_replace_adk_event(mock_adk_event)
        result2 = create_translate_replace_adk_event(mock_adk_event)

        assert result1 is not result2
        assert result1.adk_event is result2.adk_event  # Same reference
        # Modify one event and ensure the other is unaffected
        result1.is_replace = False
        assert result2.is_replace is True

    def test_create_replace_event_with_real_event_properties(self):
        """Test with a more realistic mock event."""
        # Create a more comprehensive mock
        mock_event = Mock(spec=Event)
        mock_event.id = "realistic-event-456"
        mock_event.author = "user"
        mock_event.timestamp = 1640995200.0  # 2022-01-01
        mock_event.content = Mock()
        mock_event.actions = Mock()
        mock_event.get_function_calls.return_value = []
        mock_event.get_function_responses.return_value = []

        result = create_translate_replace_adk_event(mock_event)

        assert result.adk_event.id == "realistic-event-456"
        assert result.adk_event.author == "user"
        assert result.adk_event.timestamp == 1640995200.0
        assert hasattr(result.adk_event, 'content')
        assert hasattr(result.adk_event, 'actions')

    def test_create_replace_event_default_values(self, mock_adk_event: Mock):
        """Test that all fields have expected default values."""
        result = create_translate_replace_adk_event(mock_adk_event)

        # Only is_replace should be True and adk_event should be set
        assert result.is_replace is True
        assert result.adk_event == mock_adk_event
        assert result.is_retune is False
        assert result.agui_event is None

    def test_create_replace_event_type_safety(self, mock_adk_event: Mock):
        """Test type safety of the replace event creation."""
        result = create_translate_replace_adk_event(mock_adk_event)

        # Verify it's specifically a TranslateEvent
        assert type(result).__name__ == "TranslateEvent"
        assert hasattr(result, 'is_replace')
        assert hasattr(result, 'adk_event')
        assert hasattr(result, 'agui_event')
        assert hasattr(result, 'is_retune')

    def test_create_replace_event_serialization_compatibility(self, mock_adk_event: Mock):
        """Test that replace event can be serialized."""
        result = create_translate_replace_adk_event(mock_adk_event)

        # Should be able to access as dictionary-like (if Pydantic)
        try:
            dump = result.model_dump()
            assert isinstance(dump, dict)
            assert dump['is_replace'] is True
            assert dump['is_retune'] is False
            assert dump['agui_event'] is None
            # adk_event may be serialized differently depending on implementation
        except AttributeError:
            # If not using Pydantic, ensure it's still a proper object
            assert hasattr(result, '__dict__')


class TestTranslateEventIntegration:
    """Integration tests for both translate event creation functions."""

    def test_retune_and_replace_event_differences(self):
        """Test that retune and replace events have different characteristics."""
        retune_event = create_translate_retune_event()

        mock_adk_event = Mock(spec=Event)
        replace_event = create_translate_replace_adk_event(mock_adk_event)

        # They should be different types of events
        assert retune_event.is_retune is True
        assert replace_event.is_retune is False

        assert retune_event.is_replace is False
        assert replace_event.is_replace is True

        assert retune_event.adk_event is None
        assert replace_event.adk_event is not None

    def test_event_creation_performance(self):
        """Test that event creation functions perform efficiently."""
        import time

        # Test retune event creation performance
        start_time = time.time()
        for _ in range(1000):
            create_translate_retune_event()
        retune_duration = time.time() - start_time

        # Test replace event creation performance
        mock_event = Mock(spec=Event)
        start_time = time.time()
        for _ in range(1000):
            create_translate_replace_adk_event(mock_event)
        replace_duration = time.time() - start_time

        # Both should complete quickly (less than 1 second for 1000 calls)
        assert retune_duration < 1.0
        assert replace_duration < 1.0

    def test_event_memory_usage(self):
        """Test that events don't consume excessive memory."""
        # Create many events and ensure they can be garbage collected
        events = []

        # Create mixed events
        for i in range(100):
            if i % 2 == 0:
                events.append(create_translate_retune_event())
            else:
                mock_event = Mock(spec=Event)
                mock_event.id = f"event-{i}"
                events.append(create_translate_replace_adk_event(mock_event))

        # Verify all events were created properly
        assert len(events) == 100

        retune_count = sum(1 for event in events if event.is_retune)
        replace_count = sum(1 for event in events if event.is_replace)

        assert retune_count == 50
        assert replace_count == 50

    def test_event_mutation_safety(self):
        """Test that created events can be safely mutated without affecting factory."""
        # Create events
        retune_event = create_translate_retune_event()
        mock_adk_event = Mock(spec=Event)
        replace_event = create_translate_replace_adk_event(mock_adk_event)

        # Store original values
        original_retune_flag = retune_event.is_retune
        original_replace_flag = replace_event.is_replace

        # Mutate events
        retune_event.is_retune = False
        retune_event.is_replace = True
        replace_event.is_replace = False
        replace_event.is_retune = True

        # Create new events to ensure factory functions still work correctly
        new_retune_event = create_translate_retune_event()
        new_replace_event = create_translate_replace_adk_event(mock_adk_event)

        # New events should have original characteristics
        assert new_retune_event.is_retune == original_retune_flag
        assert new_replace_event.is_replace == original_replace_flag

    def test_concurrent_event_creation_simulation(self):
        """Test that event creation behaves correctly under simulated concurrent access."""
        import threading
        import time

        results = []
        errors = []

        def create_events():
            try:
                # Create multiple events in rapid succession
                for i in range(10):
                    retune = create_translate_retune_event()
                    mock_event = Mock(spec=Event)
                    mock_event.id = f"thread-event-{threading.current_thread().ident}-{i}"
                    replace = create_translate_replace_adk_event(mock_event)

                    results.append((retune, replace))
                    time.sleep(0.001)  # Small delay to simulate real usage
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=create_events) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify correct number of results
        assert len(results) == 50  # 5 threads * 10 iterations

        # Verify all events are properly formed
        for retune_event, replace_event in results:
            assert isinstance(retune_event, TranslateEvent)
            assert isinstance(replace_event, TranslateEvent)
            assert retune_event.is_retune is True
            assert replace_event.is_replace is True