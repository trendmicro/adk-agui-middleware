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

### System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Client]
        API[API Client]
    end
    
    subgraph "FastAPI Layer"
        EP[AGUI Endpoint<br/>endpoint.py]
    end
    
    subgraph "Service Layer"
        SSE[SSE Service<br/>sse_service.py]
        BASE[Base SSE Service<br/>base_abc/sse_service.py]
    end
    
    subgraph "Handler Layer"
        UH[AGUI User Handler<br/>handler/agui_user.py]
        RH[Running Handler<br/>handler/running.py]
        SH[Session Handler<br/>handler/session.py]
        MH[User Message Handler<br/>handler/user_message.py]
    end
    
    subgraph "Manager Layer"
        SM[Session Manager<br/>manager/session.py]
    end
    
    subgraph "Google ADK Layer"
        RUNNER[ADK Runner]
        AGENT[Base Agent]
        SERVICES[ADK Services<br/>Session/Memory/Artifact/Credential]
    end
    
    subgraph "Data Models"
        CTX[Context Config<br/>data_model/context.py]
        ERR[Error Models<br/>data_model/error.py]
        SES[Session Models<br/>data_model/session.py]
    end
    
    subgraph "Tools & Utilities"
        CONV[Event Converter<br/>tools/convert.py]
        TRANS[Event Translator<br/>tools/event_translator.py]
        JSON[JSON Encoder<br/>tools/json_encoder.py]
    end
    
    subgraph "Logging & Events"
        LOG[Logging System<br/>loggers/]
        EVT[Error Events<br/>event/error_event.py]
    end
    
    WEB --> EP
    API --> EP
    EP --> SSE
    SSE -.-> BASE
    SSE --> UH
    UH --> RH
    UH --> SH
    UH --> MH
    SH --> SM
    RH --> RUNNER
    RUNNER --> AGENT
    RUNNER --> SERVICES
    SSE --> CTX
    UH --> ERR
    RH --> CONV
    RH --> TRANS
    SSE --> JSON
    UH --> LOG
    UH --> EVT
    
    classDef clientLayer fill:#e1f5fe
    classDef apiLayer fill:#f3e5f5
    classDef serviceLayer fill:#e8f5e8
    classDef handlerLayer fill:#fff3e0
    classDef managerLayer fill:#fce4ec
    classDef adkLayer fill:#f1f8e9
    classDef dataLayer fill:#e0f2f1
    classDef toolsLayer fill:#e8eaf6
    classDef loggingLayer fill:#fff8e1
    
    class WEB,API clientLayer
    class EP apiLayer
    class SSE,BASE serviceLayer
    class UH,RH,SH,MH handlerLayer
    class SM managerLayer
    class RUNNER,AGENT,SERVICES adkLayer
    class CTX,ERR,SES dataLayer
    class CONV,TRANS,JSON toolsLayer
    class LOG,EVT loggingLayer
