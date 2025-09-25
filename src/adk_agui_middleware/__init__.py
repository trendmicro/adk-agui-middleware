# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
"""ADK AGUI Python Middleware.

A professional Python middleware library that bridges Agent Development Kit (ADK)
agents with AGUI (Agent UI) protocol, providing Server-Sent Events (SSE) streaming
capabilities for real-time agent interactions.
"""

from .endpoint import register_agui_endpoint
from .service.sse_service import SSEService


__author__ = "Denny Lee"
__email__ = "denny_lee@trendmicro.com"
__version__ = "1.1.0"

__all__ = [
    "SSEService",
    "register_agui_endpoint",
]
