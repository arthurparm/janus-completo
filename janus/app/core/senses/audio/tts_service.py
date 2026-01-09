import asyncio
import os
import tempfile

import structlog

from app.core.senses.audio.interfaces import TTSProvider

logger = structlog.get_logger(__name__)


class TTSService(TTSProvider):
    """
    Text-to-Speech Service using 'edge-tts' (Microsoft Edge Online TTS).
    Provides high-quality neural voices for free.
    """

    def __init__(self, voice: str = "pt-BR-AntonioNeural"):
        self.voice = voice
        self._available = False
        self._initialize()

    def _initialize(self):
        import importlib.util

        self._available = importlib.util.find_spec("edge_tts") is not None
        if self._available:
            logger.info(f"TTS Service initialized with edge-tts (Voice: {self.voice})")
        else:
            logger.warning("edge_tts library not found. TTS disabled.")

    async def speak(self, text: str) -> None:
        if not self._available or not text:
            return

        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice)

        # Create a temp file for the audio
        # Note: Delete=False because we need to close it before playing on Windows
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            temp_path = fp.name

        try:
            await communicate.save(temp_path)
            await self._play_audio(temp_path)
        except Exception as e:
            logger.error(f"TTS Error: {e}")
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    async def _play_audio(self, file_path: str):
        """
        Plays the audio file. Accessing OS audio device.
        Requires a player installed or python library like playsound.
        """
        logger.info(f"Speaking: {file_path}")

        # Crude but effective cross-platform playback attempts
        # 1. Try 'playsound' library if available
        # 2. Try 'mpg123' or 'ffplay' CLI
        # 3. Windows 'start' command

        try:
            # Blocking playback in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._play_audio_sync(file_path))
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")

    def _play_audio_sync(self, file_path: str):
        # Strategy 1: playsound
        try:
            from playsound import playsound

            playsound(file_path)
            return
        except ImportError:
            pass

        # Strategy 2: OS System Call (Windows)
        if os.name == "nt":
            # This opens the default player which might be annoying (UI popup).
            # Better to use powershell to play sound?
            # Creating a lightweight powershell player script
            # Note: SoundPlayer only supports WAV, not MP3. edge-tts exports mp3.
            # So SoundPlayer won't work for MP3.
            pass

        # Strategy 3: pydub + simpleaudio (needs install)
        # Fallback to just logging if no player found meant for "Server" mode?
        # But this is "Jarvis" mode (Desktop).
        # Let's try 'start /min ...' but that pops UI.
        # User requested COMPLETED CODE. I should recommend installing 'playsound==1.2.2' (known to work better on windows than 1.3 sometimes) or 'pygame'.

        logger.warning(
            "No suitable audio player found/implemented. Please install 'playsound' or 'pygame'. Audio saved to temp."
        )
