"""Task scheduler with concurrency control."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Awaitable

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.core import Event, EventType, publish_event
from nvidia_multi_agent_builder.orchestration.task_queue import TaskQueue
from nvidia_multi_agent_builder.db.models import Task, TaskStatus

logger = get_logger(__name__)

TaskExecutor = Callable[[Task], Awaitable[Any]]


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""

    max_concurrent_tasks: int = 10
    max_concurrent_per_agent: int = 3
    poll_interval: float = 1.0
    task_timeout: float = 300.0  # 5 minutes default


class Scheduler:
    """Schedules and executes tasks with concurrency control."""

    def __init__(
        self,
        task_queue: TaskQueue,
        executor: TaskExecutor,
        config: SchedulerConfig | None = None,
    ):
        self.task_queue = task_queue
        self.executor = executor
        self.config = config or SchedulerConfig()
        self._running = False
        self._task_futures: dict[str, asyncio.Task] = {}
        self._agent_concurrency: dict[str, int] = {}

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        logger.info("scheduler_started", config=self.config.__dict__)
        await self._run_loop()

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._running = False
        # Wait for running tasks
        if self._task_futures:
            logger.info("scheduler_waiting_for_tasks", count=len(self._task_futures))
            await asyncio.gather(*self._task_futures.values(), return_exceptions=True)
        logger.info("scheduler_stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Check for completed futures
                self._cleanup_futures()

                # Try to schedule new tasks
                await self._schedule_tasks()

                # Wait before next iteration
                await asyncio.sleep(self.config.poll_interval)

            except Exception as e:
                logger.error("scheduler_error", error=str(e), exc_info=True)
                await asyncio.sleep(self.config.poll_interval)

    def _cleanup_futures(self) -> None:
        """Remove completed futures."""
        done = [
            task_id for task_id, future in self._task_futures.items()
            if future.done()
        ]
        for task_id in done:
            future = self._task_futures.pop(task_id)
            # Update agent concurrency
            # (Would need task info to know agent)
            try:
                future.result()
            except Exception as e:
                logger.error("task_execution_error", task_id=task_id, error=str(e))

    async def _schedule_tasks(self) -> None:
        """Schedule available tasks."""
        # Check global concurrency
        if len(self._task_futures) >= self.config.max_concurrent_tasks:
            return

        # Get next task
        task = await self.task_queue.get_next_task()
        if not task:
            return

        # Check per-agent concurrency
        agent_id = task.agent_id
        current = self._agent_concurrency.get(agent_id, 0)
        if current >= self.config.max_concurrent_per_agent:
            # Put task back (this is simplified - in reality we'd re-queue)
            logger.debug("agent_at_concurrency_limit", agent_id=agent_id)
            return

        # Execute task
        self._agent_concurrency[agent_id] = current + 1
        future = asyncio.create_task(self._execute_task(task))
        self._task_futures[task.id] = future

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        try:
            await self.executor(task)
        finally:
            # Decrement agent concurrency
            agent_id = task.agent_id
            self._agent_concurrency[agent_id] = max(
                0, self._agent_concurrency.get(agent_id, 1) - 1
            )