"""Shared Pydantic models for event payloads exchanged across the swarm."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPayload(BaseModel):
    """Canonical message shape carried on the RabbitMQ task_queue."""

    job_id: str = Field(..., description="Identifier for the parent job/goal")
    task_id: str = Field(..., description="Identifier for this discrete task")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    payload: dict[str, Any] = Field(default_factory=dict, description="Task-specific input data")
    agent_thought: Optional[str] = Field(
        default=None, description="Free-text reasoning/log emitted by the agent"
    )


class AgentLogEvent(BaseModel):
    """Canonical message shape published on the Redis `agent_logs` Pub/Sub channel."""

    job_id: str
    task_id: str
    status: TaskStatus
    message: str
    agent_thought: Optional[str] = None


class TaskStep(BaseModel):
    """A single discrete step in an LLM-generated plan."""

    step: str = Field(..., description="Short imperative description of the step, e.g. 'Research X'")
    detail: str = Field(default="", description="Additional detail or sub-instructions for the step")


class TaskPlan(BaseModel):
    """Structured-output target for the Planner's LLM call."""

    steps: list[TaskStep] = Field(
        ..., description="Ordered list of 2-6 discrete steps that accomplish the user's goal"
    )
