"""Unit tests for adk_agui_middleware.handler.running module."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ag_ui.core import BaseEvent, EventType, StateSnapshotEvent, ToolCallEndEvent
from google.adk import Runner
from google.adk.agents import RunConfig
from google.adk.events import Event

from adk_agui_middleware.data_model.context import HandlerContext
from adk_agui_middleware.handler.running import RunningHandler
from adk_agui_middleware.base_abc.handler import (
    BaseADKEventHandler,
    BaseADKEventTimeoutHandler,
    BaseAGUIEventHandler,
    BaseAGUIStateSnapshotHandler,
    BaseTranslateHandler,
)


class TestRunningHandler(unittest.TestCase):
    """Test cases for RunningHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_runner = Mock(spec=Runner)
        self.mock_run_config = Mock(spec=RunConfig)
        self.handler_context = HandlerContext()
        
        self.handler = RunningHandler(
            self.mock_runner, self.mock_run_config, self.handler_context
        )

    def test_init(self):
        """Test RunningHandler initialization."""
        self.assertEqual(self.handler.runner, self.mock_runner)
        self.assertEqual(self.handler.run_config, self.mock_run_config)
        self.assertIsNotNone(self.handler.event_translator)
        self.assertFalse(self.handler.is_long_running_tool)
        
        # All handlers should be None by default
        self.assertIsNone(self.handler.adk_event_handler)
        self.assertIsNone(self.handler.adk_event_timeout_handler)
        self.assertIsNone(self.handler.agui_event_handler)
        self.assertIsNone(self.handler.agui_state_snapshot_handler)
        self.assertIsNone(self.handler.translate_handler)

    def test_init_handler_with_all_handlers(self):
        """Test initialization with all handler types."""
        # Create actual subclasses instead of mocks to pass Pydantic validation
        class MockADKEventHandler(BaseADKEventHandler):
            async def process(self, event): 
                yield event
        
        class MockADKEventTimeoutHandler(BaseADKEventTimeoutHandler):
            async def get_timeout(self): 
                return 30
            async def process_timeout_fallback(self): 
                yield "timeout"
        
        class MockAGUIEventHandler(BaseAGUIEventHandler):
            async def process(self, event): 
                yield event
        
        class MockAGUIStateSnapshotHandler(BaseAGUIStateSnapshotHandler):
            async def process(self, state): 
                return state
        
        class MockTranslateHandler(BaseTranslateHandler):
            async def translate(self, event): 
                from adk_agui_middleware.data_model.context import TranslateEvent
                yield TranslateEvent(agui_event=None, is_retune=False)
        
        context = HandlerContext(
            adk_event_handler=MockADKEventHandler,
            adk_event_timeout_handler=MockADKEventTimeoutHandler,
            agui_event_handler=MockAGUIEventHandler,
            agui_state_snapshot_handler=MockAGUIStateSnapshotHandler,
            translate_handler=MockTranslateHandler,
        )
        
        handler = RunningHandler(self.mock_runner, self.mock_run_config, context)
        
        self.assertIsNotNone(handler.adk_event_handler)
        self.assertIsNotNone(handler.adk_event_timeout_handler)
        self.assertIsNotNone(handler.agui_event_handler)
        self.assertIsNotNone(handler.agui_state_snapshot_handler)
        self.assertIsNotNone(handler.translate_handler)

    async def test_process_events_with_handler_no_handler(self):
        """Test processing events without a handler."""
        async def mock_event_stream():
            yield "event1"
            yield "event2"
        
        mock_log_func = Mock()
        
        events = []
        async for event in self.handler._process_events_with_handler(
            mock_event_stream(), mock_log_func
        ):
            events.append(event)
        
        self.assertEqual(events, ["event1", "event2"])
        self.assertEqual(mock_log_func.call_count, 2)

    async def test_process_events_with_handler_with_handler(self):
        """Test processing events with a handler."""
        async def mock_event_stream():
            yield "event1"
            yield "event2"
        
        mock_handler = Mock(spec=BaseADKEventHandler)
        
        async def mock_process(event):
            yield f"processed_{event}"
        
        mock_handler.process = AsyncMock(side_effect=mock_process)
        mock_log_func = Mock()
        
        events = []
        async for event in self.handler._process_events_with_handler(
            mock_event_stream(), mock_log_func, mock_handler
        ):
            events.append(event)
        
        self.assertEqual(events, ["processed_event1", "processed_event2"])
        self.assertEqual(mock_log_func.call_count, 2)

    async def test_process_events_with_handler_filtered_none(self):
        """Test processing events where handler returns None."""
        async def mock_event_stream():
            yield "event1"
            yield "event2"
        
        mock_handler = Mock(spec=BaseADKEventHandler)
        
        async def mock_process(event):
            if event == "event1":
                yield None
            else:
                yield f"processed_{event}"
        
        mock_handler.process = AsyncMock(side_effect=mock_process)
        mock_log_func = Mock()
        
        events = []
        async for event in self.handler._process_events_with_handler(
            mock_event_stream(), mock_log_func, mock_handler
        ):
            events.append(event)
        
        self.assertEqual(events, ["processed_event2"])

    @patch("adk_agui_middleware.handler.running.record_warning_log")
    async def test_process_events_with_timeout(self, mock_warning_log):
        """Test processing events with timeout."""
        async def slow_event_stream():
            await asyncio.sleep(0.1)
            yield "event1"
        
        # Set up timeout handler
        mock_timeout_handler = Mock(spec=BaseADKEventTimeoutHandler)
        mock_timeout_handler.get_timeout = AsyncMock(return_value=0.05)  # 50ms timeout
        
        async def mock_timeout_fallback():
            yield "timeout_event"
        
        mock_timeout_handler.process_timeout_fallback = AsyncMock(return_value=mock_timeout_fallback())
        self.handler.adk_event_timeout_handler = mock_timeout_handler
        
        mock_log_func = Mock()
        
        events = []
        async for event in self.handler._process_events_with_handler(
            slow_event_stream(), mock_log_func, enable_timeout=True
        ):
            events.append(event)
        
        self.assertEqual(events, ["timeout_event"])
        mock_warning_log.assert_called_once()

    @patch("adk_agui_middleware.handler.running.record_warning_log")
    async def test_process_events_timeout_no_timeout_handler(self, mock_warning_log):
        """Test timeout without timeout handler."""
        async def slow_event_stream():
            await asyncio.sleep(0.1)
            yield "event1"
        
        mock_log_func = Mock()
        
        # Override timeout for test
        with patch("asyncio.timeout") as mock_timeout:
            mock_timeout.side_effect = asyncio.TimeoutError()
            
            events = []
            async for event in self.handler._process_events_with_handler(
                slow_event_stream(), mock_log_func, enable_timeout=True
            ):
                events.append(event)
        
        self.assertEqual(events, [])
        mock_warning_log.assert_called_once()

    def test_check_is_long_tool(self):
        """Test checking for long-running tools."""
        mock_adk_event = Mock(spec=Event)
        mock_adk_event.is_final_response.return_value = True
        
        mock_agui_event = Mock(spec=BaseEvent)
        mock_agui_event.type = EventType.TOOL_CALL_END
        
        self.handler._check_is_long_tool(mock_adk_event, mock_agui_event)
        self.assertTrue(self.handler.is_long_running_tool)

    def test_check_is_long_tool_not_final_response(self):
        """Test check when not final response."""
        mock_adk_event = Mock(spec=Event)
        mock_adk_event.is_final_response.return_value = False
        
        mock_agui_event = Mock(spec=BaseEvent)
        mock_agui_event.type = EventType.TOOL_CALL_END
        
        self.handler._check_is_long_tool(mock_adk_event, mock_agui_event)
        self.assertFalse(self.handler.is_long_running_tool)

    def test_check_is_long_tool_not_tool_call_end(self):
        """Test check when not tool call end event."""
        mock_adk_event = Mock(spec=Event)
        mock_adk_event.is_final_response.return_value = True
        
        mock_agui_event = Mock(spec=BaseEvent)
        mock_agui_event.type = EventType.TEXT_MESSAGE_START
        
        self.handler._check_is_long_tool(mock_adk_event, mock_agui_event)
        self.assertFalse(self.handler.is_long_running_tool)

    async def test_run_async_translator_adk_to_agui_with_translate_handler(self):
        """Test translation with custom translate handler."""
        mock_translate_handler = Mock(spec=BaseTranslateHandler)
        
        mock_translate_result = Mock()
        mock_translate_result.agui_event = Mock(spec=BaseEvent)
        mock_translate_result.agui_event.type = EventType.TEXT_MESSAGE_START
        mock_translate_result.is_retune = False
        
        async def mock_translate(event):
            yield mock_translate_result
        
        mock_translate_handler.translate = AsyncMock(return_value=mock_translate(None))
        self.handler.translate_handler = mock_translate_handler
        
        mock_adk_event = Mock(spec=Event)
        mock_adk_event.is_final_response.return_value = False
        
        events = []
        async for event in self.handler._run_async_translator_adk_to_agui(mock_adk_event):
            events.append(event)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], mock_translate_result.agui_event)

    async def test_run_async_translator_adk_to_agui_retune(self):
        """Test translation with retune signal."""
        mock_translate_handler = Mock(spec=BaseTranslateHandler)
        
        mock_translate_result1 = Mock()
        mock_translate_result1.agui_event = Mock(spec=BaseEvent)
        mock_translate_result1.agui_event.type = EventType.TEXT_MESSAGE_START
        mock_translate_result1.is_retune = False
        
        mock_translate_result2 = Mock()
        mock_translate_result2.agui_event = None
        mock_translate_result2.is_retune = True
        
        async def mock_translate(event):
            yield mock_translate_result1
            yield mock_translate_result2
        
        mock_translate_handler.translate = AsyncMock(return_value=mock_translate(None))
        self.handler.translate_handler = mock_translate_handler
        
        mock_adk_event = Mock(spec=Event)
        
        events = []
        async for event in self.handler._run_async_translator_adk_to_agui(mock_adk_event):
            events.append(event)
        
        self.assertEqual(len(events), 1)  # Should stop at retune

    async def test_run_async_translator_adk_to_agui_without_handler_incomplete(self):
        """Test translation without handler for incomplete response."""
        mock_adk_event = Mock(spec=Event)
        mock_adk_event.content = Mock()
        mock_adk_event.content.parts = ["part1"]
        mock_adk_event.is_final_response.return_value = False
        mock_adk_event.usage_metadata = None
        
        mock_agui_event = Mock(spec=BaseEvent)
        mock_agui_event.type = EventType.TEXT_MESSAGE_START
        
        # Mock the event translator
        with patch.object(self.handler.event_translator, 'translate') as mock_translate:
            async def mock_translate_gen(event):
                yield mock_agui_event
            
            mock_translate.return_value = mock_translate_gen(mock_adk_event)
            
            events = []
            async for event in self.handler._run_async_translator_adk_to_agui(mock_adk_event):
                events.append(event)
        
        self.assertEqual(len(events), 1)
        mock_translate.assert_called_once_with(mock_adk_event)

    async def test_run_async_translator_adk_to_agui_without_handler_lro(self):
        """Test translation for long-running operation."""
        mock_adk_event = Mock(spec=Event)
        mock_adk_event.content = Mock()
        mock_adk_event.content.parts = ["part1"]
        mock_adk_event.is_final_response.return_value = True
        mock_adk_event.usage_metadata = {"tokens": 100}
        
        mock_agui_event = Mock(spec=BaseEvent)
        mock_agui_event.type = EventType.TOOL_CALL_START
        
        # Mock the event translator
        with patch.object(self.handler.event_translator, 'translate_lro_function_calls') as mock_translate_lro:
            async def mock_translate_gen(event):
                yield mock_agui_event
            
            mock_translate_lro.return_value = mock_translate_gen(mock_adk_event)
            
            events = []
            async for event in self.handler._run_async_translator_adk_to_agui(mock_adk_event):
                events.append(event)
        
        self.assertEqual(len(events), 1)
        mock_translate_lro.assert_called_once_with(mock_adk_event)

    def test_force_close_streaming_message(self):
        """Test force closing streaming message."""
        with patch.object(self.handler.event_translator, 'force_close_streaming_message') as mock_force_close:
            result = self.handler.force_close_streaming_message()
            self.assertEqual(result, mock_force_close.return_value)
            mock_force_close.assert_called_once()

    async def test_create_state_snapshot_event_with_handler(self):
        """Test creating state snapshot with state handler."""
        mock_state_handler = Mock(spec=BaseAGUIStateSnapshotHandler)
        mock_state_handler.process = AsyncMock(return_value={"processed": "state"})
        self.handler.agui_state_snapshot_handler = mock_state_handler
        
        final_state = {"original": "state"}
        
        with patch.object(self.handler.event_translator, 'create_state_snapshot_event') as mock_create:
            mock_create.return_value = Mock(spec=StateSnapshotEvent)
            
            result = await self.handler.create_state_snapshot_event(final_state)
            
            mock_state_handler.process.assert_called_once_with(final_state)
            mock_create.assert_called_once_with({"processed": "state"})

    async def test_create_state_snapshot_event_without_handler(self):
        """Test creating state snapshot without state handler."""
        final_state = {"original": "state"}
        
        with patch.object(self.handler.event_translator, 'create_state_snapshot_event') as mock_create:
            mock_create.return_value = Mock(spec=StateSnapshotEvent)
            
            result = await self.handler.create_state_snapshot_event(final_state)
            
            mock_create.assert_called_once_with(final_state)

    def test_run_async_with_adk(self):
        """Test running with ADK."""
        args = ("arg1", "arg2")
        kwargs = {"key": "value"}
        
        with patch.object(self.handler, '_process_events_with_handler') as mock_process:
            with patch.object(self.mock_runner, 'run_async') as mock_run_async:
                mock_run_async.return_value = "mock_stream"
                
                result = self.handler.run_async_with_adk(*args, **kwargs)
                
                mock_run_async.assert_called_once_with(
                    *args, run_config=self.mock_run_config, **kwargs
                )
                mock_process.assert_called_once()

    def test_run_async_with_agui(self):
        """Test running with AGUI."""
        mock_adk_event = Mock(spec=Event)
        
        with patch.object(self.handler, '_process_events_with_handler') as mock_process:
            with patch.object(self.handler, '_translate_adk_to_agui_async') as mock_translate:
                mock_translate.return_value = "mock_stream"
                
                result = self.handler.run_async_with_agui(mock_adk_event)
                
                mock_translate.assert_called_once_with(mock_adk_event)
                mock_process.assert_called_once()


if __name__ == "__main__":
    unittest.main()