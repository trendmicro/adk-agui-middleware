import time
from typing import Any

from data_model.session import SessionParameter
from google.adk.events import Event, EventActions
from google.adk.sessions import BaseSessionService, Session
from loggers.record_log import record_error_log, record_warning_log


class SessionManager:
    def __init__(self, session_service: BaseSessionService):
        self.session_service = session_service

    async def get_session(self, session_parameter: SessionParameter) -> Session | None:
        return await self.session_service.get_session(
            session_id=session_parameter.session_id,
            app_name=session_parameter.app_name,
            user_id=session_parameter.user_id,
        )

    async def check_and_create_session(
        self,
        session_parameter: SessionParameter,
        initial_state: dict[str, Any] | None = None,
    ) -> Session:
        session = await self.get_session(session_parameter)
        if not session:
            session = await self.session_service.create_session(
                session_id=session_parameter.session_id,
                user_id=session_parameter.user_id,
                app_name=session_parameter.app_name,
                state=initial_state or {},
            )
        return session

    async def update_session_state(
        self,
        session_parameter: SessionParameter,
        state_updates: dict[str, Any] | None,
    ) -> bool:
        session = await self.get_session(session_parameter)
        if not (session and state_updates):
            record_warning_log(
                f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
            )
            return False
        event = Event(
            invocation_id=f"state_update_{int(time.time())}",
            author="system",
            actions=EventActions(state_delta=state_updates),
            timestamp=time.time(),
        )
        await self.session_service.append_event(session, event)
        return True

    async def get_session_state(self, session_parameter: SessionParameter) -> dict[str, Any]:
        try:
            if session := await self.get_session(session_parameter):
                return session.state
            record_warning_log(
                f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
            )
        except Exception as e:
            record_error_log(f"Failed to get session state: {e}")
            return {}
        return {}

    async def get_state_value(
        self,
        session_parameter: SessionParameter,
        key: str,
        default: Any = None,
    ) -> Any:
        try:
            session = await self.get_session(session_parameter)
            if not session:
                record_warning_log(
                    f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
                )
                return default
            return session.state.get(key, default)
        except Exception as e:
            record_error_log(f"Failed to get state value: {e}")
            return default
