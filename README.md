# ADK AGUI Python Middleware

A professional Python 3.10+ middleware library that bridges Google's Agent Development Kit (ADK) with AGUI protocol, providing Server-Sent Events (SSE) streaming for real-time agent interactions.

## ✨ Key Features

- **🚀 Real-time Streaming**: Server-Sent Events (SSE) for live agent responses
- **🔐 Session Management**: Comprehensive session handling with configurable backends  
- **⚙️ Context Extraction**: Flexible context configuration for multi-tenant applications
- **🛡️ Error Handling**: Robust error handling with structured logging and recovery
- **🔧 Tool Integration**: Complete tool call lifecycle management with HITL support
- **📊 Event Translation**: ADK ↔ AGUI event conversion with streaming support
- **🔒 Type Safety**: Full type annotations with Pydantic models
- **🏗️ Extensible Architecture**: Abstract base classes for custom implementations


## 🚀 Quick Start

### Installation

```bash
pip install adk-agui-middleware
```

**Requirements:** Python 3.10+ • Google ADK ≥1.9.0 • AGUI Protocol ≥0.1.7 • FastAPI ≥0.104.0

### Basic Implementation

```python
from fastapi import FastAPI, Request
from google.adk.agents import BaseAgent
from ag_ui.core import RunAgentInput
from adk_agui_middleware import register_agui_endpoint, SSEService
from adk_agui_middleware.data_model.context import RunnerConfig, ConfigContext

app = FastAPI(title="Agent API", version="1.0.0")

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.instructions = "You are a helpful AI assistant."

# Context extractors for multi-tenant support
async def extract_user_id(agui_content: RunAgentInput, request: Request) -> str:
    return request.headers.get("X-User-ID", "default-user")

async def extract_app_name(agui_content: RunAgentInput, request: Request) -> str:
    return request.headers.get("X-App-Name", "default-app")

# Initialize and register
agent = MyAgent()
context_config = ConfigContext(app_name=extract_app_name, user_id=extract_user_id)
runner_config = RunnerConfig(use_in_memory_services=True)
sse_service = SSEService(agent, runner_config, context_config)
register_agui_endpoint(app, sse_service, path="/agui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🏗️ Architecture Overview

The middleware is organized into distinct layers with clear separation of concerns, providing a comprehensive solution for agent-human interactions through sophisticated event processing and state management.

### 📁 Module Structure

The codebase follows a modular architecture with well-defined responsibilities:

#### Core Service Layer (`adk_agui_middleware/`)
- **`endpoint.py`**: FastAPI endpoint registration for agent interactions
- **`sse_service.py`**: Main SSE service implementation with runner management

#### Abstract Base Classes (`base_abc/`)
- **`handler.py`**: Abstract base classes for event and state handlers
- **`sse_service.py`**: Base SSE service interface definition

#### Configuration Management (`config/`)
- **`log.py`**: Logging configuration with environment variable support

#### Data Models (`data_model/`)
- **`context.py`**: Configuration models for context extraction and runner setup
- **`error.py`**: HTTP error response models
- **`event.py`**: Event translation data models for ADK ↔ AGUI conversion
- **`log.py`**: Structured log message model for comprehensive logging
- **`session.py`**: Session parameter model for session identification

#### Event Processing (`event/`)
- **`error_event.py`**: Error event classes for encoding and execution failures
- **`event_translator.py`**: Core event translation service (ADK ↔ AGUI formats)

#### Handler Layer (`handler/`)
- **`agui_user.py`**: Main AGUI user interaction and workflow orchestration
- **`running.py`**: Agent execution and event translation management
- **`session.py`**: Session operations and tool call lifecycle management
- **`user_message.py`**: User message and tool result processing

#### Logging System (`loggers/`)
- **`exception.py`**: HTTP exception handling and error response utilities
- **`logger.py`**: JSON logging formatter and logger configuration
- **`record_log.py`**: Structured logging functions for application events
- **`record_request_log.py`**: Request logging utilities for HTTP tracking

#### Session Management (`manager/`)
- **`session.py`**: ADK session operations and state management

#### Design Patterns (`pattern/`)
- **`singleton.py`**: Singleton design pattern implementation

#### Utility Tools (`tools/`)
- **`convert.py`**: Event conversion utilities for SSE format
- **`function_name.py`**: Function name extraction for debugging
- **`json_encoder.py`**: Custom JSON encoder for Pydantic models
- **`shutdown.py`**: Graceful shutdown handler for application cleanup

#### Translation Utilities (`utils/translate/`)
- **`common.py`**: Common translation utilities for retune events
- **`thinking.py`**: Thinking event utilities for AI reasoning display

### System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Client[AGUI Client]
        Browser[Web Browser]
    end
    
    subgraph "Middleware Layer"
        Endpoint[FastAPI Endpoint]
        SSEService[SSE Service]
        EventGen[Event Generator]
    end
    
    subgraph "Core Components"
        AGUIHandler[AGUI User Handler]
        RunningHandler[Running Handler]
        SessionHandler[Session Handler]
        UserMsgHandler[User Message Handler]
    end
    
    subgraph "Event Layer"
        EventTranslator[Event Translator]
        ErrorEvent[Error Events]
        Utils[Utils/Translate]
    end
    
    subgraph "Translation Layer"
        ADKEvents[ADK Events]
        AGUIEvents[AGUI Events]
    end
    
    subgraph "ADK Layer"
        Runner[ADK Runner]
        Agent[Base Agent]
        Services[ADK Services]
    end
    
    Client --> Endpoint
    Browser --> Endpoint
    Endpoint --> SSEService
    SSEService --> EventGen
    EventGen --> AGUIHandler
    
    AGUIHandler --> RunningHandler
    AGUIHandler --> SessionHandler
    AGUIHandler --> UserMsgHandler
    
    RunningHandler --> EventTranslator
    RunningHandler --> Runner
    EventTranslator --> ADKEvents
    EventTranslator --> AGUIEvents
    EventTranslator --> ErrorEvent
    Utils --> AGUIEvents
    
    Runner --> Agent
    Runner --> Services
    
    style Client fill:#e1f5fe
    style Endpoint fill:#f3e5f5
    style SSEService fill:#e8f5e8
    style EventTranslator fill:#fff3e0
    style ErrorEvent fill:#ffebee
    style Runner fill:#fce4ec
```

### Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant E as FastAPI Endpoint
    participant S as SSE Service
    participant H as AGUI Handler
    participant R as Running Handler
    participant T as Event Translator
    participant A as ADK Runner
    
    C->>E: POST /agui (RunAgentInput)
    E->>S: agui_endpoint()
    S->>S: extract_context()
    S->>H: create AGUIUserHandler
    S->>E: EventSourceResponse
    
    loop Event Generation
        H->>R: run()
        R->>A: run_async()
        A-->>R: ADK Event
        R->>T: translate()
        T-->>R: AGUI Event
        R-->>H: AGUI Event
        H-->>S: AGUI Event
        S->>S: encode_event()
        S-->>E: SSE Event
        E-->>C: Server-Sent Event
    end
    
    E-->>C: Connection Close
```

## 💡 Core Concepts

### 🔧 Utility Components

The middleware includes a dedicated `utils` module providing specialized translation utilities for common event handling patterns:

#### Translation Utilities (`utils/translate/`)

The translation utilities help with generating specific event types and managing event flows:

```python
from adk_agui_middleware.utils.translate.common import translate_retune_event
from adk_agui_middleware.utils.translate.thinking import ThinkingEventUtil

# Simple retune event creation
retune_event = translate_retune_event()

# Advanced thinking event generation
thinking_util = ThinkingEventUtil()

# Generate thinking events for streaming text
async def generate_thinking_stream(text_stream):
    thinking_util = ThinkingEventUtil()
    async for event in thinking_util.think_event_generator(text_stream):
        yield event

