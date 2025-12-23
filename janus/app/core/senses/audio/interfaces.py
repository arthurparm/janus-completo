from abc import ABC, abstractmethod
from typing import Optional, Any

class STTProvider(ABC):
    """
    Abstract Base Class for Speech-to-Text Providers.
    """
    @abstractmethod
    async def listen(self) -> str:
        """
        Listens to the microphone and returns the transcribed text.
        Should handle silence detection and ambient noise adjustment.
        """
        pass

class TTSProvider(ABC):
    """
    Abstract Base Class for Text-to-Speech Providers.
    """
    @abstractmethod
    async def speak(self, text: str) -> None:
        """
        Converts text to speech and plays it via the audio output.
        """
        pass
