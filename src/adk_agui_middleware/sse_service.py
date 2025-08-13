"""Concrete implementation of Server-Sent Events service for AGUI middleware."""

import asyncio
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
from handler.agui_user import AGUIUserHandler
from handler.session import SessionHandler
from handler.user_message import UserMessageHandler
from manager.session import SessionManager
from tools.shutdown import ShutdownHandler


class SSEService(BaseSSEService):
    """Concrete implementation of SSE service for handling AGUI agent interactions.

    Manages agent execution, session state, and event streaming for AGUI middleware.
    Coordinates between agent runners, session management, and event translation.
    """

    def __init__(
        self,
        agent: BaseAgent,
        runner_config: RunnerConfig,
        context_config: ContextConfig,
    ):
        """Initialize SSE service with agent and configuration.

        Args:
            agent: Base agent implementation for processing requests
            runner_config: Configuration for agent runners and services
            context_config: Configuration for extracting context from requests
        """
        self.agent = agent
        self.runner_config = runner_config
        self.session_manager = SessionManager(
            session_service=self.runner_config.session_service
        )
        self._runner_lock = asyncio.Lock()
        self.runner_box: dict[str, Runner] = {}
        self.context_config = context_config
        self.shutdown_handler = ShutdownHandler()

    async def _get_config_value(
        self, config_attr: str, agui_content: RunAgentInput, request: Request
    ) -> str | None:
        """Extract configuration value from context config.

        Handles both static string values and dynamic callable configurations
        that can extract values from the request context.

        Args:
            config_attr: Name of the configuration attribute to retrieve
            agui_content: Input containing agent execution parameters
            request: HTTP request for context extraction

        Returns:
            Configuration value as string, or None if not available
        """
        value: Callable[[RunAgentInput, Request], Awaitable[str]] | str = getattr(
            self.context_config, config_attr
        )
        if callable(value):
            return await value(agui_content, request)
        return value

    async def extract_app_name(
        self, agui_content: RunAgentInput, request: Request
    ) -> str:
        """Extract application name from the request context.

        Args:
            agui_content: Input containing agent execution parameters
            request: HTTP request for context extraction

        Returns:
            Application name string
        """
        return await self._get_config_value("app_name", agui_content, request)

    async def extract_user_id(
        self, agui_content: RunAgentInput, request: Request
    ) -> str:
        """Extract user identifier from the request context.

        Args:
            agui_content: Input containing agent execution parameters
            request: HTTP request for context extraction

        Returns:
            User identifier string
        """
        return await self._get_config_value("user_id", agui_content, request)

    async def extract_session_id(
        self, agui_content: RunAgentInput, request: Request
    ) -> str:
        """Extract session identifier from the request context.

        Args:
            agui_content: Input containing agent execution parameters
            request: HTTP request for context extraction

        Returns:
            Session identifier string
        """
        return await self._get_config_value("session_id", agui_content, request)

    async def extract_initial_state(
        self, agui_content: RunAgentInput, request: Request
    ) -> dict[str, str] | None:
        """Extract initial state dictionary from the request context.

        Args:
            agui_content: Input containing agent execution parameters
            request: HTTP request for context extraction

        Returns:
            Dictionary containing initial state key-value pairs, or None
        """
        return await self._get_config_value(
            "extract_initial_state", agui_content, request
        )

    @staticmethod
    def _encoding_handler(encoder: EventEncoder, event: BaseEvent) -> str:
        """Handle event encoding with error recovery.

        Attempts to encode the event using the provided encoder, falling back
        to error event encoding if the primary encoding fails.

        Args:
            encoder: Event encoder for formatting events
            event: Base event to be encoded

        Returns:
            Encoded event string, either successful encoding or error event
        """
        try:
            return encoder.encode(event)
        except Exception as e:
            return AGUIEncoderError.encoding_error(encoder, e)

    async def _create_runner(self, app_name: str) -> Runner:
        """Create or retrieve a Runner instance for the specified application.

        Implements lazy initialization and caching of Runner instances per app.
        Each app gets its own Runner with configured services.

        Args:
            app_name: Name of the application requiring a runner

        Returns:
            Runner instance configured for the specified application
        """
        async with self._runner_lock:
            if app_name not in self.runner_box:
                runner = Runner(
                    app_name=app_name,
                    agent=self.agent,
                    session_service=self.session_manager.session_service,
                    artifact_service=self.runner_config.get_artifact_service(),
                    memory_service=self.runner_config.get_memory_service(),
                    credential_service=self.runner_config.get_credential_service(),
                )
                self.shutdown_handler.register_shutdown_function(runner.close)
                self.runner_box[app_name] = runner
            return self.runner_box[app_name]

    async def get_runner(
        self, agui_content: RunAgentInput, request: Request
    ) -> Callable[[], AsyncGenerator[BaseEvent]]:
        """Create a configured runner function for the given request.

        Extracts context from the request, creates necessary handlers and managers,
        and returns a runner function that generates agent events.

        Args:
            agui_content: Input containing agent execution parameters
            request: HTTP request containing client context

        Returns:
            Callable that returns an async generator of BaseEvent objects
        """

        async def runner() -> AsyncGenerator[BaseEvent]:
            """Internal runner function that executes the agent and yields events.

            Yields:
                BaseEvent objects representing agent execution events
            """
            app_name = await self.extract_app_name(agui_content, request)
            user_id = await self.extract_user_id(agui_content, request)
            session_id = await self.extract_session_id(agui_content, request)
            initial_state = await self.extract_initial_state(agui_content, request)
            user_handler = AGUIUserHandler(
                runner=await self._create_runner(app_name),
                run_config=self.runner_config.run_config,
                agui_message=UserMessageHandler(agui_content, request, initial_state),
                session_handler=SessionHandler(
                    session_manager=self.session_manager,
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
        """Generate encoded event strings from the agent runner.

        Executes the runner and encodes each event for SSE transmission,
        handling any errors that occur during execution or encoding.

        Args:
            runner: Callable that returns an async generator of events
            encoder: Event encoder for formatting events

        Yields:
            Encoded event strings ready for SSE transmission
        """
        try:
            async for event in runner():
                yield self._encoding_handler(encoder, event)
        except Exception as e:
            yield AGUIEncoderError.agent_error(encoder, e)

    async def close(self) -> None:
        """Close all cached Runner instances."""
        async with self._runner_lock:
            for runner in self.runner_box.values():
                await runner.close()
            self.runner_box.clear()
