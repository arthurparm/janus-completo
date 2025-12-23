"""
Qdrant monitoring and recovery service for enhanced resilience.
"""
import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from app.core.memory.enhanced_circuit_breaker import circuit_breaker_manager, EnhancedCircuitBreaker
from app.core.memory.enhanced_qdrant_client import EnhancedQdrantClient

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for Qdrant failures."""
    IMMEDIATE = "immediate"
    GRADUAL = "gradual"
    CONSERVATIVE = "conservative"


@dataclass
class QdrantHealthStatus:
    """Qdrant health status information."""
    is_healthy: bool
    last_check: datetime
    consecutive_failures: int
    consecutive_successes: int
    average_response_time: float
    error_rate: float
    circuit_breaker_state: str
    recovery_recommendation: str


class QdrantMonitoringService:
    """Service for monitoring Qdrant health and managing recovery."""
    
    def __init__(self, 
                 qdrant_client: EnhancedQdrantClient,
                 check_interval: int = 30,
                 recovery_strategy: RecoveryStrategy = RecoveryStrategy.GRADUAL):
        """
        Initialize monitoring service.
        
        Args:
            qdrant_client: Enhanced Qdrant client
            check_interval: Health check interval in seconds
            recovery_strategy: Recovery strategy to use
        """
        self.qdrant_client = qdrant_client
        self.check_interval = check_interval
        self.recovery_strategy = recovery_strategy
        
        # Health tracking
        self._last_health_check: Optional[datetime] = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._response_times: list[float] = []
        self._error_count = 0
        self._total_checks = 0
        
        # Recovery tracking
        self._last_recovery_attempt: Optional[datetime] = None
        self._recovery_count = 0
        self._is_monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Circuit breaker reference
        self._circuit_breaker = qdrant_client.circuit_breaker
        
        logger.info(
            "qdrant_monitoring_service_initialized",
            check_interval=check_interval,
            recovery_strategy=recovery_strategy.value
        )
    
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        if self._is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("qdrant_monitoring_started")
    
    async def stop_monitoring(self):
        """Stop continuous health monitoring."""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("qdrant_monitoring_stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Starting Qdrant monitoring loop")
        
        while self._is_monitoring:
            try:
                await self._perform_health_check()
                
                # Auto-recovery logic
                if self._should_attempt_recovery():
                    await self._attempt_recovery()
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error("Error in monitoring loop", exc_info=e)
                await asyncio.sleep(self.check_interval)
    
    async def _perform_health_check(self):
        """Perform a single health check."""
        self._total_checks += 1
        start_time = time.time()
        
        try:
            # Use circuit breaker for health check
            async def health_check_operation():
                return await self.qdrant_client.health_check()
            
            is_healthy = await self._circuit_breaker.call_async(health_check_operation)
            
            response_time = time.time() - start_time
            self._response_times.append(response_time)
            
            # Keep only last 100 response times
            if len(self._response_times) > 100:
                self._response_times = self._response_times[-100:]
            
            if is_healthy:
                self._consecutive_successes += 1
                self._consecutive_failures = 0
                logger.debug(
                    "qdrant_health_check_success",
                    response_time=response_time,
                    consecutive_successes=self._consecutive_successes
                )
            else:
                self._consecutive_failures += 1
                self._consecutive_successes = 0
                self._error_count += 1
                logger.warning(
                    "qdrant_health_check_failed",
                    response_time=response_time,
                    consecutive_failures=self._consecutive_failures
                )
            
            self._last_health_check = datetime.now()
            
        except Exception as e:
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._error_count += 1
            response_time = time.time() - start_time
            
            logger.error(
                "qdrant_health_check_exception",
                response_time=response_time,
                consecutive_failures=self._consecutive_failures,
                error=str(e)
            )
            
            self._last_health_check = datetime.now()
    
    def _should_attempt_recovery(self) -> bool:
        """Determine if recovery should be attempted."""
        # Don't attempt recovery too frequently
        if (self._last_recovery_attempt and 
            datetime.now() - self._last_recovery_attempt < timedelta(minutes=5)):
            return False
        
        # Attempt recovery if circuit breaker is open
        if self._circuit_breaker.is_open():
            return True
        
        # Attempt recovery if we have consecutive failures
        if self._consecutive_failures >= 3:
            return True
        
        return False
    
    async def _attempt_recovery(self):
        """Attempt to recover Qdrant connection."""
        logger.info("Attempting Qdrant recovery")
        self._last_recovery_attempt = datetime.now()
        self._recovery_count += 1
        
        try:
            # Reset circuit breaker
            self._circuit_breaker.reset()
            logger.info("Circuit breaker reset during recovery")
            
            # Perform health check to verify recovery
            is_healthy = await self.qdrant_client.health_check()
            
            if is_healthy:
                self._consecutive_failures = 0
                self._consecutive_successes = 1
                logger.info("Qdrant recovery successful")
            else:
                logger.warning("Qdrant recovery failed - still unhealthy")
                
        except Exception as e:
            logger.error("Qdrant recovery failed with exception", exc_info=e)
    
    def get_health_status(self) -> QdrantHealthStatus:
        """Get current health status."""
        if not self._response_times:
            avg_response_time = 0.0
        else:
            avg_response_time = sum(self._response_times) / len(self._response_times)
        
        error_rate = self._error_count / max(self._total_checks, 1)
        
        # Determine recovery recommendation
        if self._circuit_breaker.is_open():
            recovery_recommendation = "Circuit breaker is open - manual intervention required"
        elif self._consecutive_failures > 5:
            recovery_recommendation = "Multiple consecutive failures - check Qdrant service"
        elif error_rate > 0.5:
            recovery_recommendation = "High error rate - investigate Qdrant performance"
        elif avg_response_time > 10.0:
            recovery_recommendation = "High response times - consider scaling Qdrant"
        else:
            recovery_recommendation = "System appears healthy"
        
        return QdrantHealthStatus(
            is_healthy=self._consecutive_successes > 0 and not self._circuit_breaker.is_open(),
            last_check=self._last_health_check or datetime.now(),
            consecutive_failures=self._consecutive_failures,
            consecutive_successes=self._consecutive_successes,
            average_response_time=avg_response_time,
            error_rate=error_rate,
            circuit_breaker_state=self._circuit_breaker.state.value,
            recovery_recommendation=recovery_recommendation
        )
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed monitoring metrics."""
        health_status = self.get_health_status()
        circuit_breaker_metrics = self._circuit_breaker.get_health_status()
        
        return {
            "health_status": {
                "is_healthy": health_status.is_healthy,
                "consecutive_failures": health_status.consecutive_failures,
                "consecutive_successes": health_status.consecutive_successes,
                "average_response_time": health_status.average_response_time,
                "error_rate": health_status.error_rate,
                "recovery_recommendation": health_status.recovery_recommendation,
            },
            "circuit_breaker": circuit_breaker_metrics,
            "monitoring_stats": {
                "total_checks": self._total_checks,
                "error_count": self._error_count,
                "recovery_count": self._recovery_count,
                "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
                "last_recovery_attempt": self._last_recovery_attempt.isoformat() if self._last_recovery_attempt else None,
                "check_interval": self.check_interval,
                "is_monitoring": self._is_monitoring,
            },
            "response_times": {
                "recent": self._response_times[-20:],  # Last 20 response times
                "average": sum(self._response_times) / len(self._response_times) if self._response_times else 0,
                "min": min(self._response_times) if self._response_times else 0,
                "max": max(self._response_times) if self._response_times else 0,
            }
        }