```

### Request Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant SSEService
    participant AGUIUserHandler
    participant RunningHandler
    participant SessionHandler
    participant ADKRunner
    participant SessionManager
    
    Client->>+FastAPI: POST /agui (RunAgentInput)
    FastAPI->>+SSEService: get_runner(agui_content, request)
    
    Note over SSEService: Extract context (app_name, user_id, session_id)
    SSEService->>SSEService: extract_app_name()
    SSEService->>SSEService: extract_user_id()
    SSEService->>SSEService: extract_session_id()
    
    SSEService->>+SessionManager: Create session if needed
    SessionManager-->>-SSEService: Session ready
    
    SSEService->>+ADKRunner: Create/get runner instance
    ADKRunner-->>-SSEService: Runner instance
    
    SSEService->>+AGUIUserHandler: Create handler with components
    AGUIUserHandler->>+SessionHandler: Initialize session handler
    SessionHandler-->>-AGUIUserHandler: Ready
    AGUIUserHandler->>+RunningHandler: Initialize running handler
    RunningHandler-->>-AGUIUserHandler: Ready
    AGUIUserHandler-->>-SSEService: Handler ready
    
    SSEService-->>-FastAPI: Runner function
    FastAPI->>+SSEService: event_generator(runner)
    
    loop Event Processing
        SSEService->>+AGUIUserHandler: run()
        AGUIUserHandler->>AGUIUserHandler: call_start() -> RunStartedEvent
        AGUIUserHandler->>+SessionHandler: check_and_create_session()
        SessionHandler-->>-AGUIUserHandler: Session ready
        
        AGUIUserHandler->>+RunningHandler: run_async_with_adk()
        RunningHandler->>+ADKRunner: Execute agent
        ADKRunner-->>-RunningHandler: ADK Events
        RunningHandler->>RunningHandler: Translate ADK->AGUI events
        RunningHandler-->>-AGUIUserHandler: AGUI Events
        
        AGUIUserHandler->>+SessionHandler: add_pending_tool_call() (if tools)
        SessionHandler-->>-AGUIUserHandler: Updated
        
        AGUIUserHandler->>AGUIUserHandler: call_finished() -> RunFinishedEvent
        AGUIUserHandler-->>-SSEService: BaseEvent
        
        SSEService->>SSEService: agui_to_sse(event)
        SSEService-->>FastAPI: SSE formatted event
        FastAPI-->>Client: Server-Sent Event
    end
    
    SSEService-->>-FastAPI: Stream completed
    FastAPI-->>-Client: Connection closed
```

### Component Structure

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
- Google ADK (`google-adk>=1.9.0`)
- AGUI Protocol (`ag-ui-protocol>=0.1.7`)
- Pydantic (`pydantic>=2.11.7`)
- FastAPI (`fastapi>=0.104.0`)

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
app = FastAPI(title="My Agent API", version="1.0.0")

# Initialize your ADK agent
class MyCustomAgent(BaseAgent):
    """Custom agent implementation with specific tools and behaviors."""
    
    def __init__(self):
        super().__init__()
        # Add your custom agent configuration here
        self.tools = []  # Define your agent tools
        self.instructions = "You are a helpful assistant..."

agent = MyCustomAgent()

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

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "adk-agui-middleware"}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Complete Example with Production Configuration

```python
import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.agents import BaseAgent
from google.adk.sessions import DatabaseSessionService
from google.adk.memory import RedisMemoryService
from ag_ui.core import RunAgentInput
from adk_agui_middleware import register_agui_endpoint, SSEService
from adk_agui_middleware.data_model.context import RunnerConfig, ContextConfig
from adk_agui_middleware.config.log import setup_logging

# Configure logging
setup_logging(level="INFO", format="json")
logger = logging.getLogger(__name__)

class ProductionAgent(BaseAgent):
    """Production-ready agent with comprehensive tool suite."""
    
    def __init__(self):
        super().__init__()
        # Configure your agent with tools, instructions, etc.
        logger.info("Initializing ProductionAgent")

# Context extraction functions for multi-tenant setup
async def extract_user_id(agui_content: RunAgentInput, request: Request) -> str:
    """Extract user ID from JWT token in Authorization header."""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    # Implement your JWT validation logic here
    # For demo purposes, we'll extract from a mock token
    try:
        # decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # return decoded_token["user_id"]
        return "demo-user-123"  # Replace with actual JWT decoding
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

async def extract_app_name(agui_content: RunAgentInput, request: Request) -> str:
    """Extract app name from request headers or subdomain."""
    # Try to get from header first
    app_name = request.headers.get("x-app-name")
    if app_name:
        return app_name
    
    # Fallback to subdomain extraction
    host = request.headers.get("host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        return subdomain if subdomain != "www" else "default"
    
    return "default"

async def extract_tenant_state(agui_content: RunAgentInput, request: Request) -> dict[str, str]:
    """Extract tenant-specific initial state."""
    tenant_id = request.headers.get("x-tenant-id", "default")
    return {
        "tenant_id": tenant_id,
        "environment": "production",
        "feature_flags": "basic_features"
    }

# Create FastAPI app with production settings
app = FastAPI(
    title="ADK AGUI Production API",
    description="Production deployment of ADK AGUI middleware",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize production services
def create_production_services():
    """Initialize production-grade external services."""
    return RunnerConfig(
        use_in_memory_services=False,
        session_service=DatabaseSessionService(
            connection_string="postgresql://user:pass@localhost/agents"
        ),
        memory_service=RedisMemoryService(
            redis_url="redis://localhost:6379"
        )
    )

# Configure context with dynamic extraction
context_config = ContextConfig(
    app_name=extract_app_name,
    user_id=extract_user_id,
    session_id=lambda content, req: content.thread_id,
    extract_initial_state=extract_tenant_state
)

# Initialize agent and services
agent = ProductionAgent()
runner_config = create_production_services()

# Create SSE service
sse_service = SSEService(
    agent=agent,
    runner_config=runner_config,
    context_config=context_config
)

# Register the AGUI endpoint
register_agui_endpoint(app, sse_service, path="/api/v1/agui")

@app.get("/api/v1/health")
async def health_check():
    """Comprehensive health check endpoint."""
    return {
        "status": "healthy",
        "service": "adk-agui-middleware",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.get("/api/v1/metrics")
async def metrics():
    """Basic metrics endpoint for monitoring."""
    # Implement your metrics collection here
    return {
        "active_sessions": len(sse_service.runner_box),
        "total_runners": len(sse_service.runner_box)
    }

# Graceful shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down ADK AGUI middleware")
    await sse_service.close()
    logger.info("Shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
```

