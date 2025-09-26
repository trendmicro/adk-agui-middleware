# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-09-26

### Added
- **State Management Service**: New `StateService` class providing comprehensive state operations
  - Support for JSON patch operations for partial state updates
  - Configurable context extraction from HTTP requests
  - State snapshot generation with optional transformation pipeline
  - Session parameter extraction and management
- **Enhanced Configuration Models**:
  - `StateConfig` for state management configuration
  - `HistoryPathConfig` and `StatePathConfig` for better endpoint organization
- **Abstract Handler Improvements**: Added mandatory `__init__` methods to all abstract handler base classes for better interface definition

### Enhanced
- **Endpoint Registration Refactoring**:
  - Split endpoint registration into three focused functions:
    - `register_agui_endpoint()` - Core agent interaction
    - `register_agui_history_endpoint()` - History management
    - `register_state_endpoint()` - State operations
  - Improved separation of concerns and modularity
- **Documentation**: Comprehensive method docstrings and README improvements (+1076 lines)
- **Error Handling**: Enhanced error event processing capabilities
- **Tool Message Conversion**: Improved utility functions for message transformation

### Changed
- **Architecture Separation**: Moved state management functionality from `HistoryService` to dedicated `StateService`
- **Configuration Structure**: Restructured path configuration with specialized config classes
- **Endpoint Organization**: Better endpoint separation based on functionality
- **Handler Interface**: Standardized abstract handler constructors with `InputInfo` parameter

### Removed
- **Code Cleanup**: Removed state management methods from `HistoryService` and `HistoryHandler`
  - `get_state_snapshot()` and `patch_state()` moved to `StateService`
  - Removed unused imports and dependencies
- **Configuration Simplification**: Removed `get_state` from `HistoryConfig` (moved to `StateConfig`)

### Fixed
- **Code Formatting**: Comprehensive formatting cleanup and consistency improvements
- **Import Organization**: Cleaned up unused imports and improved import structure
- **Type Safety**: Enhanced type annotations and error handling

### Breaking Changes
- `register_agui_endpoint()` signature changed - `history_service` parameter removed
- State-related endpoints now require separate `register_state_endpoint()` call
- `HistoryService` no longer provides state management methods - use `StateService` instead
- Abstract handler classes now require `__init__(self, input_info: InputInfo | None)` implementation

### Migration Guide
- Replace `history_service` parameter in `register_agui_endpoint()` with separate service registrations:
  ```python
  # Before
  register_agui_endpoint(app, sse_service, path_config, history_service)

  # After
  register_agui_endpoint(app, sse_service, path_config)
  register_agui_history_endpoint(app, history_service)
  register_state_endpoint(app, state_service)
  ```
- Update custom handler implementations to include proper `__init__` method
- Migrate state operations from `HistoryService` to `StateService`

### Technical Improvements
- **Code Quality**: Enhanced separation of concerns and modularity
- **Performance**: Optimized endpoint registration and state handling
- **Architecture**: Cleaner service boundaries and responsibilities

### Statistics
- **Files Changed**: 14 files
- **Lines Added**: +1,325
- **Lines Removed**: -487
- **Net Change**: +838 lines

## [1.1.0] - 2025-09-25

### Added
- **New Utility Functions**: Added `default_session_id.py` for standardized session ID extraction from AGUI content
- **Enhanced Conversion Tools**: New `agui_tool_message_to_adk_function_response.py` converter for seamless tool message transformation
- **Comprehensive Test Coverage**: Added extensive unit tests for session management (`test_manager_session_comprehensive.py`)
- **Translation Test Suite**: New comprehensive tests for ADK event message conversion (`test_utils_convert_adk_event_message_converter_comprehensive.py`)
- **DeepWiki Integration**: Added DeepWiki badge for enhanced documentation and community support

### Enhanced
- **Documentation Overhaul**: Completely redesigned README with enterprise architecture diagrams, lifecycle documentation, and production-ready examples
- **Session Management**: Significantly improved session ID handling and tool call management in AGUI
- **User Message Processing**: Enhanced user message handling with advanced input conversion capabilities
- **Event Translation**: Improved ADK to AGUI event translation pipeline with better error handling
- **Code Organization**: Restructured utility modules under `utils/convert/` for better maintainability

### Changed
- **Module Restructuring**: Moved conversion utilities to dedicated `utils/convert/` package:
  - `utils/convert.py` → `utils/convert/adk_event_to_agui_message.py`
  - `tools/convert.py` → `utils/convert/agui_event_to_sse.py`
- **Import Path Updates**: Updated import paths for `convert_agui_event_to_sse` function
- **Session Optimization**: Removed redundant long-running tool initialization from user session setup
- **Function Renaming**: Improved naming conventions for input conversion functions

### Removed
- **HITL Workflow Cleanup**: Removed legacy Human-in-the-Loop workflow documentation and related test cases that were no longer applicable
- **Code Simplification**: Cleaned up redundant code in session and user message handlers

### Fixed
- **Code Readability**: Improved indentation and formatting in event final state handling
- **Long-running Tool Checks**: Simplified and enhanced long-running tool validation logic
- **Session State Management**: Better handling of session state transitions and error conditions

### Technical Improvements
- **Test Coverage**: Added 541 lines of comprehensive session management tests
- **Code Quality**: Enhanced type safety and error handling across core modules
- **Performance**: Optimized event processing and translation pipelines
- **Architecture**: Better separation of concerns in handler modules

### Statistics
- **Files Changed**: 39 files modified
- **Lines Added**: +2,431 lines
- **Lines Removed**: -1,245 lines
- **Net Change**: +1,186 lines

### Migration Notes
- Update import statements for conversion utilities if using internal APIs
- Review session configuration if customizing session ID extraction
- Test Human-in-the-Loop workflows with the updated architecture

## [1.0.0] - 2025-09-XX

### Added
- Initial release of ADK AGUI Middleware
- Core middleware functionality for bridging Google ADK with AGUI protocol
- Server-Sent Events streaming capabilities
- Basic session management
- Event translation between ADK and AGUI formats
- FastAPI integration
- Enterprise-grade architecture foundation

---

**Full Changelog**: https://github.com/trendmicro/adk-agui-middleware/compare/v1.0.0...v1.1.0