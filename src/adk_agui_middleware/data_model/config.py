# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import Request
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.artifacts import BaseArtifactService, InMemoryArtifactService
from google.adk.auth.credential_service.base_credential_service import (
    BaseCredentialService,
)
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory import BaseMemoryService, InMemoryMemoryService
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session
from pydantic import BaseModel, ConfigDict, Field

from ..base_abc.handler import (
    BaseADKEventHandler,
    BaseAGUIEventHandler,
    BaseTranslateHandler,
)


T = TypeVar("T", BaseArtifactService, BaseMemoryService, BaseCredentialService)


class PathConfig(BaseModel):
    """Configuration for AGUI endpoint paths.

    Defines the URL paths for different AGUI endpoints including
    main agent interaction, conversation listing, and history retrieval.
    Enables customizable URL structure for different deployment scenarios.

    Attributes:
        agui_main_path: Path for the main agent interaction endpoint (default: empty string)
        agui_thread_list_path: Path for listing available conversation threads
        agui_state_snapshot_path: Path template for retrieving session state snapshots
        agui_message_snapshot_path: Path template for retrieving conversation history
    """

    agui_main_path: str = ""
    agui_thread_list_path: str = "/thread/list"
    agui_thread_delete_path: str = "/thread/{thread_id}"
    agui_patch_state_path: str = "/state/{thread_id}"
    agui_state_snapshot_path: str = "/state_snapshot/{thread_id}"
    agui_message_snapshot_path: str = "/message_snapshot/{thread_id}"


class RunnerConfig(BaseModel):
    """Configuration for ADK runner setup and services.

    Manages the configuration of various services required for agent execution
    including session, artifact, memory, and credential services. Provides
    flexible service configuration with automatic in-memory fallbacks for
    development and testing environments.

    Attributes:
        use_in_memory_services: Whether to automatically create in-memory services when needed
        run_config: ADK run configuration for agent execution behavior
        session_service: Session service implementation for conversation persistence
        artifact_service: Optional artifact service for file and data management
        memory_service: Optional memory service for agent memory management
        credential_service: Optional credential service for authentication
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    use_in_memory_services: bool = True
    run_config: RunConfig = RunConfig(streaming_mode=StreamingMode.SSE)
    session_service: BaseSessionService = Field(default_factory=InMemorySessionService)
    artifact_service: BaseArtifactService | None = None
    memory_service: BaseMemoryService | None = None
    credential_service: BaseCredentialService | None = None

    def _get_or_create_service(self, service_attr: str, service_class: type[T]) -> T:
        """Get existing service or create in-memory service if enabled.

        Implements lazy service initialization pattern, creating in-memory service
        instances only when needed and only if in-memory services are enabled.
        This provides flexible service configuration for different environments.

        Args:
            :param service_attr: Name of the service attribute to check and potentially set
            :param service_class: Class to instantiate if service is None and in-memory is enabled

        Returns:
            Service instance (existing or newly created)

        Raises:
            ValueError: If service is None and in-memory services are disabled
        """
        service = getattr(self, service_attr)
        if service is None:
            if self.use_in_memory_services:
                service = service_class()
                setattr(self, service_attr, service)
            else:
                raise ValueError(
                    f"{service_attr.replace('_', ' ').title()} is not set."
                )
        return service  # type: ignore[no-any-return]

    def get_artifact_service(self) -> BaseArtifactService:
        """Get or create artifact service.

        Retrieves the configured artifact service or creates an in-memory
        implementation if none is configured and in-memory services are enabled.

        Returns:
            Configured artifact service instance for file and data management
        """
        return self._get_or_create_service("artifact_service", InMemoryArtifactService)

    def get_memory_service(self) -> BaseMemoryService:
        """Get or create memory service.

        Retrieves the configured memory service or creates an in-memory
        implementation if none is configured and in-memory services are enabled.

        Returns:
            Configured memory service instance for agent memory management
        """
        return self._get_or_create_service("memory_service", InMemoryMemoryService)

    def get_credential_service(self) -> BaseCredentialService:
        """Get or create credential service.

        Retrieves the configured credential service or creates an in-memory
        implementation if none is configured and in-memory services are enabled.

        Returns:
            Configured credential service instance for authentication management
        """
        return self._get_or_create_service(
            "credential_service", InMemoryCredentialService
        )


class HistoryConfig(BaseModel):
    """Configuration for history service context extraction and session management.

    Defines how to extract context information from requests for history operations
    and manages session service configuration for conversation retrieval. Enables
    customizable history endpoints with flexible context extraction.

    Attributes:
        app_name: Static application name or callable to extract from request
        user_id: Static user ID or callable to extract from request (required)
        session_id: Static session ID or callable to extract from request (required)
        get_thread_list: Optional callable to transform session list format for client consumption
        get_state: Optional callable to transform state data before returning to client
        session_service: Session service implementation for history retrieval and management
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_name: str | Callable[[Request], Awaitable[str]] = "default"
    user_id: str | Callable[[Request], Awaitable[str]]
    session_id: str | Callable[[Request], Awaitable[str]]
    get_thread_list: (
        Callable[[list[Session]], Awaitable[list[dict[str, str]]]] | None
    ) = None
    get_state: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]] | None = None

    session_service: BaseSessionService = Field(default_factory=InMemorySessionService)
    adk_event_handler: type[BaseADKEventHandler] | None = None
    agui_event_handler: type[BaseAGUIEventHandler] | None = None
    translate_handler: type[BaseTranslateHandler] | None = None
