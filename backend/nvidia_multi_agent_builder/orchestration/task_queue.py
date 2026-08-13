"""Task queue with dependency resolution."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.core import Event, EventType, publish_event
from nvidia_multi_agent_builder.core.exceptions import TaskDependencyError
from nvidia_multi_agent_builder.db.models import Task, TaskStatus

logger = get_logger(__name__)


@dataclass
class QueuedTask:
    """Task in the queue with metadata."""

    task: Task
    added_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    priority_score: float = 0.0
    dependencies_met: bool = False


class TaskQueue:
    """Priority queue with dependency resolution."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._pending: dict[str, QueuedTask] = {}  # task_id -> QueuedTask
        self._running: dict[str, QueuedTask] = {}  # task_id -> QueuedTask
        self._completed: set[str] = set()
        self._failed: set[str] = set()
        self._blocked: dict[str, QueuedTask] = {}  # task_id -> QueuedTask
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def add_task(self, task: Task) -> None:
        """Add a task to the queue."""
        async with self._lock:
            if task.id in self._pending or task.id in self._running:
                return

            # Check if dependencies exist
            deps = task.dependencies or []
            missing_deps = [
                dep for dep in deps
                if dep not in self._completed
            ]

            queued = QueuedTask(
                task=task,
                dependencies_met=len(missing_deps) == 0,
            )

            if queued.dependencies_met:
                self._pending[task.id] = queued
                self._not_empty.set()
            else:
                self._blocked[task.id] = queued

            logger.debug("task_queued", task_id=task.id, blocked=not queued.dependencies_met)

    async def add_tasks(self, tasks: list[Task]) -> None:
        """Add multiple tasks."""
        for task in tasks:
            await self.add_task(task)
        await self._recheck_blocked()

    async def _recheck_blocked(self) -> None:
        """Recheck blocked tasks for dependency resolution."""
        newly_ready = []
        for task_id, queued in self._blocked.items():
            deps = queued.task.dependencies or []
            missing = [
                dep for dep in deps
                if dep not in self._completed
            ]
            if not missing:
                newly_ready.append(task_id)

        for task_id in newly_ready:
            queued = self._blocked.pop(task_id)
            queued.dependencies_met = True
            self._pending[task_id] = queued
            self._not_empty.set()
            logger.debug("task_unblocked", task_id=task_id)

    async def get_next_task(self) -> Task | None:
        """Get the next runnable task (highest priority)."""
        async with self._lock:
            # Wait for tasks if queue is empty
            while not self._pending and not self._running:
                self._not_empty.clear()
                try:
                    await asyncio.wait_for(self._not_empty.wait(), timeout=1.0)
                except TimeoutError:
                    return None

            if not self._pending:
                return None

            # Check concurrency limit
            if len(self._running) >= self.max_concurrent:
                return None

            # Select highest priority task
            best_task = max(
                self._pending.values(),
                key=lambda q: (q.task.priority.value, q.priority_score, -q.added_at.timestamp())
            )

            # Move to running
            del self._pending[best_task.task.id]
            self._running[best_task.task.id] = best_task

            # Update task status
            best_task.task.status = TaskStatus.RUNNING
            best_task.task.started_at = datetime.now(UTC)

            logger.info("task_started", task_id=best_task.task.id, agent=best_task.task.agent_id)
            await publish_event(
                EventType.TASK_STARTED,
                {"task_id": best_task.task.id, "agent_id": best_task.task.agent_id},
                source="task_queue",
            )

            return best_task.task

    async def complete_task(self, task_id: str, success: bool = True) -> None:
        """Mark task as completed."""
        async with self._lock:
            # Check if task is running
            if task_id in self._running:
                queued = self._running.pop(task_id)
            # Check if task is pending (for testing)
            elif task_id in self._pending:
                queued = self._pending.pop(task_id)
            else:
                return

            if success:
                self._completed.add(task_id)
                queued.task.status = TaskStatus.COMPLETED
                queued.task.completed_at = datetime.now(UTC)
                logger.info("task_completed", task_id=task_id)
                await publish_event(
                    EventType.TASK_COMPLETED,
                    {"task_id": task_id},
                    source="task_queue",
                )
            else:
                self._failed.add(task_id)
                queued.task.status = TaskStatus.FAILED
                queued.task.completed_at = datetime.now(UTC)
                logger.warning("task_failed", task_id=task_id)
                await publish_event(
                    EventType.TASK_FAILED,
                    {"task_id": task_id, "error": queued.task.error},
                    source="task_queue",
                )

            # Recheck blocked tasks
            await self._recheck_blocked()

    async def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed with error."""
        async with self._lock:
            if task_id in self._running:
                queued = self._running.pop(task_id)
                self._failed.add(task_id)
                queued.task.status = TaskStatus.FAILED
                queued.task.error = error
                queued.task.completed_at = datetime.now(UTC)
                logger.warning("task_failed", task_id=task_id, error=error)
                await publish_event(
                    EventType.TASK_FAILED,
                    {"task_id": task_id, "error": error},
                    source="task_queue",
                )
                await self._recheck_blocked()

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        async with self._lock:
            if task_id in self._pending:
                queued = self._pending.pop(task_id)
                queued.task.status = TaskStatus.CANCELLED
                return True
            if task_id in self._running:
                queued = self._running.pop(task_id)
                queued.task.status = TaskStatus.CANCELLED
                return True
            if task_id in self._blocked:
                queued = self._blocked.pop(task_id)
                queued.task.status = TaskStatus.CANCELLED
                return True
            return False

    def get_queue_status(self) -> dict[str, Any]:
        """Get queue status for monitoring."""
        return {
            "pending": len(self._pending),
            "running": len(self._running),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "blocked": len(self._blocked),
            "max_concurrent": self.max_concurrent,
        }

    def get_task_status(self, task_id: str) -> str | None:
        """Get task status."""
        if task_id in self._pending:
            return TaskStatus.PENDING.value
        if task_id in self._running:
            return TaskStatus.RUNNING.value
        if task_id in self._completed:
            return TaskStatus.COMPLETED.value
        if task_id in self._failed:
            return TaskStatus.FAILED.value
        if task_id in self._blocked:
            return TaskStatus.BLOCKED.value
        return None

    async def get_ready_tasks(self) -> list[Task]:
        """Get all tasks ready to run (dependencies met)."""
        async with self._lock:
            return [queued.task for queued in self._pending.values()]