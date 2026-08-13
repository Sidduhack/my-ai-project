"""Agents package - all 18 specialist agents."""

from nvidia_multi_agent_builder.agents.base import (
    AgentConfig,
    AgentRegistry,
    AgentResult,
    BaseAgent,
    agent_registry,
)
from nvidia_multi_agent_builder.agents.architect import ArchitectAgent
from nvidia_multi_agent_builder.agents.accessibility import AccessibilityAgent
from nvidia_multi_agent_builder.agents.backend import BackendAgent
from nvidia_multi_agent_builder.agents.code_reviewer import CodeReviewerAgent
from nvidia_multi_agent_builder.agents.creative_director import CreativeDirectorAgent
from nvidia_multi_agent_builder.agents.database import DatabaseAgent
from nvidia_multi_agent_builder.agents.debugging import DebuggingAgent
from nvidia_multi_agent_builder.agents.documentation import DocumentationAgent
from nvidia_multi_agent_builder.agents.frontend import FrontendAgent
from nvidia_multi_agent_builder.agents.integration import IntegrationAgent
from nvidia_multi_agent_builder.agents.motion_designer import MotionDesignerAgent
from nvidia_multi_agent_builder.agents.performance import PerformanceAgent
from nvidia_multi_agent_builder.agents.planner import PlannerAgent
from nvidia_multi_agent_builder.agents.security import SecurityAgent
from nvidia_multi_agent_builder.agents.seo import SEOAgent
from nvidia_multi_agent_builder.agents.sound_engineer import SoundEngineerAgent
from nvidia_multi_agent_builder.agents.testing import TestingAgent
from nvidia_multi_agent_builder.agents.ui_ux import UIUXAgent


def register_all_agents(registry: AgentRegistry | None = None) -> AgentRegistry:
    """Register all 18 specialist agent classes."""
    registry = registry or agent_registry

    registry.register_agent_class(PlannerAgent)
    registry.register_agent_class(ArchitectAgent)
    registry.register_agent_class(UIUXAgent)
    registry.register_agent_class(CreativeDirectorAgent)
    registry.register_agent_class(MotionDesignerAgent)
    registry.register_agent_class(FrontendAgent)
    registry.register_agent_class(BackendAgent)
    registry.register_agent_class(DatabaseAgent)
    registry.register_agent_class(SecurityAgent)
    registry.register_agent_class(PerformanceAgent)
    registry.register_agent_class(TestingAgent)
    registry.register_agent_class(IntegrationAgent)
    registry.register_agent_class(DebuggingAgent)
    registry.register_agent_class(SoundEngineerAgent)
    registry.register_agent_class(AccessibilityAgent)
    registry.register_agent_class(SEOAgent)
    registry.register_agent_class(DocumentationAgent)
    registry.register_agent_class(CodeReviewerAgent)

    return registry


__all__ = [
    # Base
    "BaseAgent",
    "AgentConfig",
    "AgentResult",
    "AgentRegistry",
    "agent_registry",
    "register_all_agents",
    # Agents
    "PlannerAgent",
    "ArchitectAgent",
    "UIUXAgent",
    "CreativeDirectorAgent",
    "MotionDesignerAgent",
    "FrontendAgent",
    "BackendAgent",
    "DatabaseAgent",
    "SecurityAgent",
    "PerformanceAgent",
    "TestingAgent",
    "IntegrationAgent",
    "DebuggingAgent",
    "SoundEngineerAgent",
    "AccessibilityAgent",
    "SEOAgent",
    "DocumentationAgent",
    "CodeReviewerAgent",
]