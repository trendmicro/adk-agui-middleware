# Advanced Pipeline Example

## Purpose
This example demonstrates advanced AGUI middleware features, including custom input/output recording and input preprocessing pipelines.

## Features
- Custom input preprocessing pipeline
- I/O recorder for monitoring and debugging
- Tool call metadata injection
- Custom API endpoint paths
- Advanced middleware configuration
- Event transformation capabilities

## Key Components

### `DemoAgent`
A placeholder agent demonstrating integration patterns. Replace with your actual ADK agent implementation.

### `ConsoleIORecorder`
Custom input/output recorder providing:
- **`input_record()`**: Records incoming request information for monitoring/debugging
- **`output_record()`**: Records outgoing SSE events for monitoring/debugging
- **`output_catch_and_change()`**: Transforms outgoing events when needed (use with caution)

### `preprocess_run_input()`
Input preprocessing function that enhances requests when tool calls are detected:
- Checks for tool call information
- Creates `ToolMessage` with tool metadata
- Appends metadata to the message stream
- Enables agent awareness of tool execution context

## Configuration Features

### ConfigContext
- Includes custom input preprocessing functionality
- Supports tool call metadata injection
- Enhanced request context management

### HandlerContext
- Configures I/O recording handlers
- Integrates monitoring and debugging capabilities
- Custom pipeline event handling

### Custom Endpoint Path
Uses `/api/v1/agui` as the main endpoint, demonstrating API versioning best practices.

## Running the Application
```bash
uvicorn app:app --reload
```

## Endpoints
- `POST /api/v1/agui` - Main SSE endpoint with advanced pipeline features

## Use Cases
- Production environments requiring detailed monitoring and logging
- Complex applications needing tool call preprocessing
- Systems requiring custom API versioning
- Applications with special input/output transformation needs
- Advanced debugging and observability requirements

## Advanced Features
- **Tool Metadata Injection**: Automatically adds metadata when tool calls are detected
- **I/O Recording**: Complete request/response recording for monitoring
- **Event Transformation**: Support for transforming events before SSE output
- **Pipeline Customization**: Extensible middleware pipeline

## Key Learning Points
- How to implement custom I/O recording
- Input preprocessing for tool-enhanced interactions
- Custom API path configuration
- Advanced middleware pipeline patterns
- Monitoring and debugging integration