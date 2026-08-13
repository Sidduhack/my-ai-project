"""Event system for the multi-agent builder."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from nvidia_multi_agent_builder.config.logging import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    """Core event types in the system."""

    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    PROJECT_STARTED = "project.started"
    PROJECT_PAUSED = "project.paused"
    PROJECT_COMPLETED = "project.completed"
    PROJECT_FAILED = "project.failed"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_BLOCKED = "task.blocked"
    TASK_RETRY = "task.retry"

    # Agent events
    AGENT_REGISTERED = "agent.registered"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # Model events
    MODEL_SELECTED = "model.selected"
    MODEL_FAILED = "model.failed"
    MODEL_FALLBACK = "model.fallback"
    MODEL_RECOVERED = "model.recovered"
    MODEL_HEALTH_CHANGED = "model.health_changed"

    # Build events
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    BUILD_FAILED = "build.failed"

    # Test events
    TEST_STARTED = "test.started"
    TEST_COMPLETED = "test.completed"
    TEST_FAILED = "test.failed"

    # Review events
    REVIEW_REQUIRED = "review.required"
    REVIEW_COMPLETED = "review.completed"

    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"


@dataclass
class Event:
    """Base event structure."""

    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "source": self.source,
        }


type EventHandler = Callable[[Event], Any]


class EventBus:
    """Internal event bus for pub/sub messaging."""

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("handler_subscribed", event_type=event_type.value, handler=handler.__name__)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to all events."""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        logger.debug("event_published", event_id=event.event_id, type=event.type.value)

        # Call type-specific handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    "handler_error",
                    event_id=event.event_id,
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True,
                )

        # Call global handlers
        for handler in self._global_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    "global_handler_error",
                    event_id=event.event_id,
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True,
                )

    def publish_sync(self, event: Event) -> None:
        """Publish an event synchronously (for non-async contexts)."""
        # Call type-specific handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    "handler_error",
                    event_id=event.event_id,
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True,
                )

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    "global_handler_error",
                    event_id=event.event_id,
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True,
                )


# Global event bus instance
event_bus = EventBus()


def create_event(
    event_type: EventType,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    source: str | None = None,
) -> Event:
    """Create a new event."""
    return Event(
        type=event_type,
        payload=payload or {},
        correlation_id=correlation_id,
        source=source,
    )


async def publish_event(
    event_type: EventType,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    source: str | None = None,
) -> None:
    """Create and publish an event."""
    event = create_event(event_type, payload, correlation_id, source)
    await event_bus.publish(event)