### Client-Side Usage Examples

#### JavaScript/TypeScript Client

```javascript
// Example client-side implementation
class ADKAGUIClient {
    constructor(baseUrl, authToken) {
        this.baseUrl = baseUrl;
        this.authToken = authToken;
    }

    async startAgentSession(threadId, message, tools = []) {
        const response = await fetch(`${this.baseUrl}/agui`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.authToken}`,
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify({
                thread_id: threadId,
                run_id: crypto.randomUUID(),
                message: {
                    role: 'user',
                    content: message
                },
                tool_results: tools
            })
        });

        return this.handleEventStream(response);
    }

    async *handleEventStream(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        try {
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const eventData = line.slice(6);
                        if (eventData === '[DONE]') return;
                        
                        try {
                            const event = JSON.parse(eventData);
                            yield event;
                        } catch (e) {
                            console.error('Failed to parse event:', e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }
}

// Usage example
const client = new ADKAGUIClient('https://api.example.com', 'your-jwt-token');

async function runAgent() {
    const threadId = 'thread-123';
    const message = 'Hello, can you help me with data analysis?';
    
    for await (const event of client.startAgentSession(threadId, message)) {
        switch (event.type) {
            case 'run_started':
                console.log('Agent execution started');
                break;
            case 'text_delta':
                process.stdout.write(event.text);
                break;
            case 'tool_call_end':
                console.log(`Tool called: ${event.tool_name}`);
                break;
            case 'run_finished':
                console.log('Agent execution completed');
                break;
        }
    }
}
```

#### Python Client

```python
import asyncio
import aiohttp
import json
import uuid
from typing import AsyncGenerator, Dict, Any

class ADKAGUIClient:
    """Python client for ADK AGUI middleware."""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.auth_token = auth_token
    
    async def start_agent_session(
        self, 
        thread_id: str, 
        message: str, 
        tool_results: list = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Start an agent session and yield events."""
        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'thread_id': thread_id,
            'run_id': 'run-' + str(uuid.uuid4()),
            'message': {
                'role': 'user',
                'content': message
            },
            'tool_results': tool_results or []
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/agui',
                headers=headers,
                json=payload
            ) as response:
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                        try:
                            event = json.loads(event_data)
                            yield event
                        except json.JSONDecodeError:
                            continue

# Usage example
async def main():
    client = ADKAGUIClient('https://api.example.com', 'your-jwt-token')
    
    async for event in client.start_agent_session(
        'thread-123',
        'Analyze the sales data and provide insights'
    ):
        print(f"Event: {event['type']}")
        if event['type'] == 'text_delta':
            print(event['text'], end='')
        elif event['type'] == 'tool_call_end':
            print(f"Tool called: {event['tool_name']}")

if __name__ == "__main__":
    asyncio.run(main())
```


## Advanced Usage

### Custom SSE Service

Extend the base SSE service for custom behavior:

```python
from adk_agui_middleware.base_abc.sse_service import BaseSSEService
from adk_agui_middleware.tools.convert import agui_to_sse

class CustomSSEService(BaseSSEService):
    """Custom SSE service with enhanced features."""
    
    async def get_runner(self, agui_content, request):
        """Implement custom runner creation logic."""
        # Add custom authentication, rate limiting, etc.
        return await super().get_runner(agui_content, request)
    
    async def event_generator(self, runner):
        """Custom event generation with filtering."""
        async for event in runner():
            # Apply custom event filtering or transformation
            if self.should_include_event(event):
                processed_event = self.process_event(event)
                yield agui_to_sse(processed_event)
    
    def should_include_event(self, event) -> bool:
        """Filter events based on custom logic."""
        return True  # Implement your filtering logic
    
    def process_event(self, event):
        """Transform events before encoding."""
        return event  # Apply transformations
```

### Error Handling & Monitoring

```python
from adk_agui_middleware.config.log import setup_logging
from fastapi import JSONResponse
import logging

# Configure structured logging  
setup_logging(level="INFO", format="json")
logger = logging.getLogger(__name__)

# Error events are automatically generated for:
# - Agent execution errors, encoding failures
# - Tool execution errors, session management issues

# Custom error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=exc, request_id=request.headers.get("x-request-id"))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": request.headers.get("x-request-id")}
    )
```

## API Reference

| Component | Description |
|-----------|-------------|
| `SSEService` | Main service for handling agent interactions via SSE |
| `register_agui_endpoint()` | Register AGUI endpoint on FastAPI applications |
| `ContextConfig` | Configuration for request context extraction |
| `RunnerConfig` | Configuration for ADK runner and services |
| `SessionParameter` | Session identification parameters |
| `BaseEvent` | Base class for agent events |

## Development

### Setup & Testing

```bash
# Development setup
uv sync

# Code quality
ruff format && ruff check && mypy src/

# Run tests
pytest --cov=adk_agui_middleware

# Security check
bandit -r src/
```

### Environment Configuration

```bash
# Essential environment variables
LOG_LEVEL=INFO
USE_IN_MEMORY_SERVICES=true  # false for production
SESSION_SERVICE_URL=redis://localhost:6379
```

## Production Checklist

| Category | Requirements |
|----------|-------------|
| **Services** | Use Redis/PostgreSQL instead of in-memory services |
| **Security** | JWT authentication, HTTPS, proper CORS configuration |
| **Monitoring** | Track execution times, error rates, session lifecycle |
| **Performance** | Connection pooling, session cleanup policies |

## Contributing

1. Follow existing code style (Google docstrings, type annotations)
2. Write comprehensive tests for new functionality  
3. Update documentation for API changes

### Acknowledgments

Inspired by [@contextablemark](https://github.com/contextablemark)'s [AG-UI implementation](https://github.com/contextablemark/ag-ui) for agent-UI integration patterns.

## License

Licensed under the terms specified in the [LICENSE](LICENSE) file.

## Support

- 📖 **Documentation**: Check examples and architecture diagrams above
- 🐛 **Issues**: [GitHub Issues](https://github.com/DennySORA/adk-agui-py-middleware/issues)  
- 📦 **PyPI**: [adk-agui-py-middleware](https://pypi.org/project/adk-agui-py-middleware/)