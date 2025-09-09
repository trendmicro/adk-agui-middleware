from collections.abc import AsyncGenerator
from typing import Any

import jsonpatch  # type: ignore
from ag_ui.core import BaseEvent
from ag_ui.core.types import UserMessage
from google.adk.events import Event
from google.adk.sessions import Session

from ..data_model.session import SessionParameter
from ..event.agui_event import CustomMessagesSnapshotEvent
from ..handler.running import RunningHandler
from ..manager.session import SessionManager
from ..utils.convert import ADKEventToAGUIMessageConverter
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
            session_manager: Manager for session operations
            running_handler: Handler for processing agent runs and events
            app_name: Name of the application
            user_id: Identifier for the user
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
            session_id: Unique identifier for the session

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
            session_id: Unique identifier for the session to delete
        """
        await self.session_manager.delete_session(
            SessionParameter(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id,
            )
        )

    async def get_message_snapshot(
        self, session_id: str
    ) -> CustomMessagesSnapshotEvent | None:
        """Generate a message snapshot for a conversation session.

        Retrieves the session events and converts them to AGUI format
        for client consumption as a conversation history.

        Args:
            session_id: Unique identifier for the session

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

        agui_event_box: list[BaseEvent | UserMessage] = []
        async for adk_event in self.running_handler.run_async_with_history(running()):
            if adk_event.author == "user":
                agui_event_box.append(
                    UserMessage(
                        role="user",
                        id=adk_event.id,
                        content=adk_event.content.parts[0].text
                        if adk_event.content and adk_event.content.parts
                        else "",
                    )
                )
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
            session_id: Unique identifier for the session

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
        if session := await self.get_session(session_id=session_id) is not None:
            session.state = jsonpatch.apply_patch(session.state, state_patch)  # type: ignore
            return {"status": "updated"}
        return None
