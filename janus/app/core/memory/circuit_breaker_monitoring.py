"""
Circuit Breaker Monitoring and Alerting System

This module provides comprehensive monitoring, alerting, and analytics for circuit breaker
state changes and Qdrant service health.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.core.infrastructure.resilience import CircuitBreakerState

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class CircuitBreakerAlert:
    """Circuit breaker alert information."""

    alert_id: str
    severity: AlertSeverity
    circuit_breaker_name: str
    state_transition: str
    old_state: str
    new_state: str
    timestamp: datetime
    failure_count: int
    failure_threshold: int
    recovery_timeout: int
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None


@dataclass
class CircuitBreakerMetricsSnapshot:
    """Snapshot of circuit breaker metrics."""

    timestamp: datetime
    total_calls: int
    successful_calls: int
    failed_calls: int
    rejected_calls: int
    state: str
    failure_count: int
    average_response_time: float
    p95_response_time: float
    error_rate: float
    success_rate: float


class CircuitBreakerAlertManager:
    """Manages circuit breaker alerts and notifications."""

    def __init__(self):
        self.alerts: list[CircuitBreakerAlert] = []
        self.alert_handlers: list[Callable[[CircuitBreakerAlert], None]] = []
        self.alert_history: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        self._alert_counter = 0

        # Alert thresholds
        self.alert_thresholds = {
            "state_change": AlertSeverity.INFO,
            "circuit_open": AlertSeverity.CRITICAL,
            "circuit_half_open": AlertSeverity.WARNING,
            "high_failure_rate": AlertSeverity.WARNING,
            "extended_open_duration": AlertSeverity.EMERGENCY,
        }

        # Extended open duration threshold (30 minutes)
        self.extended_open_threshold = 1800  # seconds

        logger.info("circuit_breaker_alert_manager_initialized")

    def add_alert_handler(self, handler: Callable[[CircuitBreakerAlert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)

    def create_alert(
        self,
        circuit_breaker_name: str,
        old_state: CircuitBreakerState,
        new_state: CircuitBreakerState,
        failure_count: int,
        failure_threshold: int,
        recovery_timeout: int,
        context: dict[str, Any] | None = None,
    ) -> CircuitBreakerAlert:
        """Create a new circuit breaker alert."""

        self._alert_counter += 1
        alert_id = f"cb_alert_{int(time.time())}_{self._alert_counter}"

        # Determine severity based on state transition
        if new_state == CircuitBreakerState.OPEN:
            severity = self.alert_thresholds["circuit_open"]
            message = f"Circuit breaker '{circuit_breaker_name}' opened due to {failure_count}/{failure_threshold} failures"
        elif old_state == CircuitBreakerState.OPEN and new_state == CircuitBreakerState.HALF_OPEN:
            severity = self.alert_thresholds["circuit_half_open"]
            message = f"Circuit breaker '{circuit_breaker_name}' transitioning to half-open state"
        elif old_state == CircuitBreakerState.HALF_OPEN and new_state == CircuitBreakerState.CLOSED:
            severity = self.alert_thresholds["state_change"]
            message = f"Circuit breaker '{circuit_breaker_name}' successfully recovered and closed"
        else:
            severity = self.alert_thresholds["state_change"]
            message = f"Circuit breaker '{circuit_breaker_name}' state changed from {old_state.value} to {new_state.value}"

        alert = CircuitBreakerAlert(
            alert_id=alert_id,
            severity=severity,
            circuit_breaker_name=circuit_breaker_name,
            state_transition=f"{old_state.value} -> {new_state.value}",
            old_state=old_state.value,
            new_state=new_state.value,
            timestamp=datetime.now(),
            failure_count=failure_count,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            message=message,
            context=context or {},
        )

        self.alerts.append(alert)
        self.alert_history.append(alert)

        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}", exc_info=True)
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}", exc_info=True)

        logger.log(
            self._get_log_level(severity),
            f"Circuit Breaker Alert: {message} [alert_id={alert_id}, circuit_breaker={circuit_breaker_name}, transition={alert.state_transition}, failures={failure_count}/{failure_threshold}]",
        )

        return alert

    def _get_log_level(self, severity: AlertSeverity) -> int:
        """Convert alert severity to logging level."""
        mapping = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.ERROR,
            AlertSeverity.EMERGENCY: logging.CRITICAL,
        }
        return mapping.get(severity, logging.WARNING)

    def check_extended_open_duration(
        self, circuit_breaker_name: str, open_since: float
    ) -> CircuitBreakerAlert | None:
        """Check if circuit breaker has been open for extended duration."""
        open_duration = time.time() - open_since
        if open_duration > self.extended_open_threshold:
            return self.create_alert(
                circuit_breaker_name=circuit_breaker_name,
                old_state=CircuitBreakerState.OPEN,
                new_state=CircuitBreakerState.OPEN,  # Still open
                failure_count=0,  # Not applicable for this alert
                failure_threshold=0,  # Not applicable for this alert
                recovery_timeout=0,  # Not applicable for this alert
                context={
                    "open_duration_seconds": open_duration,
                    "open_duration_minutes": open_duration / 60,
                    "threshold_exceeded": True,
                    "recommendation": "Circuit breaker has been open for extended duration - manual intervention may be required",
                },
            )
        return None

    def get_active_alerts(self, severity: AlertSeverity | None = None) -> list[CircuitBreakerAlert]:
        """Get active (unacknowledged) alerts."""
        alerts = [alert for alert in self.alerts if not alert.acknowledged]
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        return alerts

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                logger.info(
                    f"Alert acknowledged: {alert.message} [alert_id={alert_id}, acknowledged_by={acknowledged_by}]"
                )
                return True
        return False

    def get_alert_statistics(self) -> dict[str, Any]:
        """Get alert statistics."""
        total_alerts = len(self.alerts)
        active_alerts = len(self.get_active_alerts())

        severity_counts = defaultdict(int)
        for alert in self.alerts:
            severity_counts[alert.severity.value] += 1

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "acknowledged_alerts": total_alerts - active_alerts,
            "severity_breakdown": dict(severity_counts),
            "recent_alerts": len(
                [a for a in self.alerts if (datetime.now() - a.timestamp).days <= 1]
            ),
        }


class CircuitBreakerAnalytics:
    """Analytics engine for circuit breaker performance."""

    def __init__(self, max_history_minutes: int = 60):
        self.max_history_minutes = max_history_minutes
        self.metrics_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.state_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.failure_patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)

        logger.info(
            "circuit_breaker_analytics_initialized", max_history_minutes=max_history_minutes
        )

    def record_metrics(self, circuit_breaker_name: str, metrics: CircuitBreakerMetricsSnapshot):
        """Record circuit breaker metrics."""
        self.metrics_history[circuit_breaker_name].append(metrics)

        # Clean old data
        cutoff_time = datetime.now() - timedelta(minutes=self.max_history_minutes)
        while (
            self.metrics_history[circuit_breaker_name]
            and self.metrics_history[circuit_breaker_name][0].timestamp < cutoff_time
        ):
            self.metrics_history[circuit_breaker_name].popleft()

    def record_state_change(
        self,
        circuit_breaker_name: str,
        old_state: CircuitBreakerState,
        new_state: CircuitBreakerState,
    ):
        """Record state change."""
        state_record = {
            "timestamp": datetime.now(),
            "old_state": old_state.value,
            "new_state": new_state.value,
        }
        self.state_history[circuit_breaker_name].append(state_record)

        # Clean old data
        cutoff_time = datetime.now() - timedelta(minutes=self.max_history_minutes)
        while (
            self.state_history[circuit_breaker_name]
            and self.state_history[circuit_breaker_name][0]["timestamp"] < cutoff_time
        ):
            self.state_history[circuit_breaker_name].popleft()

    def analyze_failure_patterns(self, circuit_breaker_name: str) -> dict[str, Any]:
        """Analyze failure patterns for a circuit breaker."""
        if circuit_breaker_name not in self.metrics_history:
            return {"error": "No metrics history available"}

        metrics = list(self.metrics_history[circuit_breaker_name])
        if not metrics:
            return {"error": "No metrics available"}

        # Calculate trends
        recent_metrics = [
            m for m in metrics if (datetime.now() - m.timestamp).total_seconds() / 60 <= 15
        ]
        older_metrics = [
            m for m in metrics if (datetime.now() - m.timestamp).total_seconds() / 60 > 15
        ]

        if not recent_metrics or not older_metrics:
            return {"error": "Insufficient data for trend analysis"}

        recent_avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        older_avg_error_rate = sum(m.error_rate for m in older_metrics) / len(older_metrics)

        recent_avg_response_time = sum(m.average_response_time for m in recent_metrics) / len(
            recent_metrics
        )
        older_avg_response_time = sum(m.average_response_time for m in older_metrics) / len(
            older_metrics
        )

        return {
            "error_rate_trend": "increasing"
            if recent_avg_error_rate > older_avg_error_rate
            else "decreasing",
            "error_rate_change": recent_avg_error_rate - older_avg_error_rate,
            "response_time_trend": "increasing"
            if recent_avg_response_time > older_avg_response_time
            else "decreasing",
            "response_time_change": recent_avg_response_time - older_avg_response_time,
            "recent_error_rate": recent_avg_error_rate,
            "older_error_rate": older_avg_error_rate,
            "recent_response_time": recent_avg_response_time,
            "older_response_time": older_avg_response_time,
            "recommendation": self._generate_recommendation(
                recent_avg_error_rate, recent_avg_response_time
            ),
        }

    def _generate_recommendation(self, error_rate: float, response_time: float) -> str:
        """Generate recommendation based on metrics."""
        if error_rate > 0.5:
            return "High error rate detected - investigate service health"
        elif response_time > 10.0:
            return "High response times detected - consider scaling or optimization"
        elif error_rate > 0.2:
            return "Moderate error rate - monitor closely"
        else:
            return "System appears healthy"

    def get_circuit_health_score(self, circuit_breaker_name: str) -> float:
        """Calculate health score for a circuit breaker."""
        if circuit_breaker_name not in self.metrics_history:
            return 0.0

        recent_metrics = [
            m
            for m in self.metrics_history[circuit_breaker_name]
            if (datetime.now() - m.timestamp).total_seconds() / 60 <= 5
        ]

        if not recent_metrics:
            return 50.0  # Default score when no recent data

        latest = recent_metrics[-1]

        # Base score calculation
        score = 100.0

        # Penalize based on error rate
        score -= latest.error_rate * 50

        # Penalize based on response time
        if latest.average_response_time > 5.0:
            score -= 20
        elif latest.average_response_time > 10.0:
            score -= 40

        # Penalize based on circuit breaker state
        if latest.state == CircuitBreakerState.OPEN.value:
            score -= 30
        elif latest.state == CircuitBreakerState.HALF_OPEN.value:
            score -= 10

        return max(0.0, score)


class CircuitBreakerMonitoringService:
    """Comprehensive monitoring service for circuit breakers."""

    def __init__(self):
        self.alert_manager = CircuitBreakerAlertManager()
        self.analytics = CircuitBreakerAnalytics()
        self.monitoring_enabled = True
        self._monitoring_task: asyncio.Task | None = None

        logger.info("circuit_breaker_monitoring_service_initialized")

    def enable_monitoring(self):
        """Enable monitoring."""
        self.monitoring_enabled = True
        logger.info("circuit_breaker_monitoring_enabled")

    def disable_monitoring(self):
        """Disable monitoring."""
        self.monitoring_enabled = False
        logger.info("circuit_breaker_monitoring_disabled")

    def record_state_change(
        self,
        circuit_breaker_name: str,
        old_state: CircuitBreakerState,
        new_state: CircuitBreakerState,
        failure_count: int,
        failure_threshold: int,
        recovery_timeout: int,
        open_since: float | None = None,
    ):
        """Record circuit breaker state change."""
        if not self.monitoring_enabled:
            return

        # Create alert for state change
        self.alert_manager.create_alert(
            circuit_breaker_name=circuit_breaker_name,
            old_state=old_state,
            new_state=new_state,
            failure_count=failure_count,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

        # Record state change in analytics
        self.analytics.record_state_change(circuit_breaker_name, old_state, new_state)

        # Check for extended open duration
        if new_state == CircuitBreakerState.OPEN and open_since:
            extended_alert = self.alert_manager.check_extended_open_duration(
                circuit_breaker_name, open_since
            )
            if extended_alert:
                logger.warning(
                    "Extended circuit breaker open duration detected",
                    circuit_breaker_name=circuit_breaker_name,
                    open_duration=time.time() - open_since,
                    alert_id=extended_alert.alert_id,
                )

    def record_metrics(self, circuit_breaker_name: str, metrics: CircuitBreakerMetricsSnapshot):
        """Record circuit breaker metrics."""
        if not self.monitoring_enabled:
            return

        self.analytics.record_metrics(circuit_breaker_name, metrics)

    def get_health_status(self, circuit_breaker_name: str) -> dict[str, Any]:
        """Get comprehensive health status for a circuit breaker."""
        health_score = self.analytics.get_circuit_health_score(circuit_breaker_name)
        failure_analysis = self.analytics.analyze_failure_patterns(circuit_breaker_name)
        active_alerts = self.alert_manager.get_active_alerts()

        return {
            "circuit_breaker_name": circuit_breaker_name,
            "health_score": health_score,
            "status": "healthy"
            if health_score > 70
            else "degraded"
            if health_score > 30
            else "critical",
            "failure_analysis": failure_analysis,
            "active_alerts": len(active_alerts),
            "critical_alerts": len(
                [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
            ),
            "last_check": datetime.now().isoformat(),
        }

    def get_system_overview(self) -> dict[str, Any]:
        """Get system-wide circuit breaker overview."""
        alert_stats = self.alert_manager.get_alert_statistics()

        return {
            "monitoring_enabled": self.monitoring_enabled,
            "alert_statistics": alert_stats,
            "total_circuit_breakers_monitored": len(self.analytics.metrics_history),
            "system_health": self._calculate_system_health(),
            "recommendations": self._generate_system_recommendations(),
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_system_health(self) -> str:
        """Calculate overall system health."""
        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]

        if len(critical_alerts) > 2:
            return "critical"
        elif len(critical_alerts) > 0 or len(active_alerts) > 5:
            return "degraded"
        else:
            return "healthy"

    def _generate_system_recommendations(self) -> list[str]:
        """Generate system-wide recommendations."""
        recommendations = []

        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]

        if critical_alerts:
            recommendations.append(
                f"Address {len(critical_alerts)} critical circuit breaker alerts"
            )

        if len(active_alerts) > 10:
            recommendations.append("High number of active alerts - investigate system stability")

        # Add more recommendations based on analytics
        for circuit_breaker_name in self.analytics.metrics_history.keys():
            health_score = self.analytics.get_circuit_health_score(circuit_breaker_name)
            if health_score < 30:
                recommendations.append(
                    f"Circuit breaker '{circuit_breaker_name}' has low health score ({health_score:.1f}) - immediate attention required"
                )

        if not recommendations:
            recommendations.append("System appears healthy - continue monitoring")

        return recommendations


# Global monitoring service instance
circuit_breaker_monitoring_service = CircuitBreakerMonitoringService()


def get_circuit_breaker_monitoring_service() -> CircuitBreakerMonitoringService:
    """Get the global circuit breaker monitoring service."""
    return circuit_breaker_monitoring_service


def setup_default_alert_handlers():
    """Setup default alert handlers."""
    monitoring_service = get_circuit_breaker_monitoring_service()

    # Console logging handler
    def console_alert_handler(alert: CircuitBreakerAlert):
        logger.log(
            monitoring_service.alert_manager._get_log_level(alert.severity),
            f"🚨 CIRCUIT BREAKER ALERT: {alert.message}",
            alert_id=alert.alert_id,
            severity=alert.severity.value,
            circuit_breaker=alert.circuit_breaker_name,
            state_transition=alert.state_transition,
            failure_count=alert.failure_count,
            failure_threshold=alert.failure_threshold,
        )

    monitoring_service.alert_manager.add_alert_handler(console_alert_handler)
    logger.info("Default circuit breaker alert handlers configured")


# Setup default handlers on import
setup_default_alert_handlers()
