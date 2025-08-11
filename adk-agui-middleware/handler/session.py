from typing import Any

from data_model.session import SessionParameter
from loggers.record_log import record_error_log, record_log, record_warning_log
from manager.session import SessionManager


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

    def check_and_create_session(self, initial_state: dict[str, Any] | None = None):
        return self.session_manger.check_and_create_session(
            session_parameter=self.session_parameter, initial_state=initial_state
        )

    def update_session_state(self, initial_state: dict[str, Any] | None = None):
        return self.session_manger.update_session_state(
            session_parameter=self.session_parameter,
            state_updates=initial_state,
        )

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
            pending_calls = (
                await self.session_manger.get_session_state(
                    self.session_parameter,
                )
            ).get("pending_tool_calls", [])
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
            session_history = await self.session_manger.get_session_state(
                self.session_parameter
            )
            if self.session_parameter.session_id not in session_history:
                record_warning_log(
                    f"Session {self.session_parameter.session_id} not found for user {self.session_parameter.user_id}."
                )
                return None
            return session_history.get("pending_tool_calls", [])
        except Exception as e:
            record_error_log(
                f"Failed to check pending tool calls for session {self.session_parameter.session_id}.",
                e,
            )
        return None
