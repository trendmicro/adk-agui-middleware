import json
from collections.abc import AsyncGenerator, Callable

from ag_ui.core import (
    AssistantMessage,
    BaseEvent,
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolMessage,
)
from ag_ui.encoder import EventEncoder
from google.adk import Runner
from google.adk.agents import BaseAgent, RunConfig
from google.adk.events import Event
from google.adk.sessions import BaseSessionService
from google.genai import types

from data_model.session import SessionParameter
from error_event import AGUIEncoderError, AGUIErrorEvent
from handler.session import SessionHandler
from loggers.record_log import record_error_log, record_log, record_warning_log
from manager.session import SessionManager
from pattern import Singleton
from tools.event_translator import EventTranslator


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

    @staticmethod
    def _parse_tool_content(content: str, tool_call_id: str) -> dict:
        if not content or not content.strip():
            record_warning_log(
                f"Empty tool result content for tool call {tool_call_id}, using empty success result"
            )
            return {"success": True, "result": None}
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            record_error_log("Invalid JSON in tool result", e)
            return {
                "error": f"Invalid JSON in tool result: {str(e)}",
                "raw_content": content,
                "error_type": "JSON_DECODE_ERROR",
            }

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

    async def process_tool_results(self) -> types.Content | None:
        if not self.is_tool_result_submission:
            return None
        parts = []
        for tool_msg in await self.extract_tool_results():
            tool_call_id = tool_msg["message"].tool_call_id
            content = tool_msg["message"].content
            result = self._parse_tool_content(content, tool_call_id)
            parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        id=tool_call_id,
                        name=tool_msg["tool_name"],
                        response=result,
                    )
                )
            )
        return types.Content(parts=parts, role="user")

    async def get_message(self) -> types.Content:
        return await self.process_tool_results() or await self.get_latest_message()


class AGUIUserHandler:
    def __init__(
        self,
        runner: Runner,
        run_config: RunConfig,
        agui_message: AGUIMessageHandler,
        session_handler: SessionHandler,
    ):
        self.runner = runner
        self.run_config = run_config
        self.agui_message = agui_message
        self.session_handler = session_handler
        self.event_translator = EventTranslator()

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
        if (
            isinstance(event, ToolCallResultEvent)
            and event.tool_call_id in tool_call_ids
        ):
            tool_call_ids.remove(event.tool_call_id)
        return tool_call_ids

    def call_start(self):
        return RunStartedEvent(
            type=EventType.RUN_STARTED, thread_id=self.session_id, run_id=self.run_id
        )

    def call_finished(self):
        return RunFinishedEvent(
            type=EventType.RUN_FINISHED, thread_id=self.session_id, run_id=self.run_id
        )

    async def run_async(self, message: types.Content) -> AsyncGenerator[Event]:
        async for event in self.runner.run_async(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=message,
        ):
            yield event

    async def translator_to_agui(self, adk_event: Event) -> AsyncGenerator[BaseEvent]:
        is_long_running_tool = False
        if not adk_event.is_final_response():
            async for ag_ui_event in self.event_translator.translate(adk_event):
                yield ag_ui_event
        else:
            async for ag_ui_event in self.event_translator.translate_lro_function_calls(
                adk_event
            ):
                yield ag_ui_event
                is_long_running_tool = ag_ui_event.type == EventType.TOOL_CALL_END
            if is_long_running_tool:
                return

    async def remove_pending_tool_call(self) -> RunErrorEvent | None:
        tool_results = await self.agui_message.extract_tool_results()
        if not tool_results:
            return AGUIErrorEvent.no_tool_results(self.agui_message.thread_id)
        try:
            for tool_result in tool_results:
                await self.session_handler.check_and_remove_pending_tool_call(
                    tool_result["message"].tool_call_id
                )
            record_log(
                f"Starting new execution for tool result in thread {self.session_id}"
            )
        except Exception as e:
            return AGUIErrorEvent.tool_result_processing_error(e)

    async def _run_workflow(self) -> AsyncGenerator[BaseEvent]:
        yield self.call_start()
        await self.session_handler.check_and_create_session()
        await self.session_handler.update_session_state()
        tool_call_ids = []
        async for adk_event in self.run_async(await self.agui_message.get_message()):
            async for agui_event in self.translator_to_agui(adk_event):
                await self.check_tools_event(agui_event, tool_call_ids)
                yield agui_event
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


class SSEService(metaclass=Singleton):
    def __init__(self, session_service: BaseSessionService, agent: BaseAgent):
        self.agent = agent
        self.session_manager = SessionManager(
            session_service=session_service,
        )
        self.runner_box: dict[str, Runner] = {}

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
            )
        return self.runner_box[app_name]

    async def get_runner(
        self, agui_content: RunAgentInput
    ) -> Callable[[], AsyncGenerator[BaseEvent]]:
        async def runner() -> AsyncGenerator[BaseEvent]:
            user_handler = AGUIUserHandler(
                runner=self._create_runner("?????????????"),
                run_config=RunConfig(),
                agui_message=AGUIMessageHandler(agui_content),
                session_handler=SessionHandler(
                    session_manger=self.session_manager,
                    session_parameter=SessionParameter(
                        app_name="?????????????",
                        user_id="?????????????",
                        session_id=agui_content.thread_id,
                    ),
                ),
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
