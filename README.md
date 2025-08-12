# ADK AGUI Python Middleware

A professional Python middleware library that bridges Agent Development Kit (ADK) agents with AGUI (Agent UI) protocol, providing Server-Sent Events (SSE) streaming capabilities for real-time agent interactions.

## Overview

This middleware facilitates seamless integration between Google's Agent Development Kit and AGUI-compatible frontends, enabling developers to build interactive agent applications with real-time streaming responses. The library handles agent execution, session management, event encoding, and error handling in a production-ready framework.

## Features

- **Real-time Streaming**: Server-Sent Events (SSE) support for live agent responses
- **Session Management**: Comprehensive session handling with configurable backends
- **Context Extraction**: Flexible context configuration for multi-tenant applications  
- **Error Handling**: Robust error handling with detailed logging and recovery
- **Tool Integration**: Support for tool calls and tool result processing
- **Event Encoding**: Multiple event encoding formats with automatic content negotiation
- **Type Safety**: Full type annotations with Pydantic models
- **Extensible Architecture**: Abstract base classes for custom implementations

## Architecture

The middleware follows a modular architecture with clear separation of concerns:

```
├── base_abc/           # Abstract base classes
├── config/            # Configuration and logging setup
├── data_model/        # Pydantic models and data structures
├── endpoint.py        # FastAPI endpoint registration
├── event/             # Event handling and error events
├── handler/           # Request and session handlers
├── loggers/           # Logging infrastructure
├── manager/           # Session and resource management
├── sse_service.py     # Core SSE service implementation
└── tools/             # Utility functions and converters
```

## Installation

### Using pip

```bash
pip install adk-agui-py-middleware
```

Available on PyPI: https://pypi.org/project/adk-agui-py-middleware/

### Requirements

- Python 3.13+
- Google ADK (`google-adk>=1.10.0`)
- AGUI Protocol (`ag-ui-protocol>=0.1.8`)
- Pydantic (`pydantic>=2.11.7`)

### Development Install

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

## Quick Start

### Basic Setup

```python
from fastapi import FastAPI
from google.adk.agents import BaseAgent
from adk_agui_middleware import register_agui_endpoint, SSEService
from adk_agui_middleware.data_model.context import RunnerConfig, ContextConfig

# Create your FastAPI app
app = FastAPI()

# Initialize your ADK agent
agent = BaseAgent()  # Your custom agent implementation

# Configure context extraction
context_config = ContextConfig(
    app_name="my-agent-app",
    user_id="user-123",  # Can be a callable for dynamic extraction
)

# Configure runner services
runner_config = RunnerConfig(
    use_in_memory_services=True  # Use in-memory services for development
)

# Create SSE service
sse_service = SSEService(
    agent=agent,
    runner_config=runner_config,
    context_config=context_config
)

# Register the AGUI endpoint
register_agui_endpoint(app, sse_service, path="/agui")
```

### Dynamic Context Extraction

For multi-tenant applications, you can extract context dynamically from requests:

```python
from ag_ui.core import RunAgentInput
from fastapi import Request

async def extract_user_id(agui_content: RunAgentInput, request: Request) -> str:
    """Extract user ID from JWT token or headers"""
    token = request.headers.get("authorization")
    # Your authentication logic here
    return decoded_user_id

async def extract_app_name(agui_content: RunAgentInput, request: Request) -> str:
    """Extract app name from subdomain or headers"""
    host = request.headers.get("host", "")
    return host.split(".")[0] if "." in host else "default"

context_config = ContextConfig(
    app_name=extract_app_name,
    user_id=extract_user_id,
    session_id=lambda content, req: content.thread_id  # Use thread ID as session
)
```

### Custom Services Configuration

For production deployments, configure external services:

```python
from google.adk.sessions import DatabaseSessionService
from google.adk.memory import RedisMemoryService

runner_config = RunnerConfig(
    use_in_memory_services=False,
    session_service=DatabaseSessionService(connection_string="..."),
    memory_service=RedisMemoryService(redis_url="..."),
    # artifact_service and credential_service as needed
)
```

## Advanced Usage

### Custom SSE Service

Extend the base SSE service for custom behavior:

```python
from adk_agui_middleware.base_abc.sse_service import BaseSSEService

class CustomSSEService(BaseSSEService):
    async def get_runner(self, agui_content, request):
        # Custom runner logic
        pass
    
    async def event_generator(self, runner, encoder):
        # Custom event generation
        async for event in runner():
            # Custom event processing
            yield encoder.encode(event)
```

### Error Handling

The middleware includes comprehensive error handling with logging:

```python
from adk_agui_middleware.loggers.logger import setup_logging

# Configure logging
setup_logging(level="INFO")

# Error events are automatically generated for:
# - Agent execution errors
# - Encoding failures  
# - Tool execution errors
# - Session management issues
```

### Tool Integration

Handle tool calls and results seamlessly:

```python
# Tool calls are automatically extracted from AGUI messages
# Tool results are processed and converted to the appropriate format
# No additional configuration required - handled by UserMessageHandler
```

## API Reference

### Core Classes

- **`SSEService`**: Main service implementation for handling agent interactions
- **`register_agui_endpoint()`**: Function to register the AGUI endpoint on FastAPI
- **`ContextConfig`**: Configuration for extracting context from requests
- **`RunnerConfig`**: Configuration for ADK runner and services
- **`UserMessageHandler`**: Processes user messages and tool results

### Data Models

- **`SessionParameter`**: Session identification parameters
- **`BaseEvent`**: Base class for agent events
- **Various error models**: Structured error handling

## Development

### Code Quality

The project uses comprehensive linting and formatting:

```bash
# Format code
ruff format

# Lint code  
ruff check

# Type checking
mypy src/
```

### Testing

```bash
# Run tests (configure based on your test setup)
pytest

# With coverage
pytest --cov=adk_agui_middleware
```

## Configuration

### Environment Variables

Configure the middleware using environment variables or configuration files:

```bash
# Logging level
LOG_LEVEL=INFO

# Service configurations
USE_IN_MEMORY_SERVICES=true
SESSION_SERVICE_URL=redis://localhost:6379
```

### Runtime Configuration

```python
from adk_agui_middleware.config.log import setup_logging

# Configure logging
setup_logging(
    level="DEBUG",
    format="json",  # or "text"
    output="file"   # or "console"
)
```

## Production Considerations

### Performance

- Use external services (Redis, PostgreSQL) instead of in-memory services
- Configure appropriate connection pooling
- Monitor memory usage for long-running sessions
- Implement proper session cleanup policies

### Security

- Validate all incoming requests
- Implement proper authentication and authorization
- Use HTTPS in production
- Configure CORS appropriately
- Sanitize user inputs and tool results

### Monitoring

- Monitor agent execution times
- Track error rates and types
- Monitor session lifecycle
- Log security events and access patterns

## Contributing

1. Follow the existing code style and conventions
2. Add comprehensive docstrings using Google style
3. Include type annotations for all functions
4. Write tests for new functionality
5. Update documentation as needed

### Acknowledgments

This project is inspired by and builds upon the foundational work of [@contextablemark](https://github.com/contextablemark) and their [AG-UI implementation](https://github.com/contextablemark/ag-ui). We extend our gratitude for their innovative approach to agent-UI integration, which provided essential architectural insights and design patterns that shaped this middleware development.

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For issues and questions:
1. Check the documentation and examples
2. Review existing issues in the repository
3. Create a new issue with detailed information about your use case