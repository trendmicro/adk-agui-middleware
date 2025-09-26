# Minimal SSE Example

## Purpose
This example demonstrates the simplest practical integration of the AGUI middleware, creating a basic Server-Sent Events (SSE) endpoint to interact with an ADK LLM agent.

## Features
- Creates a minimal FastAPI application
- Uses google.adk's LlmAgent as the underlying agent
- Streams real-time responses via SSE
- Extracts user ID from HTTP headers
- Uses in-memory services for development and testing

## Key Components

### `build_llm_agent()`
Creates and configures a google.adk LLM agent with compatibility support for multiple ADK versions.

### `extract_user_id()`
Extracts user identifier from the `X-User-Id` HTTP header, defaults to "guest".

### SSE Service Configuration
- **RunnerConfig**: Uses default in-memory services
- **ConfigContext**: Configures request context extraction
- **SSEService**: Orchestrates the entire request-response pipeline

## Running the Application
```bash
uvicorn app:app --reload
```

## Endpoints
- `POST /agui` - Main SSE endpoint that accepts user input and streams responses

## Environment Variables
- `ADK_MODEL_NAME` (optional): Specifies the LLM model name, defaults to `gemini-1.5-flash`

## Use Cases
- Rapid prototyping
- Understanding basic AGUI integration patterns
- Local development and testing

## Key Learning Points
- Minimal setup required for AGUI integration
- How to configure an LLM agent with version compatibility
- Basic SSE endpoint registration
- Request context extraction patterns