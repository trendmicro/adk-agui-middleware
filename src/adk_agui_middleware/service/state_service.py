from collections.abc import Awaitable, Callable
from typing import Any

import jsonpatch  # type: ignore
from ag_ui.core import StateSnapshotEvent
from fastapi import Request

from ..data_model.config import StateConfig
from ..data_model.session import SessionParameter
from ..handler.session import SessionHandler
from ..manager.session import SessionManager
from ..utils.translate import StateEventUtil


class StateService:
    def __init__(self, state_config: StateConfig):
        self.state_config = state_config
        self.session_manager = SessionManager(
            session_service=self.state_config.session_service
        )
        self.state_event_util = StateEventUtil()

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
            self.state_config, config_attr
        )
        if callable(value):
            return await value(request)
        return value

    async def _get_session_parameter(self, request: Request) -> SessionParameter:
        return SessionParameter(
            app_name=await self._get_config_value("app_name", request),
            user_id=await self._get_config_value("user_id", request),
            session_id=await self._get_config_value("session_id", request),
        )

    async def _create_session_handler(self, request: Request) -> SessionHandler:
        return SessionHandler(
            session_manager=self.session_manager,
            session_parameter=await self._get_session_parameter(request),
        )

    async def get_state_snapshot(self, request: Request) -> StateSnapshotEvent:
        session_handler = await self._create_session_handler(request)
        state = (
            session.state if (session := await session_handler.get_session()) else None
        )
        if state is None:
            raise ValueError("Session not found")
        if self.state_config.get_state:
            state = await self.state_config.get_state(state)
        return self.state_event_util.create_state_snapshot_event(state)

    async def patch_state(
        self, request: Request, state_patch: list[dict[str, Any]]
    ) -> dict[str, str]:
        session_handler = await self._create_session_handler(request)
        session = await session_handler.get_session()
        if session is None:
            raise ValueError("Session not found")
        await session_handler.update_session_state(
            jsonpatch.apply_patch(session.state, state_patch)
        )
        return {"status": "updated"}
