from __future__ import annotations

from dataclasses import dataclass

from ralph.common.db.store import StateStore, WorkerRecord
from ralph.common.models import StoryState, WorkerHealth, WorkerState


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    requeued_story_ids: list[int]
    reset_worker_ids: list[int]


def recover_orphaned_stories(
    store: StateStore,
    *,
    active_worker_ids: set[int],
) -> RecoveryResult:
    """Requeue stories and reset workers left active after a crash or daemon stop."""

    reset_worker_ids: list[int] = []
    for worker in store.list_workers():
        if worker.id in active_worker_ids:
            continue
        if worker.state not in {WorkerState.RUNNING, WorkerState.STARTING}:
            continue
        store.upsert_worker(
            WorkerRecord(
                id=worker.id,
                state=WorkerState.IDLE,
                health=WorkerHealth.DEGRADED,
                worktree_path=worker.worktree_path,
                pid=None,
            )
        )
        reset_worker_ids.append(worker.id)

    requeued_story_ids: list[int] = []
    for story in store.list_stories():
        if story.state not in {StoryState.IN_PROGRESS, StoryState.VERIFYING}:
            continue
        if story.worker_id is not None and story.worker_id in active_worker_ids:
            continue
        store.requeue_story(story.id)
        requeued_story_ids.append(story.id)

    if requeued_story_ids or reset_worker_ids:
        store.record_pipeline_event(
            "orphan_recovery",
            {
                "requeued_story_ids": requeued_story_ids,
                "reset_worker_ids": reset_worker_ids,
            },
        )

    return RecoveryResult(
        requeued_story_ids=requeued_story_ids,
        reset_worker_ids=reset_worker_ids,
    )
