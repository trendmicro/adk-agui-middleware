# ADK AGUI Python Middleware

A professional Python 3.13+ middleware library that bridges Google's Agent Development Kit (ADK) with AGUI protocol, providing Server-Sent Events (SSE) streaming for real-time agent interactions.

## ✨ Key Features

- **🚀 Real-time Streaming**: Server-Sent Events (SSE) for live agent responses
- **🔐 Session Management**: Comprehensive session handling with configurable backends  
- **⚙️ Context Extraction**: Flexible context configuration for multi-tenant applications
- **🛡️ Error Handling**: Robust error handling with structured logging and recovery
- **🔧 Tool Integration**: Complete tool call lifecycle management
- **📊 Event Translation**: ADK ↔ AGUI event conversion with streaming support
- **🔒 Type Safety**: Full type annotations with Pydantic models
- **🏗️ Extensible Architecture**: Abstract base classes for custom implementations

## 🚀 Quick Start

### Installation

```bash
pip install adk-agui-py-middleware
```

**Requirements:** Python 3.13+ • Google ADK ≥1.9.0 • AGUI Protocol ≥0.1.7 • FastAPI ≥0.104.0

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
    
    subgraph "Translation Layer"
        EventTranslator[Event Translator]
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
    
    Runner --> Agent
    Runner --> Services
    
    style Client fill:#e1f5fe
    style Endpoint fill:#f3e5f5
    style SSEService fill:#e8f5e8
    style EventTranslator fill:#fff3e0
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

The middleware translates between ADK and AGUI event formats:

| ADK Event | AGUI Event | Description |
|-----------|------------|-------------|
| Text Content | TextMessageStart/Content/End | Streaming text responses |
| Function Call | ToolCallStart/Args/End | Tool invocations |
| Function Response | ToolCallResult | Tool execution results |
| State Delta | StateDelta | Session state changes |
| Custom Metadata | CustomEvent | Custom event data |

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
    async def process(self, event: BaseEvent):
        # Add custom processing logic
        yield event

handler_context = HandlerContext(agui_event_handler=CustomEventHandler)
sse_service = SSEService(agent, runner_config, context_config, handler_context)
```

## 📚 Advanced Examples & Configuration

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
        
    async def translate(self, adk_event: Event) -> AsyncGenerator[TranslateEvent]:
        # Accumulate events and generate thinking summaries every 3 events
        text = self._extract_text_content(adk_event)
        if text:
            self._accumulate_event_data(adk_event.author, text, adk_event.is_final_response())
            
            if len(self.event_history) >= 3:
                async for thinking_event in self._generate_thinking_summary():
                    yield thinking_event
                self.event_history.clear()
        
        yield TranslateEvent(is_retune=True)
    
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
    async def process(self, event: Event) -> AsyncGenerator[Event | None]:
        # Add logging, filtering, or transformation
        print(f"Processing ADK event: {event.author}")
        yield event

class MyADKTimeoutHandler(BaseADKEventTimeoutHandler):
    """Handle ADK event processing timeouts."""
    async def get_timeout(self) -> int:
        return 30  # 30 seconds timeout
    
    async def process_timeout_fallback(self) -> AsyncGenerator[Event | None]:
        # Generate fallback events when timeout occurs
        yield Event(content="Timeout occurred, continuing with fallback...")

class MyAGUIEventHandler(BaseAGUIEventHandler):
    """Process AGUI events before transmission."""
    async def process(self, event: BaseEvent) -> AsyncGenerator[BaseEvent | None]:
        # Add custom processing, metrics, or filtering
        if event.type == EventType.TEXT_MESSAGE_CONTENT:
            # Log message content for analytics
            print(f"Message content: {event.delta}")
        yield event

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

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/DennySORA/adk-agui-py-middleware/issues)  
- 📦 **PyPI**: [adk-agui-py-middleware](https://pypi.org/project/adk-agui-py-middleware/)  
- 📖 **Documentation**: Complete examples and configuration guides above