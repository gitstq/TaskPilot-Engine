"""
Core data models for TaskPilot-CLI.
Defines Task, Pipeline, Step, and ExecutionResult structures.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """Status of a task or pipeline execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Types of pipeline steps."""
    LLM_CALL = "llm_call"
    HTTP_REQUEST = "http_request"
    SHELL_COMMAND = "shell_command"
    SCRIPT = "script"
    CONDITION = "condition"
    TRANSFORM = "transform"
    PARALLEL = "parallel"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """Configuration for an LLM backend."""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    """A single step in a pipeline."""
    name: str
    step_type: StepType = StepType.LLM_CALL
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout: float = 120.0
    condition: Optional[str] = None  # Expression to evaluate before running
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class Pipeline:
    """A task pipeline definition."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: List[Step] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    max_parallel: int = 3
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class StepResult:
    """Result of a single step execution."""
    step_name: str
    step_id: str
    status: TaskStatus = TaskStatus.PENDING
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    tokens_used: int = 0
    retry_count: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "step_id": self.step_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration": round(self.duration, 3),
            "tokens_used": self.tokens_used,
            "retry_count": self.retry_count,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": self.metadata,
        }


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    pipeline_name: str
    pipeline_id: str
    status: TaskStatus = TaskStatus.PENDING
    step_results: List[StepResult] = field(default_factory=list)
    total_duration: float = 0.0
    total_tokens: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0
    error: Optional[str] = None

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.step_results if r.status == TaskStatus.SUCCESS)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.step_results if r.status == TaskStatus.FAILED)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.step_results if r.status == TaskStatus.SKIPPED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "pipeline_id": self.pipeline_id,
            "status": self.status.value,
            "step_results": [r.to_dict() for r in self.step_results],
            "total_duration": round(self.total_duration, 3),
            "total_tokens": self.total_tokens,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "summary": {
                "total_steps": len(self.step_results),
                "success": self.success_count,
                "failed": self.failed_count,
                "skipped": self.skipped_count,
            },
        }
