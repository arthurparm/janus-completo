"""
WindowsAgentClient - HTTP Client for Windows Agent
===================================================

Allows Janus (in Docker) to communicate with the Windows Agent
running on the host machine.
"""

from dataclasses import dataclass
from typing import Any

import aiohttp
import structlog

from app.core.security.egress_policy import enforce_worker_http_egress

logger = structlog.get_logger(__name__)

# Default URL for Windows Agent (from Docker's perspective)
WINDOWS_AGENT_URL = "http://host.docker.internal:5001"


@dataclass
class ScreenshotResult:
    """Result from screenshot request."""

    success: bool
    image_b64: str | None = None
    width: int | None = None
    height: int | None = None
    source: str | None = None
    error: str | None = None


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
        self._available: bool | None = None

        logger.info("WindowsAgentClient initialized", base_url=base_url)

    async def is_available(self) -> bool:
        """Check if Windows Agent is running."""
        try:
            health_url = f"{self.base_url}/health"
            allowed_url = enforce_worker_http_egress(health_url, tool="windows_agent_client")
            if not allowed_url:
                self._available = False
                return False
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(allowed_url) as response:
                    self._available = response.status == 200
                    return self._available
        except Exception:
            self._available = False
            return False

    async def capture_screenshot(
        self, mode: str = "active", max_width: int = 800, quality: int = 85
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
            screenshot_url = f"{self.base_url}/screenshot"
            allowed_url = enforce_worker_http_egress(
                screenshot_url, tool="windows_agent_client"
            )
            if not allowed_url:
                return ScreenshotResult(success=False, error="Egress blocked by policy")
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = {"mode": mode, "max_width": max_width, "quality": quality}
                async with session.post(allowed_url, json=payload) as response:
                    data = await response.json()
                    return ScreenshotResult(**data)

        except aiohttp.ClientError as e:
            return ScreenshotResult(success=False, error=f"Connection error: {e}")
        except Exception as e:
            return ScreenshotResult(success=False, error=str(e))

    async def notify(self, title: str, message: str, sound: bool = True) -> bool:
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
            notify_url = f"{self.base_url}/notify"
            allowed_url = enforce_worker_http_egress(notify_url, tool="windows_agent_client")
            if not allowed_url:
                return False
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = {"title": title, "message": message, "sound": sound}
                async with session.post(allowed_url, json=payload) as response:
                    data = await response.json()
                    return data.get("success", False)

        except Exception as e:
            logger.error("log_error", message=f"Failed to send notification: {e}")
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
            speak_url = f"{self.base_url}/speak"
            allowed_url = enforce_worker_http_egress(speak_url, tool="windows_agent_client")
            if not allowed_url:
                return False

            async with aiohttp.ClientSession(timeout=speech_timeout) as session:
                payload = {"text": text, "rate": rate}
                async with session.post(allowed_url, json=payload) as response:
                    data = await response.json()
                    return data.get("success", False)

        except Exception as e:
            logger.error("log_error", message=f"Failed to speak: {e}")
            return False

    async def get_active_window_title(self) -> str | None:
        """Get the title of the active window."""
        try:
            title_url = f"{self.base_url}/window/title"
            allowed_url = enforce_worker_http_egress(title_url, tool="windows_agent_client")
            if not allowed_url:
                return None
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(allowed_url) as response:
                    data = await response.json()
                    if data.get("success"):
                        return data.get("title")
                    return None
        except Exception:
            return None

    async def get_status(self) -> dict[str, Any]:
        """Get Windows Agent status."""
        try:
            status_url = f"{self.base_url}/"
            allowed_url = enforce_worker_http_egress(status_url, tool="windows_agent_client")
            if not allowed_url:
                return {"status": "blocked", "error": "Egress blocked by policy"}
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(allowed_url) as response:
                    return await response.json()
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}


# Singleton instance
_client_instance: WindowsAgentClient | None = None


def get_windows_agent() -> WindowsAgentClient:
    """Get singleton Windows Agent client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = WindowsAgentClient()
    return _client_instance


async def is_windows_agent_available() -> bool:
    """Quick check if Windows Agent is running."""
    return await get_windows_agent().is_available()
