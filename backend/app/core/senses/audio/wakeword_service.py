import asyncio

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class WakeWordService:
    """
    Service for detecting wake words using 'openwakeword'.
    Runs locally and efficiently.
    """

    def __init__(self, models: list[str] = ["hey_jarvis"]):
        self.models = models
        self.oww_model = None
        self._available = False
        self._initialize()

    def _initialize(self):
        try:
            from openwakeword.model import Model

            # Download models if needed is handled by openwakeword usually,
            # but sometimes needs explicit download.
            # We'll rely on auto-download or pre-existence.
            self.oww_model = Model(self.models)
            self._available = True
            logger.info(f"WakeWord Service initialized. Models: {self.models}")
        except ImportError:
            logger.warning("openwakeword library not found. Wake Word detection disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize openwakeword: {e}")
            self._available = False

    async def wait_for_wake_word(self) -> bool:
        """
        Listens to the microphone continuously until a wake word is detected.
        Returns True when detected.
        """
        if not self._available:
            # If unavailable, we shouldn't block. We might return True to fallback to "Always Listening" or False to disable.
            # For now, let's return False so we don't spam STT.
            logger.debug("WakeWord unavailable.")
            await asyncio.sleep(1)  # Prevent busy loop
            return False

        # We need PyAudio to stream audio
        import importlib.util

        if importlib.util.find_spec("pyaudio") is None:
            logger.warning("pyaudio not found. Cannot listen for wake word.")
            await asyncio.sleep(1)
            return False

        formatted_models = ", ".join(self.models)
        logger.info(f"Waiting for wake word ({formatted_models})...")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._listen_loop_sync)

    def _listen_loop_sync(self) -> bool:
        import pyaudio

        CHUNK = 1280
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        p = pyaudio.PyAudio()
        stream = None

        try:
            stream = p.open(
                format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK
            )
        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            return False

        detected = False
        try:
            while True:
                # Get audio
                audio = np.frombuffer(stream.read(CHUNK), dtype=np.int16)

                # Feed to openwakeword
                # requires shape (N samples)
                prediction = self.oww_model.predict(audio)

                # Check predictions
                # prediction is a dict: {'key': score, ...}
                for model_name in self.models:
                    score = prediction.get(model_name, 0.0)
                    if score > 0.5:  # Threshold
                        logger.info(f"Wake Word Detected: {model_name} (Score: {score:.2f})")
                        detected = True
                        break

                if detected:
                    break

        except Exception as e:
            logger.error(f"Error in wake word loop: {e}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            p.terminate()

        return detected
