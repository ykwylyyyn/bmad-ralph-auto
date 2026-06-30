from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Protocol

from ralph.common.db.store import StateStore, WorkerRecord
from ralph.common.models import HealingAttempt, HealingLayer, Story, StoryState, WorkerHealth, WorkerState

from .types import HealingOutcome, HealingOutcomeKind

logger = logging.getLogger(__name__)

SELF_HEALED_REASON = "self-healed"


@dataclass(frozen=True, slots=True)
class WorkerRestartRequest:
    story_id: int
    worker_id: int
    reason: str


class WorkerRestartGateway(Protocol):
    """Abstraction for killing workers and spawning fresh worktrees."""

    def kill_worker(self, worker_id: int) -> None: ...

    def destroy_worktree(self, worker_id: int) -> None: ...

    def spawn_fresh(self, worker_id: int, story: Story) -> Path: ...


def worker_restart_reason(old_worker_id: int, new_worker_id: int) -> str:
    return f"old_worker_id={old_worker_id},new_worker_id={new_worker_id}"


class Layer2WorkerRestart:
    """Layer 2 self-healing: replace failed workers with fresh worktrees."""

    def __init__(self, store: StateStore, gateway: WorkerRestartGateway) -> None:
        self._store = store
        self._gateway = gateway

    def handle_escalation(self, request: WorkerRestartRequest) -> HealingOutcome:
        story = self._store.get_story(request.story_id)
        old_worker_id = request.worker_id
        attempt_number = self._store.count_healing_attempts(
            request.story_id,
            HealingLayer.WORKER_RESTART,
        ) + 1

        self._gateway.kill_worker(old_worker_id)
        self._gateway.destroy_worktree(old_worker_id)

        restart_reason = worker_restart_reason(old_worker_id, old_worker_id)
        self._store.record_healing_attempt(
            HealingAttempt(
                story_id=request.story_id,
                layer=HealingLayer.WORKER_RESTART,
                attempt=attempt_number,
                reason=restart_reason,
            )
        )
        self._log_healing_activated(request.story_id, attempt_number)

        self._store.requeue_story(request.story_id)
        fresh_worktree = self._gateway.spawn_fresh(old_worker_id, story)
        new_worker_id = old_worker_id

        self._store.upsert_worker(
            WorkerRecord(
                id=new_worker_id,
                state=WorkerState.RUNNING,
                health=WorkerHealth.HEALTHY,
                worktree_path=str(fresh_worktree),
                pid=None,
            )
        )
        self._store.assign_story_to_worker(request.story_id, new_worker_id)

        return HealingOutcome(
            kind=HealingOutcomeKind.RESTART,
            story_id=request.story_id,
            worker_id=new_worker_id,
            attempt=attempt_number,
            reason=request.reason,
            old_worker_id=old_worker_id,
            new_worker_id=new_worker_id,
            worktree_path=str(fresh_worktree),
        )

    def handle_restart_failure(self, request: WorkerRestartRequest) -> HealingOutcome:
        return HealingOutcome(
            kind=HealingOutcomeKind.ESCALATE_LAYER3,
            story_id=request.story_id,
            worker_id=request.worker_id,
            reason=request.reason,
        )

    def handle_restart_success(self, story_id: int, worker_id: int) -> HealingOutcome:
        restarts = self._store.count_healing_attempts(story_id, HealingLayer.WORKER_RESTART)
        if restarts == 0:
            return HealingOutcome(
                kind=HealingOutcomeKind.SELF_HEALED,
                story_id=story_id,
                worker_id=worker_id,
            )

        self._store.record_healing_attempt(
            HealingAttempt(
                story_id=story_id,
                layer=HealingLayer.WORKER_RESTART,
                attempt=restarts,
                reason=SELF_HEALED_REASON,
            )
        )
        self._store.set_story_state(story_id, StoryState.DONE)
        return HealingOutcome(
            kind=HealingOutcomeKind.SELF_HEALED,
            story_id=story_id,
            worker_id=worker_id,
            attempt=restarts,
            reason=SELF_HEALED_REASON,
        )

    def _log_healing_activated(self, story_id: int, attempt: int) -> None:
        logger.warning(
            "healing activated",
            extra={
                "story_id": story_id,
                "attempt": attempt,
                "layer": HealingLayer.WORKER_RESTART.value,
            },
        )
