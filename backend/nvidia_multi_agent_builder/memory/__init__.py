"""Memory system for project and agent memory with vector search."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.db import get_session
from nvidia_multi_agent_builder.db.models import ProjectMemory, AgentMemory, Project, Agent

logger = get_logger(__name__)


class ProjectMemoryService:
    """Project-level memory with semantic search."""

    def __init__(self, project_id: str):
        self.project_id = project_id

    async def store(self, key: str, value: dict[str, Any], category: str = "general", importance: int = 1) -> None:
        """Store a memory entry."""
        async with get_session() as session:
            from sqlalchemy import select
            existing = await session.execute(
                select(ProjectMemory).where(
                    ProjectMemory.project_id == self.project_id,
                    ProjectMemory.key == key,
                )
            )
            memory = existing.scalar_one_or_none()

            if memory:
                memory.value = value
                memory.category = category
                memory.importance = importance
                memory.updated_at = datetime.now(UTC)
            else:
                memory = ProjectMemory(
                    project_id=self.project_id,
                    key=key,
                    value=value,
                    category=category,
                    importance=importance,
                )
                session.add(memory)

            await session.commit()

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a memory entry."""
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ProjectMemory).where(
                    ProjectMemory.project_id == self.project_id,
                    ProjectMemory.key == key,
                )
            )
            memory = result.scalar_one_or_none()
            return memory.value if memory else default

    async def get_all(self, category: str | None = None) -> dict[str, Any]:
        """Get all memories, optionally filtered by category."""
        async with get_session() as session:
            from sqlalchemy import select
            query = select(ProjectMemory).where(ProjectMemory.project_id == self.project_id)
            if category:
                query = query.where(ProjectMemory.category == category)
            query = query.order_by(ProjectMemory.importance.desc())
            result = await session.execute(query)
            memories = list(result.scalars().all())
            return {m.key: m.value for m in memories}

    async def delete(self, key: str) -> bool:
        """Delete a memory entry."""
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ProjectMemory).where(
                    ProjectMemory.project_id == self.project_id,
                    ProjectMemory.key == key,
                )
            )
            memory = result.scalar_one_or_none()
            if memory:
                await session.delete(memory)
                await session.commit()
                return True
            return False

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Semantic search (placeholder - would use vector embeddings)."""
        # In production, this would use sqlite-vec or pgvector
        # For now, simple text matching
        all_memories = await self.get_all()
        results = []
        query_lower = query.lower()
        for key, value in all_memories.items():
            content = json.dumps(value).lower()
            if query_lower in content or query_lower in key.lower():
                results.append({"key": key, "value": value, "relevance": 1.0})
                if len(results) >= limit:
                    break
        return results


class AgentMemoryService:
    """Agent-specific memory."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def store(self, key: str, value: dict[str, Any], category: str = "general", importance: int = 1) -> None:
        async with get_session() as session:
            from sqlalchemy import select
            existing = await session.execute(
                select(AgentMemory).where(
                    AgentMemory.agent_id == self.agent_id,
                    AgentMemory.key == key,
                )
            )
            memory = existing.scalar_one_or_none()

            if memory:
                memory.value = value
                memory.category = category
                memory.importance = importance
                memory.updated_at = datetime.now(UTC)
            else:
                memory = AgentMemory(
                    agent_id=self.agent_id,
                    key=key,
                    value=value,
                    category=category,
                    importance=importance,
                )
                session.add(memory)

            await session.commit()

    async def get(self, key: str, default: Any = None) -> Any:
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(AgentMemory).where(
                    AgentMemory.agent_id == self.agent_id,
                    AgentMemory.key == key,
                )
            )
            memory = result.scalar_one_or_none()
            return memory.value if memory else default

    async def get_all(self, category: str | None = None) -> dict[str, Any]:
        async with get_session() as session:
            from sqlalchemy import select
            query = select(AgentMemory).where(AgentMemory.agent_id == self.agent_id)
            if category:
                query = query.where(AgentMemory.category == category)
            query = query.order_by(AgentMemory.importance.desc())
            result = await session.execute(query)
            memories = list(result.scalars().all())
            return {m.key: m.value for m in memories}

    async def delete(self, key: str) -> bool:
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(AgentMemory).where(
                    AgentMemory.agent_id == self.agent_id,
                    AgentMemory.key == key,
                )
            )
            memory = result.scalar_one_or_none()
            if memory:
                await session.delete(memory)
                await session.commit()
                return True
            return False


def get_project_memory(project_id: str) -> ProjectMemoryService:
    """Get project memory service."""
    return ProjectMemoryService(project_id)


def get_agent_memory(agent_id: str) -> AgentMemoryService:
    """Get agent memory service."""
    return AgentMemoryService(agent_id)