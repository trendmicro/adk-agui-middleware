"""Unit tests for adk_agui_middleware.handler.session module."""

import sys
import os
import unittest
import importlib.util
import asyncio
from unittest.mock import AsyncMock, Mock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock external dependencies
class MockSession:
    def __init__(self):
        pass

class MockSessionParameter:
    def __init__(self, app_name="test_app", user_id="test_user", session_id="test_session"):
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id

class MockSessionManager:
    def __init__(self):
        self.get_session = AsyncMock()
        self.get_session_state = AsyncMock()
        self.check_and_create_session = AsyncMock()
        self.update_session_state = AsyncMock()

# Mock logging functions
mock_record_log = Mock()
mock_record_warning_log = Mock()
mock_record_error_log = Mock()

# Mock all external dependencies
sys.modules['data_model'] = Mock()
sys.modules['data_model.session'] = Mock()
sys.modules['data_model.session'].SessionParameter = MockSessionParameter
sys.modules['google'] = Mock()
sys.modules['google.adk'] = Mock()
sys.modules['google.adk.sessions'] = Mock()
sys.modules['google.adk.sessions'].Session = MockSession
sys.modules['loggers'] = Mock()
sys.modules['loggers.record_log'] = Mock()
sys.modules['loggers.record_log'].record_error_log = mock_record_error_log
sys.modules['loggers.record_log'].record_log = mock_record_log
sys.modules['loggers.record_log'].record_warning_log = mock_record_warning_log
sys.modules['manager'] = Mock()
sys.modules['manager.session'] = Mock()
sys.modules['manager.session'].SessionManager = MockSessionManager

# Load the handler.session module directly
spec = importlib.util.spec_from_file_location(
    "handler_session_module", 
    os.path.join(os.path.dirname(__file__), '..', 'src', 'adk_agui_middleware', 'handler', 'session.py')
)
handler_session_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler_session_module)

SessionHandler = handler_session_module.SessionHandler


