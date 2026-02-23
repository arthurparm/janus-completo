"""
ConversationHandler - Continuous Voice Dialogue for Janus
==========================================================

Manages voice conversation mode where users can speak naturally
without repeating the wake word for each interaction.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ConversationState(Enum):
    """Conversation mode states."""

    IDLE = "idle"  # Not in conversation mode
    LISTENING = "listening"  # Waiting for user speech
    PROCESSING = "processing"  # Processing user input
    RESPONDING = "responding"  # System is speaking
    WAITING = "waiting"  # Brief pause between turns


@dataclass
class ConversationContext:
    """Context for current conversation."""

    session_id: str
    started_at: datetime
    turns: int = 0
    last_activity: datetime = field(default_factory=datetime.now)
    user_messages: list = field(default_factory=list)
    assistant_messages: list = field(default_factory=list)

    def add_user_message(self, text: str):
        self.user_messages.append({"text": text, "timestamp": datetime.now()})
        self.turns += 1
        self.last_activity = datetime.now()

    def add_assistant_message(self, text: str):
        self.assistant_messages.append({"text": text, "timestamp": datetime.now()})
        self.last_activity = datetime.now()


class ConversationHandler:
    """
    Manages continuous voice conversation mode.

    In conversation mode:
    - No wake word required between turns
    - Auto-timeout after silence period
    - Maintains conversation context
    - Handles turn-taking (user vs system)
    """

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_turns: int = 50,
        on_user_speech: Callable[[str], Awaitable[str]] | None = None,
    ):
        """
        Initialize conversation handler.

        Args:
            timeout_seconds: Seconds of silence before ending conversation
            max_turns: Maximum conversation turns before auto-end
            on_user_speech: Callback when user speaks (returns response)
        """
        self.timeout_seconds = timeout_seconds
        self.max_turns = max_turns
        self.on_user_speech = on_user_speech

        self._state = ConversationState.IDLE
        self._context: ConversationContext | None = None
        self._timeout_task: asyncio.Task | None = None
        self._callbacks: dict = {}

        logger.info("ConversationHandler initialized", timeout=timeout_seconds, max_turns=max_turns)

    @property
    def state(self) -> ConversationState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state != ConversationState.IDLE

    @property
    def context(self) -> ConversationContext | None:
        return self._context

    async def start_conversation(self) -> bool:
        """
        Start conversation mode (skip wake word).

        Returns:
            True if conversation started successfully
        """
        if self.is_active:
            logger.warning("Conversation already active")
            return False

        self._context = ConversationContext(
            session_id=f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}", started_at=datetime.now()
        )

        self._state = ConversationState.LISTENING
        self._start_timeout()

        logger.info("Conversation started", session_id=self._context.session_id)

        # Notify callbacks
        if "on_start" in self._callbacks:
            await self._callbacks["on_start"]()

        return True

    async def end_conversation(self, reason: str = "user_ended") -> bool:
        """
        End conversation mode.

        Args:
            reason: Why conversation ended

        Returns:
            True if conversation was active and ended
        """
        if not self.is_active:
            return False

        session_id = self._context.session_id if self._context else "unknown"
        turns = self._context.turns if self._context else 0

        self._cancel_timeout()
        self._state = ConversationState.IDLE
        self._context = None

        logger.info("Conversation ended", session_id=session_id, reason=reason, total_turns=turns)

        # Notify callbacks
        if "on_end" in self._callbacks:
            await self._callbacks["on_end"](reason)

        return True

    async def process_user_input(self, text: str) -> str | None:
        """
        Process user speech during conversation.

        Args:
            text: Transcribed user speech

        Returns:
            Assistant response or None
        """
        if not self.is_active or not self._context:
            logger.warning("No active conversation")
            return None

        # Check for end phrases
        if self._is_end_phrase(text):
            await self.end_conversation(reason="user_said_goodbye")
            return "Goodbye! Let me know if you need anything else."

        # Update state and context
        self._state = ConversationState.PROCESSING
        self._context.add_user_message(text)
        self._reset_timeout()

        try:
            # Get response from callback
            if self.on_user_speech:
                self._state = ConversationState.RESPONDING
                response = await self.on_user_speech(text)
            else:
                response = "I heard you say: " + text

            self._context.add_assistant_message(response)

            # Check turn limit
            if self._context.turns >= self.max_turns:
                await self.end_conversation(reason="max_turns_reached")
                response += (
                    " (Note: We've reached the conversation limit. Starting fresh next time.)"
                )
            else:
                self._state = ConversationState.LISTENING

            return response

        except Exception as e:
            logger.error(f"Error processing input: {e}")
            self._state = ConversationState.LISTENING
            return "I had trouble processing that. Could you repeat?"

    def _is_end_phrase(self, text: str) -> bool:
        """Check if text signals end of conversation."""
        end_phrases = [
            "goodbye",
            "bye",
            "tchau",
            "adeus",
            "end conversation",
            "stop talking",
            "that's all",
            "nevermind",
            "cancel",
        ]
        text_lower = text.lower().strip()
        return any(phrase in text_lower for phrase in end_phrases)

    def _start_timeout(self):
        """Start inactivity timeout."""
        self._cancel_timeout()
        self._timeout_task = asyncio.create_task(self._timeout_handler())

    def _reset_timeout(self):
        """Reset inactivity timeout."""
        self._start_timeout()

    def _cancel_timeout(self):
        """Cancel inactivity timeout."""
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None

    async def _timeout_handler(self):
        """Handle conversation timeout."""
        try:
            await asyncio.sleep(self.timeout_seconds)

            if self.is_active:
                logger.info("Conversation timed out due to inactivity")
                await self.end_conversation(reason="timeout")

        except asyncio.CancelledError:
            pass

    def on(self, event: str, callback: Callable):
        """Register event callback."""
        self._callbacks[event] = callback

    def get_status(self) -> dict:
        """Get conversation status."""
        return {
            "state": self._state.value,
            "is_active": self.is_active,
            "session_id": self._context.session_id if self._context else None,
            "turns": self._context.turns if self._context else 0,
            "started_at": self._context.started_at.isoformat() if self._context else None,
            "last_activity": self._context.last_activity.isoformat() if self._context else None,
        }


# Singleton instance
_handler_instance: ConversationHandler | None = None


def get_conversation_handler() -> ConversationHandler:
    """Get singleton conversation handler."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = ConversationHandler()
    return _handler_instance
