"""
DesktopNotifier - Proactive Desktop Notifications for Janus
============================================================

Sends desktop notifications to keep user informed of important events.
Uses Windows native toast notifications via PowerShell (no external deps).
"""

import asyncio
import subprocess
import structlog
from typing import Optional
from enum import Enum
from datetime import datetime
from prometheus_client import Counter

logger = structlog.get_logger(__name__)

# Prometheus metrics
NOTIFICATIONS_SENT = Counter(
    "desktop_notifications_total",
    "Total desktop notifications sent",
    ["urgency", "status"]
)


class NotificationUrgency(Enum):
    """Notification urgency levels."""
    LOW = "low"           # Informational
    NORMAL = "normal"     # Standard notification
    HIGH = "high"         # Important, requires attention
    CRITICAL = "critical" # Critical alert


class DesktopNotifier:
    """
    Desktop notification service for Windows.
    
    Uses PowerShell BurntToast module or falls back to basic toast.
    """
    
    def __init__(self, app_name: str = "Janus AI"):
        self.app_name = app_name
        self._enabled = True
        self._notification_history: list = []
        logger.info("DesktopNotifier initialized", app_name=app_name)
    
    async def notify(
        self,
        title: str,
        message: str,
        urgency: NotificationUrgency = NotificationUrgency.NORMAL,
        sound: bool = True
    ) -> bool:
        """
        Send a desktop notification.
        
        Args:
            title: Notification title
            message: Notification body text
            urgency: Urgency level
            sound: Play notification sound
            
        Returns:
            True if notification was sent successfully
        """
        if not self._enabled:
            logger.debug("Notifications disabled, skipping")
            return False
        
        try:
            # Try Windows PowerShell toast
            success = await self._send_windows_toast(title, message, sound)
            
            if success:
                NOTIFICATIONS_SENT.labels(urgency=urgency.value, status="success").inc()
                self._notification_history.append({
                    "title": title,
                    "message": message,
                    "urgency": urgency.value,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(
                    "Notification sent",
                    title=title,
                    urgency=urgency.value
                )
            else:
                NOTIFICATIONS_SENT.labels(urgency=urgency.value, status="fallback").inc()
                # Fallback: just log it
                logger.warning(
                    f"NOTIFICATION: {title} - {message}",
                    urgency=urgency.value
                )
            
            return success
            
        except Exception as e:
            NOTIFICATIONS_SENT.labels(urgency=urgency.value, status="error").inc()
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def _send_windows_toast(self, title: str, message: str, sound: bool) -> bool:
        """Send notification using Windows PowerShell."""
        try:
            # Escape quotes for PowerShell
            title_escaped = title.replace('"', '`"').replace("'", "`'")
            message_escaped = message.replace('"', '`"').replace("'", "`'")
            
            # PowerShell script for Windows toast notification
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
            
            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title_escaped}</text>
                        <text id="2">{message_escaped}</text>
                    </binding>
                </visual>
            </toast>
"@
            
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.app_name}")
            $notifier.Show($toast)
            '''
            
            # Run PowerShell asynchronously
            process = await asyncio.create_subprocess_exec(
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=5.0
            )
            
            return process.returncode == 0
            
        except asyncio.TimeoutError:
            logger.warning("Toast notification timed out")
            return False
        except FileNotFoundError:
            logger.warning("PowerShell not available")
            return False
        except Exception as e:
            logger.debug(f"Windows toast failed: {e}")
            return False
    
    async def notify_task_complete(self, task_name: str, result: str = "success") -> bool:
        """Notify when a task completes."""
        icon = "✅" if result == "success" else "❌"
        return await self.notify(
            title=f"{icon} Task Complete",
            message=f"{task_name}",
            urgency=NotificationUrgency.NORMAL if result == "success" else NotificationUrgency.HIGH
        )
    
    async def notify_error(self, error_message: str) -> bool:
        """Notify about an error."""
        return await self.notify(
            title="⚠️ Janus Alert",
            message=error_message,
            urgency=NotificationUrgency.HIGH
        )
    
    async def notify_reminder(self, reminder: str) -> bool:
        """Send a reminder notification."""
        return await self.notify(
            title="🔔 Reminder",
            message=reminder,
            urgency=NotificationUrgency.NORMAL
        )
    
    async def notify_system_status(self, status: str) -> bool:
        """Notify about system status changes."""
        return await self.notify(
            title="🤖 Janus Status",
            message=status,
            urgency=NotificationUrgency.LOW,
            sound=False
        )
    
    def enable(self):
        """Enable notifications."""
        self._enabled = True
        logger.info("Desktop notifications enabled")
    
    def disable(self):
        """Disable notifications."""
        self._enabled = False
        logger.info("Desktop notifications disabled")
    
    def get_history(self, limit: int = 10) -> list:
        """Get recent notification history."""
        return self._notification_history[-limit:]
    
    def clear_history(self):
        """Clear notification history."""
        self._notification_history = []


# Singleton instance
_notifier_instance: Optional[DesktopNotifier] = None


def get_notifier() -> DesktopNotifier:
    """Get singleton notifier instance."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = DesktopNotifier()
    return _notifier_instance


async def quick_notify(title: str, message: str) -> bool:
    """Quick helper to send a notification."""
    notifier = get_notifier()
    return await notifier.notify(title, message)
