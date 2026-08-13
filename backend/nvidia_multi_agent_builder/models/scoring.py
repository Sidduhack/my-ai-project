"""Adaptive model scoring system."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.models.health import health_tracker, ModelHealth

logger = get_logger(__name__)


@dataclass
class ModelScore:
    """Computed score for a model-agent pair."""

    model_id: str  # provider/model-id
    agent_type: str

    # Component scores (0.0 - 1.0)
    reliability_score: float = 0.5
    latency_score: float = 0.5
    confidence_score: float = 0.0
    recency_score: float = 0.5
    specialization_score: float = 0.0
    priority_score: float = 0.0

    # Weighted total
    total_score: float = 0.0

    # Metadata
    sample_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Weights (must sum to 1.0)
    WEIGHTS = {
        "reliability": 0.40,
        "latency": 0.15,
        "confidence": 0.20,
        "recency": 0.10,
        "specialization": 0.10,
        "priority": 0.05,
    }

    def compute_total(self) -> float:
        """Compute weighted total score."""
        self.total_score = (
            self.reliability_score * self.WEIGHTS["reliability"] +
            self.latency_score * self.WEIGHTS["latency"] +
            self.confidence_score * self.WEIGHTS["confidence"] +
            self.recency_score * self.WEIGHTS["recency"] +
            self.specialization_score * self.WEIGHTS["specialization"] +
            self.priority_score * self.WEIGHTS["priority"]
        )
        return self.total_score

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "model_id": self.model_id,
            "agent_type": self.agent_type,
            "reliability_score": self.reliability_score,
            "latency_score": self.latency_score,
            "confidence_score": self.confidence_score,
            "recency_score": self.recency_score,
            "specialization_score": self.specialization_score,
            "priority_score": self.priority_score,
            "total_score": self.total_score,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated.isoformat(),
        }


class ScoringEngine:
    """Adaptive scoring engine for model-agent pairs."""

    def __init__(self):
        self._scores: dict[str, ModelScore] = {}  # key: "agent_type:provider/model-id"
        self._agent_baselines: dict[str, float] = {}  # agent_type -> baseline latency
        self._agent_model_outcomes: dict[str, list[dict]] = {}  # agent_type:model -> outcomes

    def _get_key(self, agent_type: str, model_id: str) -> str:
        return f"{agent_type}:{model_id}"

    def get_score(self, agent_type: str, model_id: str) -> ModelScore | None:
        """Get score for model-agent pair."""
        return self._scores.get(self._get_key(agent_type, model_id))

    def get_all_scores(self, agent_type: str) -> list[ModelScore]:
        """Get all scores for an agent type."""
        prefix = f"{agent_type}:"
        return [s for k, s in self._scores.items() if k.startswith(prefix)]

    def update_from_health(
        self,
        agent_type: str,
        model_id: str,
        health: ModelHealth,
        configured_priority: int = 0,
        priority: int | None = None,  # Alias for backward compatibility
    ) -> ModelScore:
        """Update score from health data."""
        # Support both configured_priority and priority parameter names
        if priority is not None:
            configured_priority = priority
        key = self._get_key(agent_type, model_id)

        if key not in self._scores:
            self._scores[key] = ModelScore(model_id=model_id, agent_type=agent_type)

        score = self._scores[key]
        score.sample_count = health.success_count + health.failure_count

        # 1. Reliability Score (Wilson confidence interval lower bound)
        score.reliability_score = self._compute_reliability_score(health)

        # 2. Latency Score (normalized against agent baseline)
        score.latency_score = self._compute_latency_score(agent_type, health)

        # 3. Confidence Score (based on sample size)
        score.confidence_score = self._compute_confidence_score(score.sample_count)

        # 4. Recency Score (exponential decay of recent performance)
        score.recency_score = self._compute_recency_score(health)

        # 5. Specialization Score (agent-specific performance)
        score.specialization_score = self._compute_specialization_score(agent_type, model_id, health)

        # 6. Priority Score (configured route priority)
        score.priority_score = self._compute_priority_score(configured_priority)

        score.last_updated = datetime.now(UTC)
        score.compute_total()

        return score

    def record_outcome(
        self,
        agent_type: str,
        model_id: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record an outcome for specialization tracking."""
        key = self._get_key(agent_type, model_id)
        if key not in self._agent_model_outcomes:
            self._agent_model_outcomes[key] = []

        self._agent_model_outcomes[key].append({
            "success": success,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(UTC),
        })

        # Keep last 1000 outcomes
        if len(self._agent_model_outcomes[key]) > 1000:
            self._agent_model_outcomes[key] = self._agent_model_outcomes[key][-1000:]

    def _compute_reliability_score(self, health: ModelHealth) -> float:
        """Compute reliability using Wilson score interval lower bound."""
        total = health.success_count + health.failure_count
        if total == 0:
            return 0.5  # Neutral prior

        # Wilson score interval (95% confidence, z=1.96)
        z = 1.96
        p = health.success_count / total
        denominator = 1 + z**2 / total
        centre = p + z**2 / (2 * total)
        adjustment = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
        lower_bound = (centre - adjustment) / denominator

        # Scale to 0-1 (Wilson lower bound is already 0-1)
        return max(0.0, min(1.0, lower_bound))

    def _compute_latency_score(self, agent_type: str, health: ModelHealth) -> float:
        """Compute latency score normalized against agent baseline."""
        if health.request_count == 0:
            return 0.5

        recent_avg = health.get_recent_avg_latency()
        if recent_avg <= 0:
            return 0.5

        # Get or compute baseline for this agent type
        if agent_type not in self._agent_baselines:
            # Estimate baseline from all models for this agent
            latencies = []
            for model_key, outcomes in self._agent_model_outcomes.items():
                if model_key.startswith(f"{agent_type}:"):
                    for o in outcomes[-50:]:  # Last 50 outcomes per model
                        latencies.append(o["latency_ms"])
            if latencies:
                self._agent_baselines[agent_type] = sum(latencies) / len(latencies)
            else:
                self._agent_baselines[agent_type] = recent_avg

        baseline = self._agent_baselines[agent_type]

        # Score: 1.0 at baseline, decreases as latency increases
        # Using inverse relationship with soft cap
        ratio = recent_avg / baseline
        if ratio <= 1.0:
            return 1.0
        elif ratio <= 2.0:
            return 1.0 - (ratio - 1.0) * 0.3  # Linear decay to 0.7 at 2x
        elif ratio <= 5.0:
            return 0.7 - (ratio - 2.0) * 0.1  # Slower decay to 0.4 at 5x
        else:
            return max(0.1, 0.4 - (ratio - 5.0) * 0.02)  # Slow decay to floor

    def _compute_confidence_score(self, sample_count: int) -> float:
        """Compute confidence based on sample size."""
        if sample_count <= 1:
            return 0.0
        elif sample_count <= 5:
            return 0.2
        elif sample_count <= 10:
            return 0.4
        elif sample_count <= 20:
            return 0.6
        elif sample_count <= 50:
            return 0.8
        elif sample_count <= 100:
            return 0.9
        else:
            return 1.0

    def _compute_recency_score(self, health: ModelHealth) -> float:
        """Compute recency score with exponential decay."""
        now = datetime.now(UTC)

        if health.last_failure_at is None:
            return 1.0  # No failures recorded

        # Time since last failure
        hours_since_failure = (now - health.last_failure_at).total_seconds() / 3600

        if hours_since_failure <= 0:
            return 0.1  # Very recent failure
        elif hours_since_failure <= 1:
            return 0.3
        elif hours_since_failure <= 6:
            return 0.5
        elif hours_since_failure <= 24:
            return 0.7
        elif hours_since_failure <= 72:
            return 0.85
        else:
            return 1.0  # Failure is old news

    def _compute_specialization_score(
        self,
        agent_type: str,
        model_id: str,
        health: ModelHealth,
    ) -> float:
        """Compute specialization score from agent-specific outcomes."""
        key = self._get_key(agent_type, model_id)
        outcomes = self._agent_model_outcomes.get(key, [])

        if len(outcomes) < 5:
            return 0.0  # Not enough data

        # Compute success rate for this specific agent-model pair
        recent = outcomes[-50:]  # Last 50
        successes = sum(1 for o in recent if o["success"])
        rate = successes / len(recent)

        # Compare to model's overall success rate
        overall_rate = health.get_success_rate()

        # Specialization bonus: how much better this model is for this agent
        diff = rate - overall_rate
        if diff > 0.1:
            return min(1.0, diff * 2)  # Up to 1.0 for 50% better
        elif diff > 0:
            return diff  # Small bonus
        else:
            return 0.0  # No bonus (or penalty handled elsewhere)

    def _compute_priority_score(self, configured_priority: int) -> float:
        """Convert configured priority to 0-1 score."""
        # Priority can be negative (deprioritize) or positive
        # Map: -10 -> 0.0, 0 -> 0.5, +10 -> 1.0
        return max(0.0, min(1.0, 0.5 + configured_priority * 0.05))

    def get_best_model(self, agent_type: str, available_models: list[str]) -> str | None:
        """Get highest-scoring available model for agent."""
        scores = []
        for model_id in available_models:
            score = self.get_score(agent_type, model_id)
            if score and score.total_score > 0:
                scores.append((score.total_score, model_id))

        if not scores:
            return None

        scores.sort(reverse=True)
        return scores[0][1]

    def get_ranked_models(self, agent_type: str) -> list[tuple[float, str]]:
        """Get all models for agent ranked by score."""
        scores = self.get_all_scores(agent_type)
        ranked = [(s.total_score, s.model_id) for s in scores if s.total_score > 0]
        ranked.sort(reverse=True)
        return ranked

    def get_scoring_summary(self, agent_type: str) -> dict[str, Any]:
        """Get scoring summary for debugging."""
        scores = self.get_all_scores(agent_type)
        return {
            "agent_type": agent_type,
            "models_scored": len(scores),
            "rankings": [
                {
                    "model": s.model_id,
                    "total": round(s.total_score, 4),
                    "reliability": round(s.reliability_score, 4),
                    "latency": round(s.latency_score, 4),
                    "confidence": round(s.confidence_score, 4),
                    "recency": round(s.recency_score, 4),
                    "specialization": round(s.specialization_score, 4),
                    "priority": round(s.priority_score, 4),
                    "samples": s.sample_count,
                }
                for s in sorted(scores, key=lambda x: x.total_score, reverse=True)
            ],
        }


# Global scoring engine
scoring_engine = ScoringEngine()