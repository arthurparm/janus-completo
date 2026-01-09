"""
Janus Windows Agent
====================

Lightweight FastAPI service that runs on Windows host to provide
OS-level capabilities to the Docker container.

Features:
- Screen capture (active window or full screen)
- Desktop notifications (Windows toast)
- Text-to-Speech
- Speech-to-Text (microphone)

Usage:
    python windows_agent.py

Then in Docker, Janus calls http://host.docker.internal:5001
"""

import asyncio
import base64
import io
import subprocess
import sys
from datetime import datetime
from typing import Optional


# Check dependencies and install if needed
def check_dependencies():
    required = ['fastapi', 'uvicorn', 'pillow']
    missing = []

    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Installing missing packages: {missing}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing + ['--quiet'])

check_dependencies()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from PIL import Image, ImageGrab  # noqa: E402
from pydantic import BaseModel  # noqa: E402

# Optional: win32 for active window capture
try:
    import win32con  # noqa: F401
    import win32gui  # noqa: F401
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("Note: pywin32 not installed. Active window capture will use full screen.")
    print("To install: pip install pywin32")

app = FastAPI(
    title="Janus Windows Agent",
    description="Provides OS-level capabilities to Janus Docker container",
    version="1.0.0"
)

# Allow CORS from Docker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Models
# ============================================================================

class NotifyRequest(BaseModel):
    title: str
    message: str
    sound: bool = True

class SpeakRequest(BaseModel):
    text: str
    rate: int = 150  # Words per minute

class ScreenshotRequest(BaseModel):
    mode: str = "active"  # "active" or "full"
    max_width: int = 800
    quality: int = 85

class ScreenshotResponse(BaseModel):
    success: bool
    image_b64: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    source: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Janus Windows Agent",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "screenshot": True,
            "notify": True,
            "speak": True,
            "active_window": WIN32_AVAILABLE
        }
    }

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


@app.post("/screenshot", response_model=ScreenshotResponse)
async def capture_screenshot(request: ScreenshotRequest):
    """
    Capture screen and return as base64 JPEG.

    Modes:
    - "active": Capture only the active window (requires pywin32)
    - "full": Capture entire screen
    """
    try:
        if request.mode == "active" and WIN32_AVAILABLE:
            img = capture_active_window()
        else:
            img = ImageGrab.grab()

        if img is None:
            return ScreenshotResponse(success=False, error="Failed to capture screen")


        # Resize if needed
        if img.width > request.max_width:
            ratio = request.max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((request.max_width, new_height), Image.Resampling.LANCZOS)

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=request.quality)
        image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return ScreenshotResponse(
            success=True,
            image_b64=image_b64,
            width=img.width,
            height=img.height,
            source=request.mode
        )

    except Exception as e:
        return ScreenshotResponse(success=False, error=str(e))


def capture_active_window() -> Optional[Image.Image]:
    """Capture only the active window."""
    if not WIN32_AVAILABLE:
        return ImageGrab.grab()

    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ImageGrab.grab()

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            return ImageGrab.grab()

        return ImageGrab.grab(bbox=(left, top, right, bottom))

    except Exception:
        return ImageGrab.grab()


@app.post("/notify")
async def send_notification(request: NotifyRequest):
    """Send a Windows toast notification."""
    try:
        # PowerShell toast notification
        title = request.title.replace('"', '`"').replace("'", "`'")
        message = request.message.replace('"', '`"').replace("'", "`'")

        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
"@

        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Janus AI")
        $notifier.Show($toast)
        '''

        process = await asyncio.create_subprocess_exec(
            "powershell.exe",
            "-NoProfile", "-NonInteractive",
            "-Command", ps_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)

        return {
            "success": process.returncode == 0,
            "title": request.title,
            "message": request.message
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/speak")
async def speak_text(request: SpeakRequest):
    """
    Speak text using Windows SAPI (Text-to-Speech).
    """
    try:
        # PowerShell SAPI TTS
        text = request.text.replace('"', '`"').replace("'", "`'")

        ps_script = f'''
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.Rate = {(request.rate - 150) // 25}
        $synth.Speak("{text}")
        '''

        process = await asyncio.create_subprocess_exec(
            "powershell.exe",
            "-NoProfile", "-NonInteractive",
            "-Command", ps_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)

        return {
            "success": process.returncode == 0,
            "text": request.text
        }

    except asyncio.TimeoutError:
        return {"success": False, "error": "Speech timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/window/title")
async def get_active_window_title():
    """Get the title of the active window."""
    if not WIN32_AVAILABLE:
        return {"success": False, "error": "pywin32 not installed"}

    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return {"success": True, "title": title, "hwnd": hwnd}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/monitors")
async def get_monitors():
    """Get information about connected monitors."""
    try:
        # Use PIL to get screen size
        img = ImageGrab.grab()
        return {
            "success": True,
            "primary": {
                "width": img.width,
                "height": img.height
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("🤖 Janus Windows Agent")
    print("=" * 50)
    print("Starting on http://localhost:5001")
    print("Docker access: http://host.docker.internal:5001")
    print(f"Active window capture: {'✓' if WIN32_AVAILABLE else '✗ (install pywin32)'}")
    print("=" * 50)
    print("Press Ctrl+C to stop")
    print()

    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")
