from collections.abc import AsyncGenerator, Awaitable, Callable

from ag_ui.core import MessagesSnapshotEvent
from fastapi import Request
from google.adk.sessions import Session

from ..data_model.context import HandlerContext, HistoryConfig
from ..data_model.session import SessionParameter
from ..handler.running import RunningHandler
from ..manager.session import SessionManager
from ..utils.translate import MessageEventUtil


class HistoryHandler:
    def __init__(
        self,
        session_manager: SessionManager,
        running_handler: RunningHandler,
        app_name: str,
        user_id: str,
    ):
        self.session_manager = session_manager
        self.running_handler = running_handler
        self.app_name = app_name
        self.user_id = user_id
        self.message_event_util = MessageEventUtil()

    async def list_sessions(self) -> list[Session]:
        return await self.session_manager.list_sessions(
            app_name=self.app_name,
            user_id=self.user_id,
        )

    async def get_session(self, session_id: str) -> Session | None:
        return await self.session_manager.get_session(
            SessionParameter(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id,
            )
        )

    async def get_message_snapshot(self, session_id: str) -> MessagesSnapshotEvent:
        async def running() -> AsyncGenerator:
            for i in await self.get_session(session_id=session_id):
                yield i

        agui_event_box = []
        async for adk_event in self.running_handler.run_async_with_history(running()):
            async for agui_event in self.running_handler.run_async_with_agui(adk_event):
                agui_event_box.append(agui_event)
        return self.message_event_util.create_message_snapshot(agui_event_box)


class HistoryService:
    def __init__(self, history_config: HistoryConfig, handler_context: HandlerContext):
        self.history_config = history_config
        self.session_manager = SessionManager(
            session_service=self.history_config.session_service
        )
        self.handler_context = handler_context

    def _create_history_handler(self, app_name: str, user_id: str) -> HistoryHandler:
        return HistoryHandler(
            session_manager=self.session_manager,
            running_handler=RunningHandler(handler_context=self.handler_context),
            app_name=app_name,
            user_id=user_id,
        )

    async def _get_config_value(self, config_attr: str, request: Request) -> str:
        """Extract configuration value from context config.

        Handles both static string values and dynamic callable configurations
        that can extract values from the request context.

        Args:
            config_attr: Name of the configuration attribute to retrieve
            request: HTTP request for context extraction

        Returns:
            Configuration value as string
        """
        value: Callable[[Request], Awaitable[str]] | str = getattr(
            self.history_config, config_attr
        )
        if callable(value):
            return await value(request)
        return value

    async def list_threads(self, request: Request) -> list[dict[str, str]]:
        session_list = await self._create_history_handler(
            await self._get_config_value("app_name", request),
            await self._get_config_value("user_id", request),
        ).list_sessions()
        if self.history_config.get_chat_list:
            return await self.history_config.get_chat_list(session_list)
        return [{"session_id": session.id} for session in session_list]

    async def get_history(self, request: Request) -> MessagesSnapshotEvent:
        return await self._create_history_handler(
            await self._get_config_value("app_name", request),
            await self._get_config_value("user_id", request),
        ).get_message_snapshot(await self._get_config_value("session_id", request))
