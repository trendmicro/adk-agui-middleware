"""Configuration models for AGUI middleware context and runner setup."""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from ag_ui.core import RunAgentInput
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
    BaseADKEventTimeoutHandler,
    BaseAGUIEventHandler,
    BaseAGUIStateSnapshotHandler,
    BaseInOutHandler,
    BaseTranslateHandler,
)


T = TypeVar("T", BaseArtifactService, BaseMemoryService, BaseCredentialService)


async def default_session_id(agui_content: RunAgentInput, request: Request) -> str:  # noqa: ARG001
    """Default session ID extractor that uses the thread ID from AGUI content.

    Provides a default implementation for extracting session identifiers from
    incoming AGUI requests. Uses the thread_id as the session identifier,
    enabling conversation continuity across multiple requests.

    :param agui_content: Input containing agent execution parameters and thread information
    :param request: HTTP request object (unused in default implementation)
    :return: Thread ID string to be used as session identifier
    """
    return agui_content.thread_id


class HandlerContext(BaseModel):
    """Context container for optional event and state handlers.

    Provides a configuration structure for customizing event processing
    behavior by injecting custom handlers at different stages of the pipeline.
    This enables extensible event processing through dependency injection.

    Attributes:
        adk_event_handler: Optional handler for processing ADK events before translation
        adk_event_timeout_handler: Optional handler for managing ADK event timeouts
        agui_event_handler: Optional handler for processing AGUI events before transmission
        agui_state_snapshot_handler: Optional handler for processing state snapshots
        translate_handler: Optional handler for custom event translation logic
        in_out_record_handler: Optional handler for input/output recording and transformation
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    adk_event_handler: type[BaseADKEventHandler] | None = None
    adk_event_timeout_handler: type[BaseADKEventTimeoutHandler] | None = None
    agui_event_handler: type[BaseAGUIEventHandler] | None = None
    agui_state_snapshot_handler: type[BaseAGUIStateSnapshotHandler] | None = None
    translate_handler: type[BaseTranslateHandler] | None = None
    in_out_record_handler: type[BaseInOutHandler] | None = None


class ConfigContext(BaseModel):
    """Configuration for extracting context information from requests.

    Defines how to extract application name, user ID, session ID, and initial state
    from incoming requests. Each field can be either a static value or a callable
    that extracts the value dynamically from the request. This enables flexible
    multi-tenant configuration and request-specific context extraction.

    Attributes:
        app_name: Static application name or callable to extract from request context
        user_id: Static user ID or callable to extract from request context (required)
        session_id: Static session ID or callable to extract from request context
        extract_initial_state: Optional callable to extract initial session state from request
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_name: str | Callable[[RunAgentInput, Request], Awaitable[str]] = "default"
    user_id: str | Callable[[RunAgentInput, Request], Awaitable[str]]
    session_id: str | Callable[[RunAgentInput, Request], Awaitable[str]] = (
        default_session_id
    )
    extract_initial_state: (
        Callable[[RunAgentInput, Request], Awaitable[dict[str, Any]]] | None
    ) = None


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

        :param service_attr: Name of the service attribute to check and potentially set
        :param service_class: Class to instantiate if service is None and in-memory is enabled
        :return: Service instance (existing or newly created)
        :raises ValueError: If service is None and in-memory services are disabled
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

        :return: Configured artifact service instance for file and data management
        """
        return self._get_or_create_service("artifact_service", InMemoryArtifactService)

    def get_memory_service(self) -> BaseMemoryService:
        """Get or create memory service.

        Retrieves the configured memory service or creates an in-memory
        implementation if none is configured and in-memory services are enabled.

        :return: Configured memory service instance for agent memory management
        """
        return self._get_or_create_service("memory_service", InMemoryMemoryService)

    def get_credential_service(self) -> BaseCredentialService:
        """Get or create credential service.

        Retrieves the configured credential service or creates an in-memory
        implementation if none is configured and in-memory services are enabled.

        :return: Configured credential service instance for authentication management
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
