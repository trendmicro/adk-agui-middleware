import asyncio
from collections.abc import Callable

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
)
from google.adk.agents import BaseAgent, RunConfig as ADKRunConfig
from google.adk.artifacts import BaseArtifactService, InMemoryArtifactService
from google.adk.auth.credential_service.base_credential_service import (
    BaseCredentialService,
)
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory import BaseMemoryService, InMemoryMemoryService
from google.adk.sessions import BaseSessionService, InMemorySessionService


class ADKAgent:
    def __init__(
        self,
        adk_agent: BaseAgent,
        # App identification
        app_name: str | None = None,
        session_timeout_seconds: int | None = 1200,
        app_name_extractor: Callable[[RunAgentInput], str] | None = None,
        # User identification
        user_id: str | None = None,
        user_id_extractor: Callable[[RunAgentInput], str] | None = None,
        # ADK Services
        session_service: BaseSessionService | None = None,
        artifact_service: BaseArtifactService | None = None,
        memory_service: BaseMemoryService | None = None,
        credential_service: BaseCredentialService | None = None,
        # Configuration
        run_config_factory: Callable[[RunAgentInput], ADKRunConfig] | None = None,
        use_in_memory_services: bool = True,
        # Tool configuration
        execution_timeout_seconds: int = 600,  # 10 minutes
        tool_timeout_seconds: int = 300,  # 5 minutes
        max_concurrent_executions: int = 10,
        # Session cleanup configuration
        cleanup_interval_seconds: int = 300,  # 5 minutes default
    ):
        """Initialize the ADKAgent.

        Args:
            adk_agent: The ADK agent instance to use
            app_name: Static application name for all requests
            app_name_extractor: Function to extract app name dynamically from input
            user_id: Static user ID for all requests
            user_id_extractor: Function to extract user ID dynamically from input
            session_service: Session management service (defaults to InMemorySessionService)
            artifact_service: File/artifact storage service
            memory_service: Conversation memory and search service (also enables automatic session memory)
            credential_service: Authentication credential storage
            run_config_factory: Function to create RunConfig per request
            use_in_memory_services: Use in-memory implementations for unspecified services
            execution_timeout_seconds: Timeout for entire execution
            tool_timeout_seconds: Timeout for individual tool calls
            max_concurrent_executions: Maximum concurrent background executions
        """

        self._adk_agent = adk_agent
        self._static_app_name = app_name
        self._app_name_extractor = app_name_extractor
        self._static_user_id = user_id
        self._user_id_extractor = user_id_extractor
        self._run_config_factory = run_config_factory or self._default_run_config

        # Initialize services with intelligent defaults
        if use_in_memory_services:
            self._artifact_service = artifact_service or InMemoryArtifactService()
            self._memory_service = memory_service or InMemoryMemoryService()
            self._credential_service = credential_service or InMemoryCredentialService()
        else:
            # Require explicit services for production
            self._artifact_service = artifact_service
            self._memory_service = memory_service
            self._credential_service = credential_service

        # Session lifecycle management - use singleton
        # Use provided session service or create default based on use_in_memory_services
        if session_service is None:
            session_service = (
                InMemorySessionService()
            )  # Default for both dev and production

        self._session_manager = SessionManager.get_instance(
            session_service=session_service,
            memory_service=self._memory_service,  # Pass memory service for automatic session memory
            session_timeout_seconds=session_timeout_seconds,  # 20 minutes default
            cleanup_interval_seconds=cleanup_interval_seconds,
            max_sessions_per_user=None,  # No limit by default
            auto_cleanup=True,  # Enable by default
        )

        # Tool execution tracking
        self._active_executions: dict[str, ExecutionState] = {}
        self._execution_timeout = execution_timeout_seconds
        self._tool_timeout = tool_timeout_seconds
        self._max_concurrent = max_concurrent_executions
        self._execution_lock = asyncio.Lock()

        # Event translator will be created per-session for thread safety

        # Cleanup is managed by the session manager
        # Will start when first async operation runs

    async def _run_adk_in_background(
        self,
        input: RunAgentInput,
        adk_agent: BaseAgent,
        user_id: str,
        app_name: str,
        event_queue: asyncio.Queue,
    ):
        """Run ADK agent in background, emitting events to queue.

        Args:
            input: The run input
            adk_agent: The ADK agent to run (already prepared with tools and SystemMessage)
            user_id: User ID
            app_name: App name
            event_queue: Queue for emitting events
        """
        try:
            # Create RunConfig
            run_config = self._run_config_factory(input)
            new_message = await self._convert_latest_message(input)
            event_translator = EventTranslator()

            # Run ADK agent
            is_long_running_tool = False
            async for adk_event in runner.run_async(
                user_id=user_id,
                session_id=input.thread_id,
                new_message=new_message,
                run_config=run_config,
            ):
                if not adk_event.is_final_response():
                    # Translate and emit events
                    async for ag_ui_event in event_translator.translate(
                        adk_event, input.thread_id, input.run_id
                    ):
                        logger.debug(
                            f"Emitting event to queue: {type(ag_ui_event).__name__} (thread {input.thread_id}, queue size before: {event_queue.qsize()})"
                        )
                        await event_queue.put(ag_ui_event)
                        logger.debug(
                            f"Event queued: {type(ag_ui_event).__name__} (thread {input.thread_id}, queue size after: {event_queue.qsize()})"
                        )
                else:
                    # LongRunning Tool events are usually emmitted in final response
                    async for (
                        ag_ui_event
                    ) in event_translator.translate_lro_function_calls(adk_event):
                        await event_queue.put(ag_ui_event)
                        if ag_ui_event.type == EventType.TOOL_CALL_END:
                            is_long_running_tool = True
                        logger.debug(
                            f"Event queued: {type(ag_ui_event).__name__} (thread {input.thread_id}, queue size after: {event_queue.qsize()})"
                        )
                    # hard stop the execution if we find any long running tool
                    if is_long_running_tool:
                        return
            # Force close any streaming messages
            async for ag_ui_event in event_translator.force_close_streaming_message():
                await event_queue.put(ag_ui_event)
            # moving states snapshot events after the text event clousure to avoid this error https://github.com/Contextable/ag-ui/issues/28
            final_state = await self._session_manager.get_session_state(
                input.thread_id, app_name, user_id
            )
            if final_state:
                ag_ui_event = event_translator.create_state_snapshot_event(final_state)
                await event_queue.put(ag_ui_event)
            # Signal completion - ADK execution is done
            logger.debug(
                f"Background task sending completion signal for thread {input.thread_id}"
            )
            await event_queue.put(None)
            logger.debug(
                f"Background task completion signal sent for thread {input.thread_id}"
            )

        except Exception as e:
            logger.error(f"Background execution error: {e}", exc_info=True)
            # Put error in queue
            await event_queue.put(
                RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    message=str(e),
                    code="BACKGROUND_EXECUTION_ERROR",
                )
            )
            await event_queue.put(None)
        finally:
            # Background task cleanup completed
            # Note: toolset cleanup is handled by garbage collection
            # since toolset is now embedded in the agent's tools
            pass
