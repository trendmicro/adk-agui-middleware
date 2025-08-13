"""ADK AGUI Python Middleware.

A professional Python middleware library that bridges Agent Development Kit (ADK)
agents with AGUI (Agent UI) protocol, providing Server-Sent Events (SSE) streaming
capabilities for real-time agent interactions.
"""

from .endpoint import register_agui_endpoint
from .sse_service import SSEService


__version__ = "0.1.0"
__author__ = "Denny Lee"
__email__ = "dennysora.main@gmail.com"

__all__ = [
    "register_agui_endpoint",
    "SSEService",
    "__version__",
]
