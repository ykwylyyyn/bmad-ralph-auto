from __future__ import annotations

from dataclasses import dataclass

from ralph.common.db.store import WorkerRecord
from ralph.common.models import Story, StoryState, WorkerState


@dataclass(frozen=True, slots=True)
class SchedulerSnapshot:
    schedulable: list[Story]
    active_workers: int
    available_slots: int


class StoryScheduler:
    """Dependency-aware story scheduler with worker concurrency limits."""

    def __init__(self, max_workers: int) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.max_workers = max_workers

    def completed_story_ids(self, stories: list[Story]) -> set[int]:
        return {story.id for story in stories if story.state == StoryState.DONE}

    def schedulable_stories(self, stories: list[Story]) -> list[Story]:
        completed = self.completed_story_ids(stories)
        ready: list[Story] = []
        for story in stories:
            if story.state != StoryState.QUEUED:
                continue
            if all(dep_id in completed for dep_id in story.dependencies):
                ready.append(story)
        return sorted(ready, key=lambda item: item.id)

    def active_worker_count(self, workers: list[WorkerRecord]) -> int:
        return sum(
            1
            for worker in workers
            if worker.state in {WorkerState.RUNNING, WorkerState.STARTING}
        )

    def available_slots(self, workers: list[WorkerRecord]) -> int:
        return max(0, self.max_workers - self.active_worker_count(workers))

    def idle_workers(self, workers: list[WorkerRecord]) -> list[WorkerRecord]:
        return sorted(
            [worker for worker in workers if worker.state == WorkerState.IDLE],
            key=lambda item: item.id,
        )

    def evaluate(self, stories: list[Story], workers: list[WorkerRecord]) -> SchedulerSnapshot:
        schedulable = self.schedulable_stories(stories)
        active_workers = self.active_worker_count(workers)
        return SchedulerSnapshot(
            schedulable=schedulable,
            active_workers=active_workers,
            available_slots=max(0, self.max_workers - active_workers),
        )
