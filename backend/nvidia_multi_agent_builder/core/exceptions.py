"""Core exceptions for the multi-agent builder."""


class MultiAgentBuilderError(Exception):
    """Base exception for all multi-agent builder errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(MultiAgentBuilderError):
    """Raised when configuration is invalid or missing."""


class ProviderError(MultiAgentBuilderError):
    """Raised when a model provider encounters an error."""

    def __init__(
        self,
        message: str,
        provider: str,
        model: str | None = None,
        error_type: str = "unknown",
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.provider = provider
        self.model = model
        self.error_type = error_type


class ModelNotFoundError(ProviderError):
    """Raised when a requested model is not available."""

    def __init__(self, message: str, provider: str = "unknown", model: str | None = None, details: dict | None = None):
        super().__init__(message, provider, model, "model_not_found", details)


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out."""


class ProviderRateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication fails."""


class AgentError(MultiAgentBuilderError):
    """Raised when an agent encounters an error."""

    def __init__(
        self,
        message: str,
        agent_id: str,
        task_id: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.agent_id = agent_id
        self.task_id = task_id


class AgentNotFoundError(AgentError):
    """Raised when an agent is not registered."""


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""


class TaskError(MultiAgentBuilderError):
    """Raised when a task encounters an error."""

    def __init__(
        self,
        message: str,
        task_id: str,
        agent_id: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.task_id = task_id
        self.agent_id = agent_id


class TaskNotFoundError(TaskError):
    """Raised when a task is not found."""


class TaskDependencyError(TaskError):
    """Raised when task dependencies cannot be resolved."""


class OrchestrationError(MultiAgentBuilderError):
    """Raised when orchestration encounters an error."""


class MemoryError(MultiAgentBuilderError):
    """Raised when memory operations fail."""


class SandboxError(MultiAgentBuilderError):
    """Raised when sandbox execution fails."""


class SandboxTimeoutError(SandboxError):
    """Raised when sandbox execution times out."""


class ValidationError(MultiAgentBuilderError):
    """Raised when validation fails."""


class DatabaseError(MultiAgentBuilderError):
    """Raised when database operations fail."""


class MigrationError(DatabaseError):
    """Raised when database migration fails."""