# Copyright (C) 2025 Trend Micro Inc. All rights reserved.
from collections.abc import AsyncGenerator, Callable
from typing import Any

import jsonpatch  # type: ignore
from ag_ui.core import BaseEvent, SystemMessage, UserMessage
from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types

from ..data_model.session import SessionParameter
from ..event.agui_event import CustomMessagesSnapshotEvent
from ..handler.running import RunningHandler
from ..manager.session import SessionManager
from ..utils.convert.adk_event_to_agui_message import ADKEventToAGUIMessageConverter
from ..utils.translate import MessageEventUtil


class HistoryHandler:
    """Handles conversation history retrieval and message snapshot generation.

    Manages session listing, retrieval, and conversion of conversation history
    into AGUI message snapshots for client consumption.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        running_handler: RunningHandler,
        app_name: str,
        user_id: str,
    ) -> None:
        """Initialize the history handler.

        Args:
            :param session_manager: Manager for session operations
            :param running_handler: Handler for processing agent runs and events
            :param app_name: Name of the application
            :param user_id: Identifier for the user
        """
        self.session_manager = session_manager
        self.running_handler = running_handler
        self.app_name = app_name
        self.user_id = user_id
        self.message_event_util = MessageEventUtil()

    async def list_sessions(self) -> list[Session]:
        """List all sessions for the configured app and user.

        Returns:
            List of Session objects for the app and user
        """
        return await self.session_manager.list_sessions(
            app_name=self.app_name,
            user_id=self.user_id,
        )

    async def get_session(self, session_id: str) -> Session | None:
        """Retrieve a specific session by ID.

        Args:
            :param session_id: Unique identifier for the session

        Returns:
            Session object if found, None otherwise
        """
        return await self.session_manager.get_session(
            SessionParameter(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id,
            )
        )

    async def delete_session(self, session_id: str) -> None:
        """Delete a specific session by ID.

        Permanently removes the session and all associated conversation data.

        Args:
            :param session_id: Unique identifier for the session to delete
        """
        await self.session_manager.delete_session(
            SessionParameter(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id,
            )
        )

    @staticmethod
    def _check_raw_event_message_to_convert_agui(
        adk_event: Event,
    ) -> list[SystemMessage | UserMessage] | None:
        """Convert ADK event to AGUI message format if it contains user or developer content.

        Examines an ADK event to determine if it contains user or developer authored content
        that should be converted directly to AGUI message format. This bypasses the normal
        event translation pipeline for specific event types that map directly to messages.

        Args:
            :param adk_event: ADK Event to examine for direct message conversion

        Returns:
            List of SystemMessage or UserMessage objects if conversion is applicable,
            None if event should go through normal translation pipeline
        """
        if not (adk_event.content and adk_event.content.parts):
            return None
        message_mappings: dict[
            str, Callable[[types.Part], UserMessage | SystemMessage]
        ] = {
            "user": lambda part: UserMessage(
                role="user", id=adk_event.id, content=part.text
            ),
            "developer": lambda part: SystemMessage(
                role="system", id=adk_event.id, content=part.text
            ),
        }
        author_key = adk_event.author if adk_event.author in message_mappings else ""
        role_key = (
            adk_event.content.role if adk_event.content.role in message_mappings else ""
        )
        message_creator = message_mappings.get(author_key or role_key)
        if not message_creator:
            return None
        return [message_creator(part) for part in adk_event.content.parts if part.text]

    async def get_message_snapshot(
        self, session_id: str
    ) -> CustomMessagesSnapshotEvent | None:
        """Generate a message snapshot for a conversation session.

        Retrieves the session events and converts them to AGUI format
        for client consumption as a conversation history.

        Args:
            :param session_id: Unique identifier for the session

        Returns:
            MessagesSnapshotEvent containing the conversation history
        """
        session = await self.get_session(session_id=session_id)
        if session is None:
            return None

        async def running() -> AsyncGenerator[Event]:
            """Internal generator for session events.

            Yields:
                Session events for the specified session
            """
            for event in session.events:
                yield event

        agui_event_box: list[BaseEvent | UserMessage | SystemMessage] = []
        async for adk_event in self.running_handler.run_async_with_history(running()):
            if agui_events := self._check_raw_event_message_to_convert_agui(adk_event):
                agui_event_box.extend(agui_events)
                continue
            async for agui_event in self.running_handler.run_async_with_agui(adk_event):
                agui_event_box.append(agui_event)  # noqa: PERF401
        return self.message_event_util.create_message_snapshot(
            ADKEventToAGUIMessageConverter().convert(agui_event_box)
        )

    async def get_state_snapshot(self, session_id: str) -> dict[str, Any] | None:
        """Get the current state snapshot for a specific session.

        Retrieves the complete state dictionary for the session,
        returning an empty dictionary if the session is not found.

        Args:
            :param session_id: Unique identifier for the session

        Returns:
            Dictionary containing the session state, empty dict if session not found
        """
        return (
            session.state
            if (session := await self.get_session(session_id=session_id))
            else None
        )

    async def patch_state(
        self, session_id: str, state_patch: list[dict[str, Any]]
    ) -> None | dict[str, Any]:
        """Apply JSON patch operations to update session state incrementally.

        Uses JSON Patch RFC 6902 format to apply partial updates to the session state,
        enabling efficient incremental state modifications without replacing the entire
        state dictionary. This is useful for updating specific state fields while
        preserving other session data.

        Args:
            :param session_id: Unique identifier for the session to update
            :param state_patch: List of JSON Patch operations to apply to the session state

        Returns:
            Dictionary with success status if patch applied successfully, None if session not found
        """
        session = await self.get_session(session_id=session_id)
        if session is None:
            return None
        await self.session_manager.update_session_state(
            SessionParameter(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id,
            ),
            jsonpatch.apply_patch(session.state, state_patch),
        )
        return {"status": "updated"}
