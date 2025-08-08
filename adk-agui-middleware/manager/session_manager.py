import time
from typing import Any

from google.adk.events import Event, EventActions

from data_model.session import SessionParameter
from loggers.record_log import record_error_log, record_log, record_warning_log


class TrackedSessionManger:
    def __init__(self):
        self._user_sessions: dict[str, set[str]] = {}
        self._session_keys: set[str] = set()
        self._max_per_user: int | None = None

    async def check_user_session_limit(self, user_id: str, session_id: str) -> bool:
        if not (session_id not in self._session_keys and self._max_per_user):
            return False
        return len(self._user_sessions.get(user_id, set())) >= self._max_per_user

    def track_session(self, user_id: str, session_id: str):
        self._session_keys.add(session_id)
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)


class SessionManager:
    def __init__(self, session_service):
        self.session_service = session_service
        self.tracked_sessions = TrackedSessionManger()

    async def get_or_create_session(
        self,
        session_parameter: SessionParameter,
        initial_state: dict[str, Any] | None = None,
    ) -> Any:
        if self.tracked_sessions.check_user_session_limit(
            session_parameter.user_id, session_parameter.session_id
        ):
            record_warning_log(
                f"User {session_parameter.user_id} has reached the maximum session limit for session {session_parameter.session_id}."
            )
            raise Exception("User session limit reached")
        session = await self.session_service.get_session(
            session_id=session_parameter.session_id,
            app_name=session_parameter.app_name,
            user_id=session_parameter.user_id,
        )
        if not session:
            session = await self.session_service.create_session(
                session_id=session_parameter.session_id,
                user_id=session_parameter.user_id,
                app_name=session_parameter.app_name,
                state=initial_state or {},
            )
        self.tracked_sessions.track_session(
            user_id=session_parameter.user_id, session_id=session_parameter.session_id
        )
        return session

    async def update_session_state(
        self,
        session_parameter: SessionParameter,
        state_updates: dict,
    ) -> bool:
        session = await self.session_service.get_session(
            session_id=session_parameter.session_id,
            app_name=session_parameter.app_name,
            user_id=session_parameter.user_id,
        )
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

    async def get_session_state(
        self, session_parameter: SessionParameter
    ) -> dict | None:
        try:
            session = await self.session_service.get_session(
                session_id=session_parameter.session_id,
                app_name=session_parameter.app_name,
                user_id=session_parameter.user_id,
            )
            if not session:
                record_warning_log(
                    f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
                )
                return None
            if hasattr(session.state, "to_dict"):
                return session.state.to_dict()
            return dict(session.state)
        except Exception as e:
            record_error_log(f"Failed to get session state: {e}")
            return None

    async def get_state_value(
        self,
        session_parameter: SessionParameter,
        key: str,
        default: Any = None,
    ) -> Any:
        try:
            session = await self.session_service.get_session(
                session_id=session_parameter.session_id,
                app_name=session_parameter.app_name,
                user_id=session_parameter.user_id,
            )
            if not session:
                record_warning_log(
                    f"Session not found: {session_parameter.app_name}:{session_parameter.session_id}"
                )
                return default
            if hasattr(session.state, "get"):
                return session.state.get(key, default)
            return session.state.get(key, default) if key in session.state else default
        except Exception as e:
            record_error_log(f"Failed to get state value: {e}")
            return default


class SessionHandler:
    def __init__(
        self, session_manger: SessionManager, session_parameter: SessionParameter
    ):
        self.session_manger = session_manger
        self.session_parameter = session_parameter

    @property
    def app_name(self):
        return self.session_parameter.app_name

    @property
    def user_id(self):
        return self.session_parameter.user_id

    @property
    def session_id(self):
        return self.session_parameter.session_id

    @staticmethod
    def get_pending_tool_calls_dict(pending_calls) -> Any:
        return {"pending_tool_calls": pending_calls}

    async def check_and_remove_pending_tool_call(self, tool_call_id: str):
        pending_calls = await self.get_pending_tool_calls()
        if tool_call_id not in pending_calls:
            record_warning_log(
                f"No pending tool calls found for tool result {tool_call_id} in thread {self.session_parameter.session_id}"
            )
            return
        record_log(
            f"Processing tool result {tool_call_id} for thread {self.session_parameter.session_id} with pending tools"
        )
        pending_calls.remove(tool_call_id)
        success = await self.session_manger.update_session_state(
            session_parameter=self.session_parameter,
            state_updates=self.get_pending_tool_calls_dict(pending_calls),
        )
        record_log(
            f"Removed tool call {tool_call_id} from session {self.session_parameter.session_id} pending list is {success}."
        )

    async def add_pending_tool_call(self, tool_call_id: str):
        record_log(
            f"Adding pending tool call {tool_call_id} for session {self.session_parameter.session_id}, app_name={self.session_parameter.app_name}, user_id={self.session_parameter.user_id}"
        )
        try:
            pending_calls = await self.session_manger.get_state_value(
                self.session_parameter,
                key="pending_tool_calls",
                default=[],
            )
            if tool_call_id not in pending_calls:
                pending_calls.append(tool_call_id)
                if await self.session_manger.update_session_state(
                    self.session_parameter,
                    state_updates=self.get_pending_tool_calls_dict(pending_calls),
                ):
                    record_log(
                        f"Added tool call {tool_call_id} to session {self.session_parameter.session_id} pending list"
                    )
        except Exception as e:
            record_error_log(
                f"Failed to add pending tool call {tool_call_id} to session {self.session_parameter.session_id}.",
                e,
            )

    async def get_pending_tool_calls(self) -> Any | None:
        try:
            session_history = self.session_manger.user_sessions.get(
                self.session_parameter.user_id
            )
            if self.session_parameter.session_id not in session_history:
                record_warning_log(
                    f"Session {self.session_parameter.session_id} not found for user {self.session_parameter.user_id}."
                )
                return None
            return await self.session_manger.get_state_value(
                session_parameter=self.session_parameter,
                key="pending_tool_calls",
                default=[],
            )
        except Exception as e:
            record_error_log(
                f"Failed to check pending tool calls for session {self.session_parameter.session_id}.",
                e,
            )
        return None
