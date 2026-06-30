from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StoryState(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"


class StoryResult(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class WorkerState(StrEnum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class WorkerHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNRESPONSIVE = "unresponsive"
    UNKNOWN = "unknown"


class PipelineState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    HEALING = "healing"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETE = "complete"


class HealingLayer(StrEnum):
    STEP_RETRY = "step_retry"
    WORKER_RESTART = "worker_restart"
    DIAGNOSE = "diagnose"


@dataclass(slots=True)
class Story:
    id: int
    title: str
    state: StoryState = StoryState.QUEUED
    dependencies: list[int] = field(default_factory=list)
    worker_id: int | None = None


@dataclass(slots=True)
class SprintPlan:
    stories: list[Story] = field(default_factory=list)


@dataclass(slots=True)
class HealingAttempt:
    story_id: int
    layer: HealingLayer
    attempt: int
    reason: str


@dataclass(slots=True)
class DiagnosticReport:
    story_id: int
    root_cause: str
    recommendation: str
    suggested_fix: str
    analysis: dict[str, object] = field(default_factory=dict)
    id: int | None = None
