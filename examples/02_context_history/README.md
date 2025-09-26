# Context, History & State Example

## Purpose
This example demonstrates comprehensive AGUI middleware functionality, including conversation history management, session state persistence, and integration of multiple endpoints.

## Features
- Main SSE endpoint for agent interaction
- Conversation history management endpoints
- Session state management endpoints
- Custom user and session ID extraction
- Thread list formatting and customization

## Key Components

### `DemoAgent`
A placeholder agent demonstrating integration points. Replace with your actual ADK agent implementation.

### Identity Extraction Functions
- **`extract_user_id_main()`**: Extracts user ID for the main SSE endpoint
- **`extract_user_id_history()`**: Extracts user ID for history/state endpoints
- **`extract_session_id_history()`**: Extracts session ID from URL path parameters

### `format_thread_list()`
Converts session lists to client-friendly format, including:
- Thread ID
- Last update timestamp
- Optional thread title from session state

## Service Configuration

### SSE Service
Handles main chat/agent interaction endpoint.

### History Service
Manages conversation threads and message history:
- `GET /threads` - List all threads
- `DELETE /threads/{thread_id}` - Delete specific thread
- `GET /threads/{thread_id}/messages` - Get message snapshot

### State Service
Manages session state persistence and retrieval:
- `PATCH /threads/{thread_id}/state` - Update session state
- `GET /threads/{thread_id}/state` - Get state snapshot

## Running the Application
```bash
uvicorn app:app --reload
```

## API Endpoints
- `POST /agui` - Main SSE endpoint for real-time interaction
- `GET /threads` - List all conversation threads
- `DELETE /threads/{thread_id}` - Delete a conversation thread
- `GET /threads/{thread_id}/messages` - Retrieve message history
- `PATCH /threads/{thread_id}/state` - Update session state
- `GET /threads/{thread_id}/state` - Retrieve session state

## Use Cases
- Applications requiring conversation history management
- Multi-user chat systems
- Complex interactions requiring state persistence
- Building conversational AI with memory

## Key Learning Points
- How to integrate multiple AGUI services
- Session and user ID extraction patterns
- State management across conversations
- Thread/conversation lifecycle management