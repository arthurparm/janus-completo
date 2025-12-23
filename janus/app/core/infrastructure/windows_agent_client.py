"""
WindowsAgentClient - HTTP Client for Windows Agent
===================================================

Allows Janus (in Docker) to communicate with the Windows Agent
running on the host machine.
"""

import asyncio
import aiohttp
import structlog
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# Default URL for Windows Agent (from Docker's perspective)
WINDOWS_AGENT_URL = "http://host.docker.internal:5001"


@dataclass 
class ScreenshotResult:
    """Result from screenshot request."""
    success: bool
    image_b64: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    source: Optional[str] = None
    error: Optional[str] = None


class WindowsAgentClient:
    """
    HTTP client for communicating with Windows Agent.
    
    The Windows Agent runs on the host machine and provides
    OS-level capabilities that aren't available inside Docker.
    """
    
    def __init__(self, base_url: str = WINDOWS_AGENT_URL, timeout: int = 10):
        """
        Initialize client.
        
        Args:
            base_url: URL of the Windows Agent
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._available: Optional[bool] = None
        
        logger.info("WindowsAgentClient initialized", base_url=base_url)
    
    async def is_available(self) -> bool:
        """Check if Windows Agent is running."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    self._available = response.status == 200
                    return self._available
        except Exception:
            self._available = False
            return False
    
    async def capture_screenshot(
        self,
        mode: str = "active",
        max_width: int = 800,
        quality: int = 85
    ) -> ScreenshotResult:
        """
        Capture screenshot via Windows Agent.
        
        Args:
            mode: "active" for active window, "full" for entire screen
            max_width: Maximum width (auto-scales)
            quality: JPEG quality (1-100)
            
        Returns:
            ScreenshotResult with base64 image
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = {
                    "mode": mode,
                    "max_width": max_width,
                    "quality": quality
                }
                async with session.post(
                    f"{self.base_url}/screenshot",
                    json=payload
                ) as response:
                    data = await response.json()
                    return ScreenshotResult(**data)
                    
        except aiohttp.ClientError as e:
            return ScreenshotResult(
                success=False,
                error=f"Connection error: {e}"
            )
        except Exception as e:
            return ScreenshotResult(
                success=False,
                error=str(e)
            )
    
    async def notify(
        self,
        title: str,
        message: str,
        sound: bool = True
    ) -> bool:
        """
        Send desktop notification via Windows Agent.
        
        Args:
            title: Notification title
            message: Notification body
            sound: Play notification sound
            
        Returns:
            True if notification was sent
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = {
                    "title": title,
                    "message": message,
                    "sound": sound
                }
                async with session.post(
                    f"{self.base_url}/notify",
                    json=payload
                ) as response:
                    data = await response.json()
                    return data.get("success", False)
                    
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def speak(self, text: str, rate: int = 150) -> bool:
        """
        Speak text using Windows TTS.
        
        Args:
            text: Text to speak
            rate: Words per minute (50-300)
            
        Returns:
            True if speech completed
        """
        try:
            # Longer timeout for speech
            speech_timeout = aiohttp.ClientTimeout(total=60)
            
            async with aiohttp.ClientSession(timeout=speech_timeout) as session:
                payload = {"text": text, "rate": rate}
                async with session.post(
                    f"{self.base_url}/speak",
                    json=payload
                ) as response:
                    data = await response.json()
                    return data.get("success", False)
                    
        except Exception as e:
            logger.error(f"Failed to speak: {e}")
            return False
    
    async def get_active_window_title(self) -> Optional[str]:
        """Get the title of the active window."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/window/title") as response:
                    data = await response.json()
                    if data.get("success"):
                        return data.get("title")
                    return None
        except Exception:
            return None
    
    async def get_status(self) -> Dict[str, Any]:
        """Get Windows Agent status."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/") as response:
                    return await response.json()
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}


# Singleton instance
_client_instance: Optional[WindowsAgentClient] = None


def get_windows_agent() -> WindowsAgentClient:
    """Get singleton Windows Agent client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = WindowsAgentClient()
    return _client_instance


async def is_windows_agent_available() -> bool:
    """Quick check if Windows Agent is running."""
    return await get_windows_agent().is_available()
