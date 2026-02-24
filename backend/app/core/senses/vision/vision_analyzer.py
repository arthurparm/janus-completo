"""
VisionAnalyzer - Screen Content Analysis for Janus
===================================================

Analyzes screen captures using multimodal LLM.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from app.core.senses.vision.screen_capture import (
    ScreenCapture,
    ScreenCaptureService,
    get_screen_capture,
)

logger = structlog.get_logger(__name__)


@dataclass
class VisionAnalysis:
    """Result of vision analysis."""

    description: str
    elements: list
    text_content: str | None
    confidence: float
    model_used: str


class VisionAnalyzer:
    """
    Analyzes screen content using multimodal LLM.

    Supports:
    - Natural language scene description
    - Text extraction (OCR-like)
    - Element detection
    """

    def __init__(self, screen_capture: ScreenCaptureService | None = None, model: str = "llava"):
        """
        Initialize VisionAnalyzer.

        Args:
            screen_capture: Screen capture service (uses singleton if None)
            model: Multimodal model to use (default: llava for Ollama)
        """
        self.screen_capture = screen_capture or get_screen_capture()
        self.model = model
        self._enabled = self.screen_capture.is_available()

        logger.info("VisionAnalyzer initialized", model=model)

    async def describe_screen(self) -> str | None:
        """
        Capture and describe what's on screen.

        Returns:
            Natural language description of screen content
        """
        if not self._enabled:
            return "Vision is not available."

        try:
            capture = await self.screen_capture.capture_active_window()
            if not capture:
                return "Failed to capture screen."

            return await self._analyze_with_llm(
                capture, prompt="Describe what you see in this screenshot. Be concise."
            )
        except Exception as e:
            logger.error("log_error", message=f"Failed to describe screen: {e}")
            return f"Error analyzing screen: {e}"

    async def find_element(self, description: str) -> dict[str, Any] | None:
        """
        Find a UI element matching the description.

        Args:
            description: Natural language description of element to find

        Returns:
            Dict with element info (location, type, text) or None
        """
        if not self._enabled:
            return None

        try:
            capture = await self.screen_capture.capture_active_window()
            if not capture:
                return None

            result = await self._analyze_with_llm(
                capture,
                prompt=f"Find the UI element that matches: '{description}'. "
                f"Describe its approximate location (top/middle/bottom, left/center/right) "
                f"and what it looks like.",
            )

            return {
                "description": result,
                "found": bool(result and "not found" not in result.lower()),
            }
        except Exception as e:
            logger.error("log_error", message=f"Failed to find element: {e}")
            return None

    async def extract_text(self) -> str | None:
        """
        Extract visible text from screen (OCR-like).

        Returns:
            Text content visible on screen
        """
        if not self._enabled:
            return None

        try:
            capture = await self.screen_capture.capture_active_window()
            if not capture:
                return None

            return await self._analyze_with_llm(
                capture,
                prompt="Read and transcribe all visible text in this screenshot. "
                "List the text you can see, organized by sections.",
            )
        except Exception as e:
            logger.error("log_error", message=f"Failed to extract text: {e}")
            return None

    async def analyze_context(self) -> dict[str, Any] | None:
        """
        Analyze screen for contextual understanding.

        Returns:
            Dict with application, task, and context info
        """
        if not self._enabled:
            return None

        try:
            capture = await self.screen_capture.capture_active_window()
            if not capture:
                return None

            analysis = await self._analyze_with_llm(
                capture,
                prompt="Analyze this screenshot and identify: "
                "1) What application is shown "
                "2) What task the user appears to be doing "
                "3) Any error messages or important notifications visible",
            )

            return {
                "analysis": analysis,
                "source": capture.source,
                "timestamp": capture.timestamp.isoformat(),
            }
        except Exception as e:
            logger.error("log_error", message=f"Failed to analyze context: {e}")
            return None

    async def _analyze_with_llm(self, capture: ScreenCapture, prompt: str) -> str:
        """
        Send image to multimodal LLM for analysis.

        Note: In production, this would use the LLM router with llava/gpt-4-vision.
        For now, returns a placeholder or uses Ollama directly.
        """
        try:
            # Try to use Ollama with llava
            from app.core.llm.factory import create_ollama_client

            client = await create_ollama_client(model=self.model)

            if client:
                # Ollama vision format
                response = await client.ainvoke(
                    [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{capture.image_b64}"
                                    },
                                },
                            ],
                        }
                    ]
                )

                return response.content if hasattr(response, "content") else str(response)

        except ImportError:
            pass
        except Exception as e:
            logger.warning("log_warning", message=f"LLM vision analysis failed: {e}")

        # Fallback: return basic info
        return (
            f"[Vision analysis placeholder - LLM not available]\n"
            f"Captured {capture.source}: {capture.width}x{capture.height}px "
            f"(original: {capture.original_size[0]}x{capture.original_size[1]})"
        )

    def is_available(self) -> bool:
        """Check if vision analysis is available."""
        return self._enabled


# Singleton instance
_analyzer_instance: VisionAnalyzer | None = None


def get_vision_analyzer() -> VisionAnalyzer:
    """Get singleton vision analyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = VisionAnalyzer()
    return _analyzer_instance
