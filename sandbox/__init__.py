"""Sandbox execution package for Autonomous Data Analyst AI."""

import logging
from typing import Optional, Protocol, runtime_checkable
from config.settings import get_settings
from schemas.execution import ExecutionResult
from sandbox.security import CodeSecurityAuditor, SecurityViolationError
from sandbox.secure_subprocess_executor import SecureSubprocessExecutor

logger = logging.getLogger(__name__)


@runtime_checkable
class SandboxExecutorProtocol(Protocol):
    """Protocol interface for sandbox execution providers."""
    def execute(self, code: str, dataset_path: str) -> ExecutionResult:
        ...


def get_sandbox_executor() -> SandboxExecutorProtocol:
    """Instantiate and return the isolated secure subprocess sandbox executor."""
    settings = get_settings()
    logger.info("Initializing SecureSubprocessExecutor sandbox.")
    return SecureSubprocessExecutor(
        timeout_seconds=settings.sandbox_timeout_seconds,
        max_memory_mb=settings.sandbox_max_memory_mb
    )


__all__ = [
    "SandboxExecutorProtocol",
    "get_sandbox_executor",
    "SecureSubprocessExecutor",
    "CodeSecurityAuditor",
    "SecurityViolationError",
]
