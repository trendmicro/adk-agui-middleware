# Lifecycle Handlers Example

## Purpose
This example demonstrates comprehensive lifecycle management and custom handlers that plug into the AGUI middleware event pipeline. It provides extensive inline documentation of the end-to-end request lifecycle and shows how to customize every stage of event processing.

## Features
- Complete lifecycle event handling demonstration
- Custom session locking mechanism
- ADK event preprocessing and timeout handling
- Custom event translation hooks
- AGUI event post-processing
- State snapshot transformation
- Comprehensive I/O recording
- Detailed pipeline stage documentation

## Key Components

### `build_llm_agent()`
Creates an LlmAgent from google.adk with environment-based model configuration and version compatibility.

### `InMemorySessionLock`
Simple in-memory session lock implementation that:
- Prevents concurrent runs on the same (app, user, session) triple
- Provides configurable retry logic with timeout
- Generates appropriate error messages for locked sessions
- Demonstrates session locking patterns for production systems

### Lifecycle Handlers

#### `LifecycleADKEventHandler`
ADK event preprocessor for:
- Filtering internal roles
- Modifying event metadata
- Implementing custom event routing
- Demonstrating event processing placement in pipeline

#### `LifecycleTimeoutHandler`
Timeout policy handler that:
- Configures timeout duration for ADK event processing
- Provides fallback event generation on timeout
- Demonstrates timeout handling strategies

#### `LifecycleTranslateHandler`
Event translation interceptor that:
- Allows custom event translation logic
- Demonstrates translation stage hooks
- Shows how to override default translation behavior

#### `LifecycleAGUIEventHandler`
AGUI event post-processor for:
- Filtering or reshaping AGUI events before SSE encoding
- Final-stage event modification
- Client-specific event customization

#### `LifecycleStateHandler`
State snapshot transformer that:
- Filters sensitive server-only keys
- Enriches state data for clients
- Demonstrates state security patterns

#### `LifecycleIORecorder`
Comprehensive I/O recorder that:
- Records incoming request context
- Logs outgoing SSE frames
- Provides monitoring and debugging capabilities
- Demonstrates observability integration

## Pipeline Architecture

### Request Lifecycle Stages
1. **Session Locking**: Prevents concurrent processing
2. **Input Recording**: Logs request context
3. **ADK Event Processing**: Handles agent events with timeout
4. **Event Translation**: Converts ADK events to AGUI format
5. **AGUI Event Processing**: Final event modifications
6. **State Snapshot**: Transforms state for client
7. **Output Recording**: Logs SSE responses

### Handler Integration Points
- **Session Management**: Custom locking strategies
- **Event Processing**: ADK event filtering and modification
- **Translation**: Custom ADK-to-AGUI event translation
- **Output Processing**: Final event transformation
- **State Management**: Client-safe state filtering
- **Observability**: Complete I/O monitoring

## Configuration

### HandlerContext
Comprehensive handler configuration including:
- Session lock handler for concurrency control
- ADK event processing and timeout handlers
- Translation intercept hooks
- AGUI event and state handlers
- I/O recording for monitoring

## Running the Application
```bash
uvicorn app:app --reload
```

## Endpoints
- `POST /lifecycle/agui` - Main SSE endpoint with full lifecycle handling

## Environment Variables
- `ADK_MODEL_NAME` (optional): Specifies the LLM model name, defaults to `gemini-1.5-flash`

## Use Cases
- Production systems requiring comprehensive event lifecycle management
- Applications needing custom session concurrency control
- Systems requiring detailed event processing customization
- Complex debugging and monitoring requirements
- Custom translation and filtering needs
- Educational purposes for understanding AGUI middleware internals

## Key Learning Points
- Complete AGUI middleware pipeline understanding
- Custom handler implementation patterns
- Session locking and concurrency management
- Event transformation and filtering techniques
- Timeout handling and fallback strategies
- State security and client data filtering
- Comprehensive monitoring and logging integration

## Production Considerations
- Replace in-memory session lock with Redis or database-backed implementation
- Implement proper error handling and recovery mechanisms
- Configure appropriate timeouts for your use case
- Add structured logging for production monitoring
- Consider security implications of state filtering
- Implement proper authentication and authorization