# Global monitoring service instance
_qdrant_monitoring_service: Optional[QdrantMonitoringService] = None


async def initialize_qdrant_monitoring(qdrant_client: EnhancedQdrantClient,
                                        check_interval: int = 30,
                                        recovery_strategy: RecoveryStrategy = RecoveryStrategy.GRADUAL) -> QdrantMonitoringService:
    """Initialize and start Qdrant monitoring service."""
    global _qdrant_monitoring_service
    
    if _qdrant_monitoring_service is not None:
        logger.warning("Qdrant monitoring service already initialized")
        return _qdrant_monitoring_service
    
    _qdrant_monitoring_service = QdrantMonitoringService(
        qdrant_client=qdrant_client,
        check_interval=check_interval,
        recovery_strategy=recovery_strategy
    )
    
    await _qdrant_monitoring_service.start_monitoring()
    return _qdrant_monitoring_service


async def get_qdrant_monitoring_service() -> Optional[QdrantMonitoringService]:
    """Get the global Qdrant monitoring service instance."""
    return _qdrant_monitoring_service


async def stop_qdrant_monitoring():
    """Stop Qdrant monitoring service."""
    global _qdrant_monitoring_service
    
    if _qdrant_monitoring_service is not None:
        await _qdrant_monitoring_service.stop_monitoring()
        _qdrant_monitoring_service = None
        logger.info("Qdrant monitoring service stopped")