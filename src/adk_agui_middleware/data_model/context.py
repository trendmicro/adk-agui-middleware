"""Configuration models for AGUI middleware context and runner setup."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from ag_ui.core import RunAgentInput
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
from google.adk.sessions import BaseSessionService, InMemorySessionService
from pydantic import BaseModel, Field
from starlette.requests import Request


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


class ContextConfig(BaseModel):
    """Configuration for extracting context information from requests.

    Defines how to extract application name, user ID, session ID, and initial state
    from incoming requests. Each field can be either a static value or a callable
    that extracts the value dynamically from the request.
    """

    app_name: str | Callable[[RunAgentInput, Request], Awaitable[str]] = "default"
    user_id: str | Callable[[RunAgentInput, Request], Awaitable[str]]
    session_id: str | Callable[[RunAgentInput, Request], Awaitable[str]] = (
        default_session_id
    )
    extract_initial_state: (
        Callable[[RunAgentInput, Request], Awaitable[dict[str, str]]] | None
    ) = None


class RunnerConfig(BaseModel):
    """Configuration for ADK runner setup and services.

    Manages the configuration of various services required for agent execution
    including session, artifact, memory, and credential services.
    """

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
        return service

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
