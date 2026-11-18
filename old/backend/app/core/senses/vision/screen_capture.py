"""
ScreenCaptureService - Lightweight Vision for Janus
====================================================

Captures screen content for visual context analysis.
Optimized for low resource usage with FullHD + Ultrawide monitors.
"""

import asyncio
import base64
import io
from dataclasses import dataclass
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)

# Optional imports - graceful fallback if not available
try:
    from PIL import Image, ImageGrab

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available. Screen capture disabled.")

try:
    import win32gui

    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("win32 libraries not available. Active window capture disabled.")


@dataclass
class ScreenCapture:
    """Represents a captured screen image."""

    image_b64: str
    width: int
    height: int
    source: str  # "full_screen", "active_window", "region"
    timestamp: datetime
    original_size: tuple[int, int]


class ScreenCaptureService:
    """
    Lightweight screen capture service.

    Features:
    - Capture active window only (not full screen)
    - Automatic downscaling to reduce LLM processing load
    - Base64 encoding for easy transmission
    """

    def __init__(self, max_width: int = 800, quality: int = 85):
        """
        Initialize screen capture service.

        Args:
            max_width: Maximum width for captured images (auto-scales)
            quality: JPEG quality (1-100)
        """
        self.max_width = max_width
        self.quality = quality
        self._enabled = PIL_AVAILABLE

        if not PIL_AVAILABLE:
            logger.warning("ScreenCaptureService disabled: PIL not available")
        else:
            logger.info("ScreenCaptureService initialized", max_width=max_width, quality=quality)

    async def capture_active_window(self) -> ScreenCapture | None:
        """
        Capture only the active (focused) window.

        This is much lighter than full screen capture and respects privacy
        by only capturing what the user is actively working on.

        Returns:
            ScreenCapture object or None if capture failed
        """
        if not self._enabled:
            logger.warning("Screen capture is disabled")
            return None

        try:
            return await asyncio.to_thread(self._capture_active_window_sync)
        except Exception as e:
            logger.error("log_error", message=f"Failed to capture active window: {e}")
            return None

    def _capture_active_window_sync(self) -> ScreenCapture | None:
        """Synchronous active window capture."""
        if not WIN32_AVAILABLE:
            # Fallback to full screen if win32 not available
            return self._capture_full_screen_sync()

        try:
            # Get active window handle
            hwnd = win32gui.GetForegroundWindow()

            if not hwnd:
                logger.warning("No active window found")
                return self._capture_full_screen_sync()

            # Get window rectangle
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                return self._capture_full_screen_sync()

            # Capture the window region
            img = ImageGrab.grab(bbox=(left, top, right, bottom))

            return self._process_image(img, "active_window")

        except Exception as e:
            logger.error("log_error", message=f"Active window capture failed: {e}")
            return self._capture_full_screen_sync()

    async def capture_full_screen(self) -> ScreenCapture | None:
        """
        Capture the entire screen.

        Warning: This can be resource-intensive with multiple monitors.
        Prefer capture_active_window() when possible.
        """
        if not self._enabled:
            return None

        try:
            return await asyncio.to_thread(self._capture_full_screen_sync)
        except Exception as e:
            logger.error("log_error", message=f"Failed to capture full screen: {e}")
            return None

    def _capture_full_screen_sync(self) -> ScreenCapture | None:
        """Synchronous full screen capture."""
        try:
            img = ImageGrab.grab()
            return self._process_image(img, "full_screen")
        except Exception as e:
            logger.error("log_error", message=f"Full screen capture failed: {e}")
            return None

    async def capture_region(self, x: int, y: int, width: int, height: int) -> ScreenCapture | None:
        """
        Capture a specific screen region.

        Args:
            x: Left coordinate
            y: Top coordinate
            width: Region width
            height: Region height
        """
        if not self._enabled:
            return None

        try:
            bbox = (x, y, x + width, y + height)
            img = await asyncio.to_thread(ImageGrab.grab, bbox=bbox)
            return self._process_image(img, "region")
        except Exception as e:
            logger.error("log_error", message=f"Failed to capture region: {e}")
            return None

    def _process_image(self, img: "Image.Image", source: str) -> ScreenCapture:
        """Process captured image: resize and encode."""
        original_size = img.size

        # Resize if wider than max_width
        if img.width > self.max_width:
            ratio = self.max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)

        # Convert to JPEG and base64 encode
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=self.quality)
        image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return ScreenCapture(
            image_b64=image_b64,
            width=img.width,
            height=img.height,
            source=source,
            timestamp=datetime.now(),
            original_size=original_size,
        )

    def is_available(self) -> bool:
        """Check if screen capture is available."""
        return self._enabled

    def enable(self):
        """Enable screen capture."""
        if PIL_AVAILABLE:
            self._enabled = True

    def disable(self):
        """Disable screen capture."""
        self._enabled = False


# Singleton instance
_capture_instance: ScreenCaptureService | None = None


def get_screen_capture() -> ScreenCaptureService:
    """Get singleton screen capture service."""
    global _capture_instance
    if _capture_instance is None:
        _capture_instance = ScreenCaptureService()
    return _capture_instance
