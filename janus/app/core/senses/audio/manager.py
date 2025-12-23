import structlog
import asyncio
from typing import Optional

from app.core.senses.audio.interfaces import STTProvider, TTSProvider
from app.core.senses.audio.stt_service import STTService
from app.core.senses.audio.tts_service import TTSService
from app.core.senses.audio.wakeword_service import WakeWordService

logger = structlog.get_logger(__name__)

class VoiceManager:
    """
    The High-Level Manager for Voice Interaction (Hearing & Speaking).
    Integrates STT, TTS, and WakeWord services.
    """
    def __init__(self):
        self.stt: Optional[STTProvider] = None
        self.tts: Optional[TTSProvider] = None
        self.wakeword: Optional[WakeWordService] = None
        self._enabled = False
        
        # Resilience
        self._failure_count = 0
        self._max_failures = 5
        self._circuit_open = False
        self._last_failure_time = 0
        self._recovery_timeout = 60 # seconds

    def initialize(self):
        """
        Initializes the subsystems. 
        Exceptions are caught to prevent crashing the Kernel if audio isn't available.
        """
        try:
            self.stt = STTService()
            self.tts = TTSService()
            self.wakeword = WakeWordService(models=["hey_jarvis"]) # Placeholder for "Janus"
            self._enabled = True
            logger.info("Voice Manager initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Voice Manager: {e}")
            self._enabled = False

    def _check_circuit(self) -> bool:
        if not self._enabled:
            return False
            
        if self._circuit_open:
            import time
            if time.time() - self._last_failure_time > self._recovery_timeout:
                self._circuit_open = False
                self._failure_count = 0
                logger.info("Voice Circuit Recovery: Attempting to re-enable voice.")
                return True
            else:
                return False
        return True

    def _record_failure(self, error: Exception):
        import time
        self._failure_count += 1
        self._last_failure_time = time.time()
        logger.warning(f"Voice Failure ({self._failure_count}/{self._max_failures}): {error}")
        
        if self._failure_count >= self._max_failures:
            self._circuit_open = True
            logger.error("Voice Circuit Breaker TRIPPED. Voice disabled for 60s.")

    async def speak(self, text: str):
        if not self._check_circuit() or not self.tts:
            return

        try:
            await self.tts.speak(text)
            self._failure_count = 0 # Reset on success? Or slowly decay? Reset for now.
        except Exception as e:
            self._record_failure(e)

    async def listen(self) -> str:
        """
        Active listening (after wake word).
        """
        if not self._check_circuit() or not self.stt:
            return ""
        
        try:
            result = await self.stt.listen()
            self._failure_count = 0
            return result
        except Exception as e:
            self._record_failure(e)
            return ""

    async def wait_for_wake_word(self) -> bool:
        """
        Passive listening for wake word.
        """
        if not self._check_circuit() or not self.wakeword:
            return False
        
        try:
            result = await self.wakeword.wait_for_wake_word()
            # If successful (even if False/timeout), implies hardware is working?
            # wait_for_wake_word usually loops. If it returns False, it might be timeout or error caught inside.
            # If it throws, we catch here.
            
            # Note: We rely on wake_word service ensuring it doesn't crash on simple silence.
            # But if mic is unplugged, it might crash.
            self._failure_count = 0
            return result
        except Exception as e:
            self._record_failure(e)
            return False
