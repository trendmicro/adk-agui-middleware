from collections.abc import AsyncGenerator, Awaitable, Callable

from ag_ui.core import (
    BaseEvent,
    RunAgentInput,
)
from ag_ui.encoder import EventEncoder
from base_abc.sse_service import BaseSSEService
from data_model.context import ContextConfig, RunnerConfig
from data_model.session import SessionParameter
from event.error_event import AGUIEncoderError
from fastapi import Request
from google.adk import Runner
from google.adk.agents import BaseAgent
from handler.agui_message import AGUIMessageHandler
from handler.agui_user import AGUIUserHandler
from handler.session import SessionHandler
from manager.session import SessionManager


class SSEService(BaseSSEService):
    def __init__(
        self,
        agent: BaseAgent,
        runner_config: RunnerConfig,
        context_config: ContextConfig,
    ):
        self.agent = agent
        self.runner_config = runner_config
        self.session_manager = SessionManager(
            session_service=self.runner_config.session_service
        )
        self.runner_box: dict[str, Runner] = {}
        self.context_config = context_config

    async def _get_config_value(
        self, config_attr: str, agui_content: RunAgentInput, request: Request
    ) -> str:
        value: Callable[[RunAgentInput, Request], Awaitable[str]] | str = getattr(
            self.context_config, config_attr
        )
        if callable(value):
            return await value(agui_content, request)
        return value

    async def get_app_name(self, agui_content: RunAgentInput, request: Request) -> str:
        return await self._get_config_value("app_name", agui_content, request)

    async def get_user_id(self, agui_content: RunAgentInput, request: Request) -> str:
        return await self._get_config_value("user_id", agui_content, request)

    async def get_session_id(
        self, agui_content: RunAgentInput, request: Request
    ) -> str:
        return await self._get_config_value("session_id", agui_content, request)

    @staticmethod
    def _encoding_handler(encoder: EventEncoder, event: BaseEvent) -> str:
        try:
            return encoder.encode(event)
        except Exception as e:
            return AGUIEncoderError.encoding_error(encoder, e)

    def _create_runner(self, app_name: str) -> Runner:
        if app_name not in self.runner_box:
            self.runner_box[app_name] = Runner(
                app_name=app_name,
                agent=self.agent,
                session_service=self.session_manager.session_service,
                artifact_service=self.runner_config.get_artifact_service(),
                memory_service=self.runner_config.get_memory_service(),
                credential_service=self.runner_config.get_credential_service(),
            )
        return self.runner_box[app_name]

    async def get_runner(
        self, agui_content: RunAgentInput, request: Request
    ) -> Callable[[], AsyncGenerator[BaseEvent]]:
        async def runner() -> AsyncGenerator[BaseEvent]:
            app_name = await self.get_app_name(agui_content, request)
            user_id = await self.get_user_id(agui_content, request)
            session_id = await self.get_session_id(agui_content, request)
            user_handler = AGUIUserHandler(
                runner=self._create_runner(app_name),
                run_config=self.runner_config.run_config,
                agui_message=AGUIMessageHandler(agui_content),
                session_handler=SessionHandler(
                    session_manger=self.session_manager,
                    session_parameter=SessionParameter(
                        app_name=app_name, user_id=user_id, session_id=session_id
                    ),
                ),
            )
            async for event in user_handler.run():
                yield event

        return runner

    async def event_generator(
        self, runner: Callable[[], AsyncGenerator[BaseEvent]], encoder: EventEncoder
    ) -> AsyncGenerator[str]:
        try:
            async for event in runner():
                yield self._encoding_handler(encoder, event)
        except Exception as e:
            yield AGUIEncoderError.agent_error(encoder, e)