# Individual thinking events
start_event = thinking_util.thinking_start_event()
content_event = thinking_util.thinking_content_event("AI is thinking...")
end_event = thinking_util.thinking_end_event()
```

**Key Utility Features:**
- **🔄 Retune Events**: Simple creation of agent retune events
- **🧠 Thinking Events**: Complete thinking message lifecycle management
- **📊 Event Generators**: Async generators for streaming thinking content
- **⚡ Type Safety**: Fully typed utilities with comprehensive docstrings

### 🤝 Human-in-the-Loop (HITL) Workflows

The middleware provides sophisticated HITL support through its `pending_tool_call` system, enabling agents to pause execution and wait for human intervention when needed.

#### HITL Flow Overview

```mermaid
sequenceDiagram
    participant A as Agent
    participant M as Middleware
    participant S as Session Store
    participant H as Human/UI
    
    Note over A,H: Agent encounters tool requiring human input
    A->>M: Tool Call (requires human input)
    M->>S: Add to pending_tool_calls
    M->>A: Pause execution
    
    Note over A,H: Human intervention phase
    S-->>H: Query pending_tool_calls
    H->>H: Review & provide input
    H->>M: Submit tool result
    M->>S: Remove from pending_tool_calls
    
    Note over A,H: Resume execution
    M->>A: Resume with tool result
    A->>M: Continue processing
```
### Session-Based State Management

**🔑 Key Concept**: The middleware creates **one handler instance per session** to maintain conversation state throughout the interaction.

```python
# ✅ Pass handler CLASSES, not instances
handler_context = HandlerContext(
    translate_handler=MyTranslateHandler,  # Class
    agui_event_handler=MyEventHandler      # Class
)
# ❌ NOT: translate_handler=MyTranslateHandler()  # Instance
```

**Why this design matters:**
- **Per-Session Isolation**: Each conversation gets its own handler instance
- **State Persistence**: Handlers accumulate data across multiple events
- **Memory Safety**: No state leakage between users/sessions
- **Concurrency Safe**: Multiple sessions run simultaneously without interference

### Event Translation Pipeline

The middleware translates between ADK and AGUI event formats using the `EventTranslator` class (located in `adk_agui_middleware.event.event_translator`):

| ADK Event | AGUI Event | Description |
|-----------|------------|-------------|
| Text Content | TextMessageStart/Content/End | Streaming text responses |
| Function Call | ToolCallStart/Args/End | Tool invocations |
| Function Response | ToolCallResult | Tool execution results |
| State Delta | StateDelta | Session state changes |
| Custom Metadata | CustomEvent | Custom event data |
| Pending Tool Call | Session State | HITL workflow coordination |

### Production Configuration

```python
from google.adk.sessions import DatabaseSessionService
from google.adk.memory import DatabaseMemoryService

# Production services configuration
runner_config = RunnerConfig(
    use_in_memory_services=False,
    session_service=DatabaseSessionService(connection_string="..."),
    memory_service=DatabaseMemoryService(connection_string="..."),
)

