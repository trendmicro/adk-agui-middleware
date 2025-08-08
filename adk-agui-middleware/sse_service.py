from collections.abc import AsyncGenerator, Callable

from ag_ui.core import (
    AssistantMessage,
    BaseEvent,
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    ToolMessage, ToolCallEndEvent, ToolCallResultEvent,
)
from ag_ui.encoder import EventEncoder
from google.adk.memory import BaseMemoryService
from google.adk.sessions import BaseSessionService
from google.genai import types

from data_model.session import SessionParameter
from error_event import AGUIErrorEvent, AGUIEncoderError
from loggers.record_log import record_log
from manager.execution_manger import ExecutionManger
from manager.session_manager import SessionManager, SessionHandler
from pattern import Singleton


class AGUIMessageHandler:
    def __init__(self, agui_content: RunAgentInput):
        self.agui_content = agui_content

    @property
    def thread_id(self) -> str:
        return self.agui_content.thread_id

    @property
    def is_tool_result_submission(self) -> bool:
        if not self.agui_content.messages:
            return False
        return self.agui_content.messages[-1].role == "tool"

    async def get_latest_message(self) -> types.Content | None:
        if not self.agui_content.messages:
            return None
        for message in reversed(self.agui_content.messages):
            if message.role == "user" and message.content:
                return types.Content(
                    role="user", parts=[types.Part(text=message.content)]
                )
        return None

    async def extract_tool_results(self) -> list[dict]:
        most_recent_tool_message = next(
            (
                msg
                for msg in reversed(self.agui_content.messages)
                if isinstance(msg, ToolMessage)
            ),
            None,
        )
        if not most_recent_tool_message:
            return []

        tool_call_map = {
            tool_call.id: tool_call.function.name
            for msg in self.agui_content.messages
            if isinstance(msg, AssistantMessage) and msg.tool_calls
            for tool_call in msg.tool_calls
        }
        tool_name = tool_call_map.get(most_recent_tool_message.tool_call_id, "unknown")
        record_log(
            f"Extracted most recent ToolMessage: role={most_recent_tool_message.role}, "
            f"tool_call_id={most_recent_tool_message.tool_call_id}, "
            f"content='{most_recent_tool_message.content}'"
        )
        return [{"tool_name": tool_name, "message": most_recent_tool_message}]


class AGUIUserHandler:

    def __init__(
            self,
            agui_message: AGUIMessageHandler,
            session_handler: SessionHandler,
            execution_handler: ExecutionManger
    ):
        self.agui_message = agui_message
        self.session_handler = session_handler
        self.execution_handler = execution_handler

    @property
    def app_name(self):
        return self.session_handler.app_name

    @property
    def user_id(self):
        return self.session_handler.user_id

    @property
    def session_id(self):
        return self.agui_message.thread_id

    @property
    def run_id(self):
        return self.agui_message.agui_content.run_id

    @staticmethod
    async def check_tools_event(event: BaseEvent, tool_call_ids: list[str]):
        if isinstance(event, ToolCallEndEvent):
            tool_call_ids.append(event.tool_call_id)
        if isinstance(event, ToolCallResultEvent) and event.tool_call_id in tool_call_ids:
            tool_call_ids.remove(event.tool_call_id)

    def call_start(self):
        return RunStartedEvent(
            type=EventType.RUN_STARTED, thread_id=self.session_id, run_id=self.run_id
        )

    def call_finished(self):
        return RunFinishedEvent(
            type=EventType.RUN_FINISHED, thread_id=self.session_id, run_id=self.run_id
        )

    async def remove_pending_tool_call(self) -> RunErrorEvent | None:
        tool_results = await self.agui_message.extract_tool_results()
        if not tool_results:
            return AGUIErrorEvent.no_tool_results(self.agui_message.thread_id)
        try:
            for tool_result in tool_results:
                await self.session_handler.check_and_remove_pending_tool_call(tool_result["message"].tool_call_id)
            record_log(
                f"Starting new execution for tool result in thread {self.session_id}"
            )
        except Exception as e:
            return AGUIErrorEvent.tool_result_processing_error(e)

    async def _run_workflow(self) -> AsyncGenerator[BaseEvent]:
        yield self.call_start()

        await self.execution_handler.check_existing_execution(self.session_id)
        execution = await self._start_background_execution()
        await self.execution_handler.lock_execution(self.session_id, execution)

        tool_call_ids = []
        async for event in self._stream_events(execution):
            await self.check_tools_event(event, tool_call_ids)
            yield event
        for tool_call_id in tool_call_ids:
            await self.session_handler.add_pending_tool_call(tool_call_id)
        yield self.call_finished()

    async def run(self) -> AsyncGenerator[BaseEvent]:
        if self.agui_message.is_tool_result_submission and (
                error := await self.remove_pending_tool_call()
        ):
            yield error
            return

        try:
            async for event in self._run_workflow():
                yield event
        except Exception as e:
            yield AGUIErrorEvent.execution_error(e)
        finally:
            await self.execution_handler.unlock_execution(self.session_id)


class SSEService(metaclass=Singleton):
    def __init__(self, session_service: BaseSessionService):
        self.session_manager = SessionManager(
            session_service=session_service,
        )
        self.execution_handler = ExecutionManger()

    @staticmethod
    def _encoding_handler(encoder: EventEncoder, event: BaseEvent) -> str:
        try:
            return encoder.encode(event)
        except Exception as e:
            return AGUIEncoderError.encoding_error(encoder, e)

    async def get_runner(
            self, agui_content: RunAgentInput
    ) -> Callable[[], AsyncGenerator[BaseEvent]]:
        async def runner() -> AsyncGenerator[BaseEvent]:
            user_handler = AGUIUserHandler(
                agui_message=AGUIMessageHandler(agui_content),
                session_handler=SessionHandler(
                    session_manger=self.session_manager,
                    session_parameter=SessionParameter(
                        app_name="?????????????",
                        user_id="?????????????",
                        session_id=agui_content.thread_id
                    )
                ),
                execution_handler=self.execution_handler
            )
            async for event in user_handler.run():
                yield event

        return runner

    async def event_generator(
            self,
            encoder: EventEncoder,
            runner: Callable[[], AsyncGenerator[BaseEvent]],
    ) -> AsyncGenerator[str]:
        try:
            async for event in runner():
                yield self._encoding_handler(encoder, event)
        except Exception as e:
            yield AGUIEncoderError.agent_error(encoder, e)
