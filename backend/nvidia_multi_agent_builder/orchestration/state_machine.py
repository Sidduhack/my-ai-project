"""State machine for task and project lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from nvidia_multi_agent_builder.db.models import TaskStatus, ProjectStatus


class StateMachine:
    """Manages valid state transitions."""

    # Valid transitions: current_state -> set(valid_next_states)
    TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
        TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED},
        TaskStatus.BLOCKED: {TaskStatus.PENDING, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: set(),  # Terminal
        TaskStatus.FAILED: {TaskStatus.PENDING},  # Retry
        TaskStatus.CANCELLED: set(),  # Terminal
    }

    PROJECT_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
        ProjectStatus.CREATED: {ProjectStatus.PLANNING, ProjectStatus.CANCELLED},
        ProjectStatus.PLANNING: {ProjectStatus.RUNNING, ProjectStatus.CANCELLED},
        ProjectStatus.RUNNING: {ProjectStatus.PAUSED, ProjectStatus.COMPLETED, ProjectStatus.FAILED, ProjectStatus.CANCELLED},
        ProjectStatus.PAUSED: {ProjectStatus.RUNNING, ProjectStatus.CANCELLED},
        ProjectStatus.COMPLETED: set(),
        ProjectStatus.FAILED: {ProjectStatus.RUNNING, ProjectStatus.CANCELLED},
        ProjectStatus.CANCELLED: set(),
    }

    @classmethod
    def can_transition_task(cls, from_status: TaskStatus, to_status: TaskStatus) -> bool:
        """Check if task transition is valid."""
        return to_status in cls.TASK_TRANSITIONS.get(from_status, set())

    @classmethod
    def can_transition_project(cls, from_status: ProjectStatus, to_status: ProjectStatus) -> bool:
        """Check if project transition is valid."""
        return to_status in cls.PROJECT_TRANSITIONS.get(from_status, set())

    @classmethod
    def get_valid_task_transitions(cls, status: TaskStatus) -> list[TaskStatus]:
        """Get valid next states for task."""
        return list(cls.TASK_TRANSITIONS.get(status, set()))

    @classmethod
    def get_valid_project_transitions(cls, status: ProjectStatus) -> list[ProjectStatus]:
        """Get valid next states for project."""
        return list(cls.PROJECT_TRANSITIONS.get(status, set()))

    @classmethod
    def is_terminal_task(cls, status: TaskStatus) -> bool:
        """Check if task status is terminal."""
        return status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}

    @classmethod
    def is_terminal_project(cls, status: ProjectStatus) -> bool:
        """Check if project status is terminal."""
        return status in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}


@dataclass
class StateTransition:
    """Record of a state transition."""

    entity_type: str  # "task" or "project"
    entity_id: str
    from_state: str
    to_state: str
    timestamp: Any
    reason: str | None = None