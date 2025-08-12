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
    return agui_content.thread_id


class ContextConfig(BaseModel):
    app_name: str | Callable[[RunAgentInput, Request], Awaitable[str]] = "default"
    user_id: str | Callable[[RunAgentInput, Request], Awaitable[str]]
    session_id: str | Callable[[RunAgentInput, Request], Awaitable[str]] = (
        default_session_id
    )
    extract_initial_state: (
        Callable[[RunAgentInput, Request], Awaitable[dict[str, str]]] | None
    ) = None


class RunnerConfig(BaseModel):
    use_in_memory_services: bool = True
    run_config: RunConfig = RunConfig(streaming_mode=StreamingMode.SSE)
    session_service: BaseSessionService = Field(default_factory=InMemorySessionService)
    artifact_service: BaseArtifactService | None = None
    memory_service: BaseMemoryService | None = None
    credential_service: BaseCredentialService | None = None

    def _get_or_create_service(self, service_attr: str, service_class: type[T]) -> T:
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
        return self._get_or_create_service("artifact_service", InMemoryArtifactService)

    def get_memory_service(self) -> BaseMemoryService:
        return self._get_or_create_service("memory_service", InMemoryMemoryService)

    def get_credential_service(self) -> BaseCredentialService:
        return self._get_or_create_service(
            "credential_service", InMemoryCredentialService
        )