class TestSessionHandler(unittest.TestCase):
    """Test cases for the SessionHandler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session_manager = MockSessionManager()
        self.session_parameter = MockSessionParameter(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session"
        )
        self.handler = SessionHandler(
            session_manger=self.mock_session_manager,
            session_parameter=self.session_parameter
        )

    def test_init(self):
        """Test SessionHandler initialization."""
        self.assertEqual(self.handler.session_manger, self.mock_session_manager)
        self.assertEqual(self.handler.session_parameter, self.session_parameter)

    def test_app_name_property(self):
        """Test app_name property returns correct value."""
        self.assertEqual(self.handler.app_name, "test_app")

    def test_user_id_property(self):
        """Test user_id property returns correct value."""
        self.assertEqual(self.handler.user_id, "test_user")

    def test_session_id_property(self):
        """Test session_id property returns correct value."""
        self.assertEqual(self.handler.session_id, "test_session")

    def test_get_pending_tool_calls_dict(self):
        """Test get_pending_tool_calls_dict static method."""
        pending_calls = ["tool1", "tool2", "tool3"]
        result = SessionHandler.get_pending_tool_calls_dict(pending_calls)
        
        expected = {"pending_tool_calls": pending_calls}
        self.assertEqual(result, expected)

    def test_get_pending_tool_calls_dict_empty_list(self):
        """Test get_pending_tool_calls_dict with empty list."""
        result = SessionHandler.get_pending_tool_calls_dict([])
        
        expected = {"pending_tool_calls": []}
        self.assertEqual(result, expected)

    def test_get_session(self):
        """Test get_session method."""
        async def run_test():
            mock_session = MockSession()
            self.mock_session_manager.get_session = AsyncMock(return_value=mock_session)
            
            result = await self.handler.get_session()
            
            self.assertEqual(result, mock_session)
            self.mock_session_manager.get_session.assert_called_once_with(self.session_parameter)
        
        asyncio.run(run_test())

    def test_get_session_none(self):
        """Test get_session method returning None."""
        async def run_test():
            self.mock_session_manager.get_session = AsyncMock(return_value=None)
            
            result = await self.handler.get_session()
            
            self.assertIsNone(result)
        
        asyncio.run(run_test())

    def test_get_session_state(self):
        """Test get_session_state method."""
        async def run_test():
            expected_state = {"key1": "value1", "pending_tool_calls": ["tool1"]}
            self.mock_session_manager.get_session_state = AsyncMock(return_value=expected_state)
            
            result = await self.handler.get_session_state()
            
            self.assertEqual(result, expected_state)
            self.mock_session_manager.get_session_state.assert_called_once_with(self.session_parameter)
        
        asyncio.run(run_test())

    def test_check_and_create_session_with_initial_state(self):
        """Test check_and_create_session with initial state."""
        async def run_test():
            mock_session = MockSession()
            initial_state = {"initial_key": "initial_value"}
            self.mock_session_manager.check_and_create_session = AsyncMock(return_value=mock_session)
            
            result = await self.handler.check_and_create_session(initial_state)
            
            self.assertEqual(result, mock_session)
            self.mock_session_manager.check_and_create_session.assert_called_once_with(
                session_parameter=self.session_parameter,
                initial_state=initial_state
            )
        
        asyncio.run(run_test())

    def test_check_and_create_session_without_initial_state(self):
        """Test check_and_create_session without initial state."""
        async def run_test():
            mock_session = MockSession()
            self.mock_session_manager.check_and_create_session = AsyncMock(return_value=mock_session)
            
            result = await self.handler.check_and_create_session()
            
            self.assertEqual(result, mock_session)
            self.mock_session_manager.check_and_create_session.assert_called_once_with(
                session_parameter=self.session_parameter,
                initial_state=None
            )
        
        asyncio.run(run_test())

    def test_update_session_state_success(self):
        """Test update_session_state successful update."""
        async def run_test():
            state_updates = {"key": "value", "count": 42}
            self.mock_session_manager.update_session_state = AsyncMock(return_value=True)
            
            result = await self.handler.update_session_state(state_updates)
            
            self.assertTrue(result)
            self.mock_session_manager.update_session_state.assert_called_once_with(
                session_parameter=self.session_parameter,
                state_updates=state_updates
            )
        
        asyncio.run(run_test())

    def test_update_session_state_failure(self):
        """Test update_session_state failed update."""
        async def run_test():
            state_updates = {"key": "value"}
            self.mock_session_manager.update_session_state = AsyncMock(return_value=False)
            
            result = await self.handler.update_session_state(state_updates)
            
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_session_parameter_modification(self):
        """Test that modifying session parameter affects handler properties."""
        # Create handler with different session parameter
        new_param = MockSessionParameter(
            app_name="new_app",
            user_id="new_user", 
            session_id="new_session"
        )
        new_handler = SessionHandler(self.mock_session_manager, new_param)
        
        self.assertEqual(new_handler.app_name, "new_app")
        self.assertEqual(new_handler.user_id, "new_user")
        self.assertEqual(new_handler.session_id, "new_session")

    def test_async_method_call_order(self):
        """Test that async methods can be called in sequence."""
        async def run_test():
            # Setup mocks
            self.mock_session_manager.get_session = AsyncMock(return_value=MockSession())
            self.mock_session_manager.get_session_state = AsyncMock(return_value={})
            self.mock_session_manager.check_and_create_session = AsyncMock(return_value=MockSession())
            self.mock_session_manager.update_session_state = AsyncMock(return_value=True)
            
            # Call methods in sequence
            session = await self.handler.get_session()
            state = await self.handler.get_session_state()
            created_session = await self.handler.check_and_create_session()
            update_result = await self.handler.update_session_state({"key": "value"})
            
            # Verify all methods were called
            self.assertIsNotNone(session)
            self.assertEqual(state, {})
            self.assertIsNotNone(created_session)
            self.assertTrue(update_result)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()