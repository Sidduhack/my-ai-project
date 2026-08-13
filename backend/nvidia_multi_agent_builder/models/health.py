"""Model health tracking with HEALTHY/DEGRADED/COOLDOWN states."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from nvidia_multi_agent_builder.config.logging import get_logger

logger = get_logger(__name__)


class ModelHealthState(str, Enum):
    """Model health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"


@dataclass
class ModelHealth:
    """Health tracking for a specific model."""

    model_id: str  # format: "provider/model-id"
    provider: str

    # State
    state: ModelHealthState = ModelHealthState.HEALTHY

    # Counters
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    # Latency tracking
    total_latency_ms: float = 0.0
    request_count: int = 0
    recent_latencies: list[float] = field(default_factory=list)
    max_recent_latencies: int = 100

    # Error tracking
    timeout_count: int = 0
    error_count: int = 0
    last_error_type: str | None = None
    last_error_message: str | None = None

    # Timestamps
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None

    # Cooldown
    cooldown_until: datetime | None = None
    cooldown_duration_seconds: int = 300  # 5 minutes default

    # Thresholds
    failure_threshold: int = 3  # consecutive failures to trigger DEGRADED
    success_threshold: int = 2  # consecutive successes to recover from DEGRADED

    def record_success(self, latency_ms: float) -> None:
        """Record a successful request."""
        now = datetime.now(UTC)

        self.success_count += 1
        self.consecutive_failures = 0
        self.consecutive_successes += 1

        # Update latency
        self.total_latency_ms += latency_ms
        self.request_count += 1
        self.recent_latencies.append(latency_ms)
        if len(self.recent_latencies) > self.max_recent_latencies:
            self.recent_latencies.pop(0)

        self.last_success_at = now

        # State transitions
        if self.state == ModelHealthState.DEGRADED:
            if self.consecutive_successes >= self.success_threshold:
                self.state = ModelHealthState.HEALTHY
                logger.info("model_recovered", model_id=self.model_id, provider=self.provider)
        elif self.state == ModelHealthState.COOLDOWN:
            if self.cooldown_until and now >= self.cooldown_until:
                self.state = ModelHealthState.HEALTHY
                self.cooldown_until = None
                self.consecutive_failures = 0
                logger.info("model_cooldown_expired", model_id=self.model_id, provider=self.provider)

    def record_failure(
        self,
        error_type: str,
        error_message: str,
        is_timeout: bool = False,
    ) -> None:
        """Record a failed request."""
        now = datetime.now(UTC)

        self.failure_count += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.error_count += 1
        self.last_error_type = error_type
        self.last_error_message = error_message
        self.last_failure_at = now

        if is_timeout:
            self.timeout_count += 1

        # State transitions
        if self.state == ModelHealthState.HEALTHY:
            if self.consecutive_failures >= self.failure_threshold:
                self.state = ModelHealthState.DEGRADED
                self.cooldown_until = now
                logger.warning("model_degraded", model_id=self.model_id, provider=self.provider,
                             consecutive_failures=self.consecutive_failures)
        elif self.state == ModelHealthState.DEGRADED:
            # Another failure while degraded triggers cooldown
            self.state = ModelHealthState.COOLDOWN
            self.cooldown_until = now + timedelta(seconds=self.cooldown_duration_seconds)
            logger.warning("model_cooldown", model_id=self.model_id, provider=self.provider,
                         cooldown_until=self.cooldown_until)
        elif self.state == ModelHealthState.COOLDOWN:
            # Extend cooldown
            self.cooldown_until = now + timedelta(seconds=self.cooldown_duration_seconds)

    def is_available(self) -> bool:
        """Check if model is available for selection."""
        if self.state == ModelHealthState.HEALTHY:
            return True
        if self.state == ModelHealthState.DEGRADED:
            return True  # Still usable but lower priority
        if self.state == ModelHealthState.COOLDOWN:
            if self.cooldown_until and datetime.now(UTC) >= self.cooldown_until:
                return True
            return False
        return False

    def is_in_cooldown(self) -> bool:
        """Check if model is in active cooldown."""
        if self.state != ModelHealthState.COOLDOWN:
            return False
        if self.cooldown_until and datetime.now(UTC) < self.cooldown_until:
            return True
        return False

    def get_avg_latency(self) -> float:
        """Get average latency across all requests."""
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count

    def get_recent_avg_latency(self) -> float:
        """Get average latency of recent requests."""
        if not self.recent_latencies:
            return 0.0
        return sum(self.recent_latencies) / len(self.recent_latencies)

    def get_success_rate(self) -> float:
        """Get overall success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def get_recent_success_rate(self, window: int = 20) -> float:
        """Get recent success rate (requires tracking individual outcomes)."""
        # Simplified - would need outcome history for true recent rate
        return self.get_success_rate()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "state": self.state.value,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "avg_latency_ms": self.get_avg_latency(),
            "recent_avg_latency_ms": self.get_recent_avg_latency(),
            "timeout_count": self.timeout_count,
            "error_count": self.error_count,
            "last_error_type": self.last_error_type,
            "last_error_message": self.last_error_message,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "is_available": self.is_available(),
        }


class HealthTracker:
    """Central health tracking for all models."""

    def __init__(
        self,
        failure_threshold: int = 3,
        success_threshold: int = 2,
        cooldown_duration_seconds: int = 300,
    ):
        self._health: dict[str, ModelHealth] = {}
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.cooldown_duration_seconds = cooldown_duration_seconds

    def get_health(
        self,
        model_id: str,
        provider: str,
        failure_threshold: int | None = None,
        success_threshold: int | None = None,
    ) -> ModelHealth:
        """Get or create health tracker for model."""
        key = f"{provider}/{model_id}"
        if key not in self._health:
            self._health[key] = ModelHealth(
                model_id=model_id,
                provider=provider,
                failure_threshold=failure_threshold or self.failure_threshold,
                success_threshold=success_threshold or self.success_threshold,
                cooldown_duration_seconds=self.cooldown_duration_seconds,
            )
        return self._health[key]

    def record_success(self, model_id: str, provider: str, latency_ms: float) -> None:
        """Record successful request."""
        health = self.get_health(model_id, provider)
        health.record_success(latency_ms)

    def record_failure(
        self,
        model_id: str,
        provider: str,
        error_type: str,
        error_message: str,
        is_timeout: bool = False,
    ) -> None:
        """Record failed request."""
        health = self.get_health(model_id, provider)
        health.record_failure(error_type, error_message, is_timeout)

    def get_all_health(self) -> dict[str, ModelHealth]:
        """Get all health records."""
        return self._health.copy()

    def get_health_summary(self) -> dict[str, Any]:
        """Get summary of all model health."""
        summary = {
            "healthy": 0,
            "degraded": 0,
            "cooldown": 0,
            "total": len(self._health),
        }
        for health in self._health.values():
            summary[health.state.value] += 1
        return summary

    def cleanup_stale_cooldowns(self) -> int:
        """Clean up expired cooldowns and return count."""
        now = datetime.now(UTC)
        cleaned = 0
        for health in self._health.values():
            if health.state == ModelHealthState.COOLDOWN:
                if health.cooldown_until and now >= health.cooldown_until:
                    health.state = ModelHealthState.HEALTHY
                    health.cooldown_until = None
                    health.consecutive_failures = 0
                    cleaned += 1
        return cleaned


# Global health tracker
health_tracker = HealthTracker()