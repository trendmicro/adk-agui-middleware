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

    Args:
        agui_content: Input containing thread information
        request: HTTP request (unused in default implementation)

    Returns:
        Thread ID as session identifier
    """
    return agui_content.thread_id


class HandlerContext(BaseModel):
    """Context container for optional event and state handlers.

    Provides a configuration structure for customizing event processing
    behavior by injecting custom handlers at different stages of the pipeline.

    Attributes:
        adk_event_handler: Optional handler for processing ADK events
        agui_event_handler: Optional handler for processing AGUI events
        agui_state_snapshot_handler: Optional handler for processing state snapshots
        translate_handler: Optional handler for event translation logic
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
    that extracts the value dynamically from the request.
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

    Attributes:
        agui_main_path: Path for the main agent interaction endpoint
        agui_chat_list_path: Path for listing available conversations
        agui_history_path: Path template for retrieving conversation history
    """

    agui_main_path: str = "/"
    agui_chat_list_path: str = "/list"
    agui_history_path: str = "/history/{session_id}"


class RunnerConfig(BaseModel):
    """Configuration for ADK runner setup and services.

    Manages the configuration of various services required for agent execution
    including session, artifact, memory, and credential services.
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

        Args:
            service_attr: Name of the service attribute
            service_class: Class to instantiate if service is None

        Returns:
            Service instance

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

        Returns:
            Configured artifact service instance
        """
        return self._get_or_create_service("artifact_service", InMemoryArtifactService)

    def get_memory_service(self) -> BaseMemoryService:
        """Get or create memory service.

        Returns:
            Configured memory service instance
        """
        return self._get_or_create_service("memory_service", InMemoryMemoryService)

    def get_credential_service(self) -> BaseCredentialService:
        """Get or create credential service.

        Returns:
            Configured credential service instance
        """
        return self._get_or_create_service(
            "credential_service", InMemoryCredentialService
        )


class HistoryConfig(BaseModel):
    """Configuration for history service context extraction and session management.

    Defines how to extract context information from requests for history operations
    and manages session service configuration for conversation retrieval.

    Attributes:
        app_name: Static app name or callable to extract from request
        user_id: Static user ID or callable to extract from request
        session_id: Static session ID or callable to extract from request
        get_chat_list: Optional callable to transform session list format
        session_service: Session service implementation for history retrieval
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_name: str | Callable[[Request], Awaitable[str]] = "default"
    user_id: str | Callable[[Request], Awaitable[str]]
    session_id: str | Callable[[Request], Awaitable[str]]
    get_chat_list: Callable[[list[Session]], Awaitable[list[dict[str, str]]]] | None = (
        None
    )

    session_service: BaseSessionService = Field(default_factory=InMemorySessionService)