# Custom event handlers
class CustomEventHandler(BaseAGUIEventHandler):
    @staticmethod
    async def _handle_event(event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        # Add custom processing logic
        yield event
    
    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        return self._handle_event(event)

handler_context = HandlerContext(agui_event_handler=CustomEventHandler)
sse_service = SSEService(agent, runner_config, context_config, handler_context)
```

## ⚠️ Critical Implementation Notes

### 🔴 Base Handler Pattern - IMPORTANT

When implementing custom handlers that extend the Base handler classes, you **MUST** follow the specific async pattern used by the middleware:

```python
# ❌ WRONG - This will cause runtime errors
class FilterADKEvent(BaseADKEventHandler):
    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        yield event  # This won't work with the middleware's calling pattern

class MyTranslateHandler(BaseTranslateHandler):
    async def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        yield TranslateEvent(is_retune=True)  # This will also fail

# ✅ CORRECT - Return the async generator, don't yield directly
class FilterADKEvent(BaseADKEventHandler):
    @staticmethod
    async def filter(event: Event) -> AsyncGenerator[Event | None]:
        has_text = (
            event.content and
            event.content.parts and
            event.content.parts[0].text
        )
        if has_text:
            yield event
        elif event.actions.state_delta:
            event.actions.state_delta = {
                k: v for k, v in event.actions.state_delta.items()
                if k.startswith("companion")
            }
            yield event
        else:
            yield None

    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        return self.filter(event)  # Return the generator, don't yield

class MyTranslateHandler(BaseTranslateHandler):
    @staticmethod
    async def _do_translate(adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        yield TranslateEvent(is_retune=True)  # Yield in internal method
    
    async def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        return self._do_translate(adk_event)  # Return the generator
```

**Why this matters:**
- The middleware uses `async for i in await handler.process()` internally
- The extra `await` requires that `process()` returns an async generator, not yields directly
- Violating this pattern will cause `TypeError: 'async_generator' object is not an async iterator`

**The Pattern:**
1. Create a separate static/async method that yields events (`filter()`, `_translate_internal()`)
2. Have the interface method return that method's generator (`return self.filter(event)`)
3. Never yield directly in interface methods (`process()`, `translate()`, `process_timeout_fallback()`)

## 📚 Advanced Examples & Configuration

<details>
<summary><strong>🎯 Event Filtering & Processing (Click to expand)</strong></summary>

This example shows how to implement sophisticated event filtering to control which ADK events get processed and translated:

```python
from adk_agui_middleware.base_abc.handler import BaseADKEventHandler
from adk_agui_middleware.data_model.context import HandlerContext
from google.adk.events import Event

class SmartEventFilter(BaseADKEventHandler):
    """Intelligent event filter for production environments."""
    
    @staticmethod
    async def filter(event: Event) -> AsyncGenerator[Event | None]:
        # Process text events
        if event.content and event.content.parts and event.content.parts[0].text:
            yield event
            return
            
        # Skip function responses
        if event.get_function_responses():
            yield None
            return
            
        # Filter state deltas (only companion data)
        if event.actions and event.actions.state_delta:
            companion_data = {
                k: v for k, v in event.actions.state_delta.items()
                if k.startswith("companion")
            }
            if companion_data:
                event.actions.state_delta = companion_data
                yield event
            else:
                yield None
        else:
            yield None

    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        return self.filter(event)

# Apply the filter
context = HandlerContext(adk_event_handler=SmartEventFilter)
sse_service = SSEService(agent, runner_config, config_context, context)
```

**Use Cases:**
- **Performance**: Reduce processing overhead by filtering unnecessary events
- **Security**: Remove sensitive data from state deltas  
- **Customization**: Focus on specific event types for your application
- **Analytics**: Filter events for targeted metrics collection

</details>

<details>
<summary><strong>🤝 Complete HITL (Human-in-the-Loop) Implementation (Click to expand)</strong></summary>

```python
from fastapi import FastAPI, BackgroundTasks
from adk_agui_middleware import SSEService, register_agui_endpoint
from adk_agui_middleware.handler.session import SessionHandler
from adk_agui_middleware.data_model.session import SessionParameter

app = FastAPI(title="HITL Agent API")

# HITL Monitoring System
class HITLMonitor:
    """Monitors and manages HITL workflows across all sessions."""
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
    
    async def check_pending_actions(self, session_id: str) -> dict:
        """Check if a session has pending actions requiring human attention."""
        session_param = SessionParameter(
            app_name="hitl-demo", user_id="demo-user", session_id=session_id
        )
        session_handler = SessionHandler(self.session_manager, session_param)
        
        pending_calls = await session_handler.get_pending_tool_calls()
        if pending_calls:
            return {
                "has_pending": True,
                "pending_tool_calls": pending_calls,
                "requires_human_attention": True
            }
        return {"has_pending": False, "status": "agent_active"}

# HITL API Endpoints
@app.get("/sessions/{session_id}/pending")
async def get_pending_actions(session_id: str):
    """Get pending actions requiring human approval."""
    return await hitl_monitor.check_pending_actions(session_id)

@app.post("/sessions/{session_id}/approve/{tool_call_id}")
async def approve_pending_action(session_id: str, tool_call_id: str, approval: dict):
    """Approve or reject a pending action."""
    # Process human approval and resume agent execution
    return {"status": "approved", "resuming_execution": True}
```

**HITL Benefits:**
- **🛡️ Safety**: Human oversight for critical operations
- **🎯 Accuracy**: Human validation improves decision quality  
- **📋 Compliance**: Audit trails for regulated environments
- **🔄 Seamless**: Agent execution resumes automatically after approval

</details>

<details>
<summary><strong>🧠 AI-Powered Event Summarization (Click to expand)</strong></summary>

Here's a real-world example demonstrating stateful handler design with AI thinking capabilities:

```python
import json
import time
import uuid
from typing import Any, AsyncGenerator

from adk_agui_middleware.base_abc.handler import BaseTranslateHandler, BaseAGUIStateSnapshotHandler
from adk_agui_middleware.data_model.context import RunnerConfig, ConfigContext, HandlerContext
from adk_agui_middleware.data_model.event import TranslateEvent
from ag_ui.core import RunAgentInput, EventType, ThinkingTextMessageStartEvent

class AIThinkingTranslateHandler(BaseTranslateHandler):
    """Accumulates events and generates AI thinking summaries."""
    
    def __init__(self):
        self.event_partial: dict[str, str] = {}  # Partial event accumulation
        self.event_history: list[str] = []       # Complete event history
        
    async def _translate_internal(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        # Accumulate events and generate thinking summaries every 3 events
        text = self._extract_text_content(adk_event)
        if text:
            self._accumulate_event_data(adk_event.author, text, adk_event.is_final_response())
            
            if len(self.event_history) >= 3:
                async for thinking_event in self._generate_thinking_summary():
                    yield thinking_event
                self.event_history.clear()
        
        yield TranslateEvent(is_retune=True)
    
    async def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        return self._translate_internal(adk_event)
    
    # ... (implementation details)

class ProductionAGUIEndpoint:
    def __init__(self):
        self.sse_service = SSEService(
            agent=self._create_agent(),
            runner_config=self._create_runner_config(),
            config_context=self._create_context_config(),
            handler_context=HandlerContext(
                translate_handler=AIThinkingTranslateHandler,  # ✅ Pass class
                agui_state_snapshot_handler=CustomStateSnapshotHandler
            )
        )
```

**Key Benefits:**
- **🔄 Session Continuity**: Handler instances persist throughout conversations
- **🛡️ Memory Isolation**: No state leakage between users/sessions  
- **📊 Stateful Processing**: Accumulate partial events, maintain conversation history
- **🎯 Real-World Use Cases**: Conversation summarization, progressive data collection, adaptive behavior

</details>

<details>
<summary><strong>⚙️ Configuration Deep Dive (Click to expand)</strong></summary>

The middleware provides three main configuration models that control different aspects of the system behavior:

### Event Filtering and Processing

Here's a practical example of filtering ADK events to control what gets processed and translated:

```python
from adk_agui_middleware.base_abc.handler import BaseADKEventHandler
from google.adk.events import Event
from typing import AsyncGenerator

class FilterADKEvent(BaseADKEventHandler):
    """Advanced event filter that selectively processes different types of ADK events.
    
    This filter demonstrates sophisticated event processing logic:
    - Only processes events with text content
    - Filters out function responses (tool results)
    - Selectively processes state deltas (only companion-related changes)
    - Skips all other event types
    """

    @staticmethod
    async def filter(event: Event) -> AsyncGenerator[Event | None]:
        # Check if event has meaningful text content
        has_text = (
            event.content and
            event.content.parts and
            event.content.parts[0].text
        )
        
        if has_text:
            # Process events with text content
            yield event
        elif event.get_function_responses():
            # Skip function responses (tool execution results)
            yield None
        elif event.actions and event.actions.state_delta:
            # Filter state deltas to only include companion-related changes
            filtered_delta = {
                k: v for k, v in event.actions.state_delta.items()
                if k.startswith("companion")
            }
            
            if filtered_delta:
                # Create modified event with filtered state delta
                event.actions.state_delta = filtered_delta
                yield event
            else:
                # No companion-related changes, skip this event
                yield None
        else:
            # Skip all other event types
            yield None

    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        return self.filter(event)

# Usage in production
handler_context = HandlerContext(
    adk_event_handler=FilterADKEvent,  # Apply filtering before translation
)
```

**Event Filtering Benefits:**
- **🎯 Selective Processing**: Only process relevant events, reduce noise
- **⚡ Performance**: Skip unnecessary event processing and translation
- **🔧 Customization**: Tailor event flow to specific application needs
- **🛡️ Security**: Filter out sensitive data before processing
- **📊 Analytics**: Focus on specific event types for metrics

### HandlerContext: Event Processing Pipeline

`HandlerContext` allows you to inject custom handlers at different stages of the event processing pipeline:

```python
from adk_agui_middleware.data_model.context import HandlerContext
from adk_agui_middleware.base_abc.handler import (
    BaseADKEventHandler,
    BaseADKEventTimeoutHandler,
    BaseAGUIEventHandler,
    BaseAGUIStateSnapshotHandler,
    BaseTranslateHandler
)

class MyADKEventHandler(BaseADKEventHandler):
    """Process ADK events before translation."""
    @staticmethod
    async def _process_event(event: Event) -> AsyncGenerator[Event | None]:
        # Add logging, filtering, or transformation
        print(f"Processing ADK event: {event.author}")
        yield event
    
    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        return self._process_event(event)

class MyADKTimeoutHandler(BaseADKEventTimeoutHandler):
    """Handle ADK event processing timeouts."""
    async def get_timeout(self) -> int:
        return 30  # 30 seconds timeout
    
    @staticmethod
    async def _generate_fallback() -> AsyncGenerator[Event | None]:
        # Generate fallback events when timeout occurs
        yield Event(content="Timeout occurred, continuing with fallback...")
    
    async def process_timeout_fallback(self) -> AsyncGenerator[Event | None]:
        return self._generate_fallback()

class MyAGUIEventHandler(BaseAGUIEventHandler):
    """Process AGUI events before transmission."""
    @staticmethod
    async def _process_agui_event(event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        # Add custom processing, metrics, or filtering
        if event.type == EventType.TEXT_MESSAGE_CONTENT:
            # Log message content for analytics
            print(f"Message content: {event.delta}")
        yield event
    
    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        return self._process_agui_event(event)

# Configure the handler pipeline
handler_context = HandlerContext(
    adk_event_handler=MyADKEventHandler,           # Process ADK events
    adk_event_timeout_handler=MyADKTimeoutHandler, # Handle timeouts
    agui_event_handler=MyAGUIEventHandler,         # Process AGUI events
    agui_state_snapshot_handler=CustomStateSnapshotHandler,  # Clean final state
    translate_handler=AIThinkingTranslateHandler   # Custom event translation
)
```

**Handler Execution Order:**
1. `adk_event_handler` → Processes raw ADK events
2. `translate_handler` → Converts ADK to AGUI events  
3. `agui_event_handler` → Processes AGUI events before transmission
4. `agui_state_snapshot_handler` → Cleans final session state

### ConfigContext: Request Context Extraction

`ConfigContext` defines how to extract tenant/user information from incoming requests:

```python
from adk_agui_middleware.data_model.context import ConfigContext

# Static configuration (simple scenarios)
static_config = ConfigContext(
    app_name="my-app",
    user_id="default-user"
)

# Dynamic extraction (production scenarios)
async def extract_app_from_subdomain(agui_content: RunAgentInput, request: Request) -> str:
    """Extract app name from subdomain (e.g., tenant1.myservice.com)."""
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if "." in host else "default"
    return f"app-{subdomain}"

async def extract_user_from_jwt(agui_content: RunAgentInput, request: Request) -> str:
    """Extract user ID from JWT token."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Decode JWT and extract user_id
        # decoded = jwt.decode(token, secret, algorithms=["HS256"])
        # return decoded["user_id"]
        return "user-from-jwt"
    return "anonymous"

async def extract_session_from_thread(agui_content: RunAgentInput, request: Request) -> str:
    """Use AGUI thread_id as session identifier."""
    return agui_content.thread_id

async def extract_initial_context(agui_content: RunAgentInput, request: Request) -> dict[str, Any]:
    """Setup initial session state from request."""
    return {
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent", ""),
        "conversation_started_at": int(time.time() * 1000),
        "features_enabled": ["thinking", "tools", "memory"]
    }

# Production configuration
production_config = ConfigContext(
    app_name=extract_app_from_subdomain,      # Multi-tenant app isolation
    user_id=extract_user_from_jwt,            # JWT-based authentication
    session_id=extract_session_from_thread,   # Thread-based sessions
    extract_initial_state=extract_initial_context  # Rich context setup
)
```

**Key Configuration Patterns:**

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Static Values** | Single-tenant, development | `app_name="my-app"` |
| **Header Extraction** | API keys, tenant IDs | `request.headers.get("X-Tenant-ID")` |
| **JWT Decoding** | User authentication | `jwt.decode(token)["user_id"]` |
| **Path/Subdomain** | Multi-tenant routing | `request.url.path.split("/")[1]` |
| **AGUI Content** | Thread-based sessions | `agui_content.thread_id` |

### RunnerConfig: Service Configuration

`RunnerConfig` manages the ADK services that power agent execution:

```python
from adk_agui_middleware.data_model.context import RunnerConfig
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode

# Development configuration (in-memory services)
dev_config = RunnerConfig(
    use_in_memory_services=True,  # Automatically creates in-memory services
    run_config=RunConfig(
        streaming_mode=StreamingMode.SSE,
        max_response_tokens=2000,
        temperature=0.7
    )
)

# Production configuration (external services)
from google.adk.sessions import DatabaseSessionService
from google.adk.memory import DatabaseMemoryService
from google.adk.artifacts import S3ArtifactService
from google.adk.auth.credential_service import VaultCredentialService

prod_config = RunnerConfig(
    use_in_memory_services=False,  # Use external services
    
    # Session persistence
    session_service=DatabaseSessionService(
        connection_string="postgresql://user:pass@host:5432/sessions"
    ),
    
    # Agent memory
    memory_service=DatabaseMemoryService(
        connection_string="postgresql://user:pass@host:5432/memory"
    ),
    
    # File/artifact storage
    artifact_service=S3ArtifactService(
        bucket_name="agent-artifacts",
        region="us-west-2"
    ),
    
    # Credentials management
    credential_service=VaultCredentialService(
        vault_url="https://vault.company.com",
        vault_token=os.getenv("VAULT_TOKEN")
    ),
    
    # Agent execution configuration
    run_config=RunConfig(
        streaming_mode=StreamingMode.SSE,
        max_response_tokens=4000,
        temperature=0.3,
        top_p=0.9
    )
)
```

**Service Fallback Behavior:**
```python
# When use_in_memory_services=True (default)
config = RunnerConfig()
# ✅ Automatically creates:
# - InMemorySessionService
# - InMemoryMemoryService  
# - InMemoryArtifactService
# - InMemoryCredentialService

# When use_in_memory_services=False
config = RunnerConfig(
    use_in_memory_services=False,
    session_service=None  # ❌ Will raise ValueError at runtime
)
```

**Production Service Integration:**
```python
# Custom service factory
def create_production_runner_config(environment: str) -> RunnerConfig:
    """Create environment-specific runner configuration."""
    
    if environment == "development":
        return RunnerConfig(use_in_memory_services=True)
    
    elif environment == "staging":
        return RunnerConfig(
            use_in_memory_services=False,
            session_service=DatabaseSessionService(
                connection_string=os.getenv("STAGING_DB_URL")
            ),
            memory_service=InMemoryMemoryService(),  # Still use in-memory for staging
        )
    
    elif environment == "production":
        return RunnerConfig(
            use_in_memory_services=False,
            session_service=DatabaseSessionService(
                connection_string=os.getenv("PROD_SESSION_DB_URL"),
                pool_size=20,
                max_overflow=30
            ),
            memory_service=DatabaseMemoryService(
                connection_string=os.getenv("PROD_MEMORY_DB_URL"),
                cache_ttl=3600
            ),
            artifact_service=S3ArtifactService(
                bucket_name=os.getenv("PROD_ARTIFACTS_BUCKET"),
                encryption="AES256"
            ),
            credential_service=VaultCredentialService(
                vault_url=os.getenv("VAULT_URL"),
                vault_token=os.getenv("VAULT_TOKEN")
            )
        )
    
    raise ValueError(f"Unknown environment: {environment}")

# Usage
runner_config = create_production_runner_config(os.getenv("ENV", "development"))
```

</details>

## 📄 License

Licensed under the MIT License. See [LICENSE](LICENSE) file for details.
