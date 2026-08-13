"""Database models for NVIDIA Multi-Agent Builder."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, select
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from nvidia_multi_agent_builder.db.base import Base


class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, enum.Enum):
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


class AgentType(str, enum.Enum):
    PLANNER = "planner"
    ARCHITECT = "architect"
    UI_UX = "ui_ux"
    CREATIVE_DIRECTOR = "creative_director"
    MOTION_DESIGNER = "motion_designer"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    INTEGRATION = "integration"
    DEBUGGING = "debugging"
    SOUND_ENGINEER = "sound_engineer"
    ACCESSIBILITY = "accessibility"
    SEO = "seo"
    DOCUMENTATION = "documentation"
    CODE_REVIEWER = "code_reviewer"


class ModelHealthState(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"


class Project(Base):
    """Project entity."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.CREATED, nullable=False
    )
    requirements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    architecture: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    events: Mapped[list["EventLog"]] = relationship("EventLog", back_populates="project", cascade="all, delete-orphan")
    project_memory: Mapped[list["ProjectMemory"]] = relationship(
        "ProjectMemory", back_populates="project", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    checkpoints: Mapped[list["Checkpoint"]] = relationship("Checkpoint", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_projects_status", "status"),)


class Agent(Base):
    """Agent configuration entity."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    preferred_model_route: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    fallback_models: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    system_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_tools: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    input_schema: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_schema: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    permissions: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    task_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    model_routes: Mapped[list["ModelRoute"]] = relationship("ModelRoute", back_populates="agent", cascade="all, delete-orphan")
    agent_memories: Mapped[list["AgentMemory"]] = relationship("AgentMemory", back_populates="agent", cascade="all, delete-orphan")


class Task(Base):
    """Task entity."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)  # AgentType value
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.NORMAL, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    input_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    dependencies: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    assigned_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    dependencies_rel: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    dependents_rel: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_id",
        back_populates="depends_on",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_agent_status", "agent_id", "status"),
    )


class TaskDependency(Base):
    """Task dependency entity."""

    __tablename__ = "task_dependencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    task: Mapped["Task"] = relationship("Task", foreign_keys=[task_id], back_populates="dependencies_rel")
    depends_on: Mapped["Task"] = relationship("Task", foreign_keys=[depends_on_id], back_populates="dependents_rel")

    __table_args__ = (
        Index("ix_task_dependencies_task", "task_id"),
        Index("ix_task_dependencies_depends_on", "depends_on_id"),
    )


class Model(Base):
    """Model entity."""

    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    context_window: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supports_streaming: Mapped[bool] = mapped_column(default=True, nullable=False)
    supports_structured_output: Mapped[bool] = mapped_column(default=False, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    health: Mapped[Optional["ModelHealth"]] = relationship(
        "ModelHealth", back_populates="model", uselist=False, cascade="all, delete-orphan"
    )
    observations: Mapped[list["ModelObservation"]] = relationship("ModelObservation", back_populates="model", cascade="all, delete-orphan")
    scores: Mapped[list["ModelScore"]] = relationship("ModelScore", back_populates="model", cascade="all, delete-orphan")
    routes: Mapped[list["ModelRoute"]] = relationship("ModelRoute", back_populates="model")


class ModelRoute(Base):
    """Model route configuration for agents."""

    __tablename__ = "model_routes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_fallback: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    agent: Mapped["Agent"] = relationship("Agent", back_populates="model_routes")
    model: Mapped["Model"] = relationship("Model", back_populates="routes")

    __table_args__ = (
        Index("ix_model_routes_agent_priority", "agent_id", "priority"),
    )


class ModelHealth(Base):
    """Model health tracking."""

    __tablename__ = "model_health"

    model_id: Mapped[str] = mapped_column(String(128), ForeignKey("models.id", ondelete="CASCADE"), primary_key=True)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timeout_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_latency_ms: Mapped[float] = mapped_column(default=0.0, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recent_latencies: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    max_recent_latencies: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    last_error_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    availability: Mapped[float] = mapped_column(default=1.0, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    state: Mapped[ModelHealthState] = mapped_column(Enum(ModelHealthState), default=ModelHealthState.HEALTHY, nullable=False)
    failure_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    success_threshold: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    cooldown_duration_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    model: Mapped["Model"] = relationship("Model", back_populates="health")

    __table_args__ = (Index("ix_model_health_state", "state"),)


class ModelObservation(Base):
    """Model execution observation for scoring."""

    __tablename__ = "model_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    model_id: Mapped[str] = mapped_column(String(128), ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    success: Mapped[bool] = mapped_column(nullable=False)
    latency_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_benchmark: Mapped[bool] = mapped_column(default=False, nullable=False)

    model: Mapped["Model"] = relationship("Model", back_populates="observations")

    __table_args__ = (
        Index("ix_model_observations_model_timestamp", "model_id", "timestamp"),
        Index("ix_model_observations_agent_model", "agent_id", "model_id"),
    )


class ModelScore(Base):
    """Model score for agent-model pairs."""

    __tablename__ = "model_scores"

    model_id: Mapped[str] = mapped_column(String(128), ForeignKey("models.id", ondelete="CASCADE"), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reliability_score: Mapped[float] = mapped_column(default=0.5, nullable=False)
    latency_score: Mapped[float] = mapped_column(default=0.5, nullable=False)
    confidence_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    composite_score: Mapped[float] = mapped_column(default=0.5, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_calculated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    model: Mapped["Model"] = relationship("Model", back_populates="scores")

    __table_args__ = (Index("ix_model_scores_composite", "composite_score"),)


class EventLog(Base):
    """Event log for audit trail and realtime updates."""

    __tablename__ = "event_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    project: Mapped["Project"] = relationship("Project", back_populates="events")

    __table_args__ = (
        Index("ix_event_logs_project_timestamp", "project_id", "created_at"),
        Index("ix_event_logs_type", "event_type"),
    )


class ProjectMemory(Base):
    """Project-level memory."""

    __tablename__ = "project_memory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    project: Mapped["Project"] = relationship("Project", back_populates="project_memory")

    __table_args__ = (
        Index("ix_project_memory_project_category", "project_id", "category"),
    )


class AgentMemory(Base):
    """Agent-specific memory."""

    __tablename__ = "agent_memory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="agent_memories")

    __table_args__ = (
        Index("ix_agent_memory_agent_project", "agent_id", "project_id"),
    )


class Artifact(Base):
    """Generated artifact."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    project: Mapped["Project"] = relationship("Project", back_populates="artifacts")

    __table_args__ = (Index("ix_artifacts_project_type", "project_id", "type"),)


class Checkpoint(Base):
    """Project checkpoint for recovery."""

    __tablename__ = "checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    project: Mapped["Project"] = relationship("Project", back_populates="checkpoints")

    __table_args__ = (Index("ix_checkpoints_project", "project_id"),)


# Re-export enums for convenience
__all__ = [
    "ProjectStatus",
    "TaskStatus",
    "TaskPriority",
    "AgentType",
    "ModelHealthState",
    "Project",
    "Agent",
    "Task",
    "TaskDependency",
    "Model",
    "ModelRoute",
    "ModelHealth",
    "ModelObservation",
    "ModelScore",
    "EventLog",
    "ProjectMemory",
    "AgentMemory",
    "Artifact",
    "Checkpoint",
]