"""Project API routes."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nvidia_multi_agent_builder.db import get_session
from nvidia_multi_agent_builder.db.models import Project, ProjectStatus
from nvidia_multi_agent_builder.orchestration import orchestrator

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    requirements: dict[str, Any] = Field(default_factory=dict)


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    requirements: dict[str, Any]
    created_at: str
    started_at: str | None
    completed_at: str | None

    class Config:
        from_attributes = True


class ProjectStatusResponse(BaseModel):
    project_id: str
    name: str
    status: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    tasks: list[dict[str, Any]]
    queue_status: dict[str, Any]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Create a new project."""
    project = Project(
        name=project_data.name,
        description=project_data.description,
        requirements=project_data.requirements,
        status=ProjectStatus.CREATED,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[Project]:
    """List all projects."""
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Get a project by ID."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/start", response_model=ProjectResponse)
async def start_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Start a project (begin planning phase)."""
    await orchestrator.start_project(project_id)

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/pause", response_model=ProjectResponse)
async def pause_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Pause a running project."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from nvidia_multi_agent_builder.orchestration.state_machine import StateMachine
    if not StateMachine.can_transition_project(project.status, ProjectStatus.PAUSED):
        raise HTTPException(status_code=400, detail=f"Cannot pause project in status: {project.status}")

    project.status = ProjectStatus.PAUSED
    await session.commit()
    await session.refresh(project)
    return project


@router.post("/{project_id}/cancel", response_model=ProjectResponse)
async def cancel_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Cancel a project."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from nvidia_multi_agent_builder.orchestration.state_machine import StateMachine
    if not StateMachine.can_transition_project(project.status, ProjectStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel project in status: {project.status}")

    project.status = ProjectStatus.CANCELLED
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(
    project_id: str,
) -> dict[str, Any]:
    """Get detailed project status with tasks."""
    status = await orchestrator.get_project_status(project_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.get("/{project_id}/tasks")
async def get_project_tasks(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Get all tasks for a project."""
    from nvidia_multi_agent_builder.db.models import Task
    from sqlalchemy import select

    result = await session.execute(
        select(Task).where(Task.project_id == project_id).order_by(Task.created_at)
    )
    tasks = list(result.scalars().all())

    return [
        {
            "id": t.id,
            "agent_id": t.agent_id,
            "description": t.description,
            "priority": t.priority,
            "status": t.status,
            "dependencies": t.dependencies,
            "created_at": t.created_at.isoformat(),
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "error": t.error,
        }
        for t in tasks
    ]


@router.get("/{project_id}/events")
async def get_project_events(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Get event log for a project."""
    from nvidia_multi_agent_builder.db.models import EventLog
    from sqlalchemy import select

    result = await session.execute(
        select(EventLog)
        .where(EventLog.project_id == project_id)
        .order_by(EventLog.created_at.desc())
        .limit(100)
    )
    events = list(result.scalars().all())

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_id": e.event_id,
            "payload": e.payload,
            "correlation_id": e.correlation_id,
            "source": e.source,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]