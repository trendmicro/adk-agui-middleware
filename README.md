# ADK AGUI Python Middleware

A professional Python 3.13+ middleware library that bridges Google's Agent Development Kit (ADK) with AGUI protocol, providing Server-Sent Events (SSE) streaming for real-time agent interactions.

## Overview

This middleware enables seamless integration between Google ADK agents and AGUI-compatible frontends, supporting real-time streaming responses with comprehensive session management, event translation, and error handling in a production-ready framework.

## Features

- **🚀 Real-time Streaming**: Server-Sent Events (SSE) for live agent responses
- **🔐 Session Management**: Comprehensive session handling with configurable backends  
- **⚙️ Context Extraction**: Flexible context configuration for multi-tenant applications
- **🛡️ Error Handling**: Robust error handling with structured logging and recovery
- **🔧 Tool Integration**: Complete tool call lifecycle management
- **📊 Event Translation**: ADK ↔ AGUI event conversion with streaming support
- **🔒 Type Safety**: Full type annotations with Pydantic models
- **🏗️ Extensible Architecture**: Abstract base classes for custom implementations


## Installation

```bash
pip install adk-agui-py-middleware
```

**Requirements:**
- Python 3.13+
- Google ADK (`google-adk>=1.9.0`)
- AGUI Protocol (`ag-ui-protocol>=0.1.7`) 
- Pydantic (`pydantic>=2.11.7`)
- FastAPI (`fastapi>=0.104.0`)

## Quick Start

### Basic Implementation

```python
from fastapi import FastAPI
from google.adk.agents import BaseAgent
from adk_agui_middleware import register_agui_endpoint, SSEService
from adk_agui_middleware.data_model.context import RunnerConfig, ConfigContext

# Create FastAPI application
app = FastAPI(title="Agent API", version="1.0.0")

# Define your agent implementation
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.instructions = "You are a helpful AI assistant."

# Initialize components
agent = MyAgent()
context_config = ConfigContext(
    app_name="my-agent-app",
    user_id="default-user"  # In production, extract from auth
)
runner_config = RunnerConfig(use_in_memory_services=True)

# Create and register SSE service
sse_service = SSEService(agent, runner_config, context_config)
register_agui_endpoint(app, sse_service, path="/agui")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```


## License

Licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## Support

- 📖 **Documentation**: Architecture diagrams and examples above
- 🐛 **Issues**: [GitHub Issues](https://github.com/DennySORA/adk-agui-py-middleware/issues)
- 📦 **PyPI**: [adk-agui-py-middleware](https://pypi.org/project/adk-agui-py-middleware/)