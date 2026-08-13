"""Code execution sandbox abstraction."""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nvidia_multi_agent_builder.config.logging import get_logger
from nvidia_multi_agent_builder.config.settings import settings
from nvidia_multi_agent_builder.core.exceptions import SandboxError, SandboxTimeoutError

logger = get_logger(__name__)


@dataclass
class SandboxResult:
    """Result of sandbox execution."""

    stdout: str
    stderr: str
    return_code: int
    execution_time_ms: float
    timed_out: bool = False


@dataclass
class SandboxLimits:
    """Resource limits for sandbox execution."""

    timeout_seconds: int = 30
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0


class Sandbox(ABC):
    """Abstract sandbox interface."""

    @abstractmethod
    async def execute(
        self,
        command: str,
        working_dir: Path | None = None,
        environment: dict[str, str] | None = None,
        limits: SandboxLimits | None = None,
    ) -> SandboxResult:
        """Execute a command in the sandbox."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up sandbox resources."""
        pass


class ProcessSandbox(Sandbox):
    """Process-based sandbox (limited isolation)."""

    def __init__(self):
        self._processes: list[subprocess.Popen] = []

    async def execute(
        self,
        command: str,
        working_dir: Path | None = None,
        environment: dict[str, str] | None = None,
        limits: SandboxLimits | None = None,
    ) -> SandboxResult:
        limits = limits or SandboxLimits(timeout_seconds=settings.sandbox_timeout)
        working_dir = working_dir or Path.cwd()
        env = {**os.environ, **(environment or {})}

        logger.debug("sandbox_execute", command=command, working_dir=str(working_dir))

        start_time = asyncio.get_event_loop().time()

        try:
            process = await asyncio.create_subprocess_exec(
                *shlex.split(command),
                cwd=working_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes.append(process)

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=limits.timeout_seconds,
                )
                execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                return SandboxResult(
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    return_code=process.returncode or 0,
                    execution_time_ms=execution_time_ms,
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                return SandboxResult(
                    stdout="",
                    stderr=f"Execution timed out after {limits.timeout_seconds}s",
                    return_code=-1,
                    execution_time_ms=execution_time_ms,
                    timed_out=True,
                )
        except Exception as e:
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error("sandbox_execution_error", command=command, error=str(e))
            return SandboxResult(
                stdout="",
                stderr=str(e),
                return_code=-1,
                execution_time_ms=execution_time_ms,
            )
        finally:
            if process in self._processes:
                self._processes.remove(process)

    async def cleanup(self) -> None:
        """Kill all running processes."""
        for process in self._processes:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
        self._processes.clear()


class DockerSandbox(Sandbox):
    """Docker-based sandbox (strong isolation)."""

    def __init__(self):
        self._containers: list[str] = []

    async def execute(
        self,
        command: str,
        working_dir: Path | None = None,
        environment: dict[str, str] | None = None,
        limits: SandboxLimits | None = None,
    ) -> SandboxResult:
        limits = limits or SandboxLimits(timeout_seconds=settings.sandbox_timeout)
        working_dir = working_dir or Path.cwd()
        container_id = str(uuid.uuid4())[:12]

        # Build docker command
        docker_cmd = [
            "docker", "run", "--rm",
            "--name", f"sandbox-{container_id}",
            "--memory", f"{limits.memory_limit_mb}m",
            "--cpus", str(limits.cpu_limit),
            "--network", "none",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=100m",
            "-v", f"{working_dir}:/workspace:ro",
            "-w", "/workspace",
        ]

        if environment:
            for key, value in environment.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

        docker_cmd.extend([settings.docker_image, "sh", "-c", command])

        logger.debug("docker_sandbox_execute", container_id=container_id, command=command)

        start_time = asyncio.get_event_loop().time()

        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._containers.append(container_id)

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=limits.timeout_seconds,
                )
                execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                return SandboxResult(
                    stdout=stdout.decode("utf-8", errors="replace"),
                    stderr=stderr.decode("utf-8", errors="replace"),
                    return_code=process.returncode or 0,
                    execution_time_ms=execution_time_ms,
                )
            except TimeoutError:
                # Kill container
                kill_process = await asyncio.create_subprocess_exec(
                    "docker", "kill", f"sandbox-{container_id}",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await kill_process.wait()
                execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                return SandboxResult(
                    stdout="",
                    stderr=f"Execution timed out after {limits.timeout_seconds}s",
                    return_code=-1,
                    execution_time_ms=execution_time_ms,
                    timed_out=True,
                )
        except Exception as e:
            execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error("docker_sandbox_error", container_id=container_id, error=str(e))
            return SandboxResult(
                stdout="",
                stderr=str(e),
                return_code=-1,
                execution_time_ms=execution_time_ms,
            )
        finally:
            if container_id in self._containers:
                self._containers.remove(container_id)

    async def cleanup(self) -> None:
        """Kill all running containers."""
        for container_id in self._containers:
            try:
                process = await asyncio.create_subprocess_exec(
                    "docker", "kill", f"sandbox-{container_id}",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await process.wait()
            except Exception:
                pass
        self._containers.clear()


class NoOpSandbox(Sandbox):
    """No-op sandbox for testing."""

    async def execute(
        self,
        command: str,
        working_dir: Path | None = None,
        environment: dict[str, str] | None = None,
        limits: SandboxLimits | None = None,
    ) -> SandboxResult:
        logger.warning("noop_sandbox_execute", command=command)
        return SandboxResult(
            stdout=f"[NOOP] Would execute: {command}",
            stderr="",
            return_code=0,
            execution_time_ms=0,
        )

    async def cleanup(self) -> None:
        pass


def create_sandbox(sandbox_type: str | None = None) -> Sandbox:
    """Factory function to create sandbox based on configuration."""
    sandbox_type = sandbox_type or settings.sandbox_type

    if sandbox_type == "docker":
        return DockerSandbox()
    elif sandbox_type == "process":
        return ProcessSandbox()
    elif sandbox_type == "none":
        return NoOpSandbox()
    else:
        raise ValueError(f"Unknown sandbox type: {sandbox_type}")