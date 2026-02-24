import asyncio

import structlog

from app.core.senses.audio.interfaces import STTProvider

logger = structlog.get_logger(__name__)


class STTService(STTProvider):
    """
    Speech-to-Text Service using the 'SpeechRecognition' library.
    Supports Google Web Speech API (default) and others.
    """

    def __init__(self):
        self.recognizer = None
        self.microphone = None
        self._available = False
        self._initialize()

    @property
    def is_available(self) -> bool:
        return self._available

    def _initialize(self):
        try:
            import speech_recognition as sr

            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self._available = True
            logger.info("STT Service initialized with SpeechRecognition.")
        except ImportError:
            logger.warning("speech_recognition library not found. STT disabled.")
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to initialize microphone: {e}. STT disabled.")

    async def listen(self) -> str:
        if not self._available:
            logger.warning("STT unavailable. Cannot listen.")
            return ""

        loop = asyncio.get_event_loop()

        try:
            # Run blocking audio I/O in executor
            text = await loop.run_in_executor(None, self._listen_sync)
            return text
        except Exception as e:
            logger.error("log_error", message=f"Error during listening: {e}")
            return ""

    def _listen_sync(self) -> str:
        import speech_recognition as sr

        with self.microphone as source:
            logger.info("Listening... (adjusting for ambient noise)")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("Listening... (ready)")
            try:
                # listen() blocks until silence is detected after speech
                audio = self.recognizer.listen(source, timeout=5.0, phrase_time_limit=10.0)
            except sr.WaitTimeoutError:
                logger.debug("Listening timed out (silence).")
                return ""

        try:
            logger.info("Transcribing...")
            # recognize_google is free and works well for general commands
            # language='pt-BR' can be made configurable
            text = self.recognizer.recognize_google(audio, language="pt-BR")
            logger.info("log_info", message=f"Heard: {text}")
            return text
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error("log_error", message=f"Could not request results from Google Speech Recognition service; {e}")
            return ""
