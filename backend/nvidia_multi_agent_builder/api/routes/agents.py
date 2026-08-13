"""Agent API routes."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nvidia_multi_agent_builder.agents import agent_registry, register_all_agents
from nvidia_multi_agent_builder.db import get_session
from nvidia_multi_agent_builder.db.models import Agent, AgentType

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentCreate(BaseModel):
    type: AgentType
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    system_prompt: str | None = None


class AgentResponse(BaseModel):
    id: str
    type: str
    name: str
    role: str | None
    description: str | None
    system_prompt: str | None
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Register a new agent type."""
    # Check if agent type already exists
    existing = await session.execute(
        select(Agent).where(Agent.agent_type == agent_data.type)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Agent type {agent_data.type} already registered")

    agent = Agent(
        id=f"{agent_data.type.value}-{str(uuid4())[:8]}",
        agent_type=agent_data.type,
        name=agent_data.name,
        role=agent_data.description or "",
        system_instructions=agent_data.system_prompt,
        is_active=True,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    session: AsyncSession = Depends(get_session),
) -> list[Agent]:
    """List all registered agents."""
    result = await session.execute(select(Agent).order_by(Agent.agent_type))
    return list(result.scalars().all())


@router.get("/types")
async def list_agent_types() -> list[dict[str, str]]:
    """List all available agent types."""
    register_all_agents()
    return [
        {"type": at.value, "name": at.value.replace("_", " ").title()}
        for at in AgentType
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Get an agent by ID."""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/memory")
async def get_agent_memory(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get agent memory."""
    from nvidia_multi_agent_builder.db.models import AgentMemory
    from sqlalchemy import select

    result = await session.execute(
        select(AgentMemory).where(AgentMemory.agent_id == agent_id)
    )
    memories = list(result.scalars().all())

    return {m.key: m.value for m in memories}


@router.post("/{agent_id}/memory")
async def set_agent_memory(
    agent_id: str,
    key: str,
    value: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Set agent memory."""
    from nvidia_multi_agent_builder.db.models import AgentMemory
    from sqlalchemy import select

    existing = await session.execute(
        select(AgentMemory).where(AgentMemory.agent_id == agent_id, AgentMemory.key == key)
    )
    memory = existing.scalar_one_or_none()

    if memory:
        memory.value = value
    else:
        memory = AgentMemory(agent_id=agent_id, key=key, value=value)
        session.add(memory)

    await session.commit()
    return {"status": "ok"}