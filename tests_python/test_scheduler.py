from __future__ import annotations

import unittest

from ralph.common.db.store import WorkerRecord
from ralph.common.models import Story, StoryState, WorkerHealth, WorkerState
from ralph.pipeline.scheduler import StoryScheduler


class SchedulerTests(unittest.TestCase):
    def test_schedulable_stories_respect_dependencies(self) -> None:
        scheduler = StoryScheduler(max_workers=3)
        stories = [
            Story(id=1001, title="First", state=StoryState.DONE),
            Story(id=1002, title="Second", state=StoryState.QUEUED, dependencies=[1001]),
            Story(id=1003, title="Third", state=StoryState.QUEUED, dependencies=[1002]),
        ]

        schedulable = scheduler.schedulable_stories(stories)
        self.assertEqual([story.id for story in schedulable], [1002])

    def test_dependency_completion_unlocks_dependent_story(self) -> None:
        scheduler = StoryScheduler(max_workers=2)
        stories = [
            Story(id=2001, title="A", state=StoryState.DONE),
            Story(id=2002, title="B", state=StoryState.QUEUED, dependencies=[2001]),
        ]
        self.assertEqual([story.id for story in scheduler.schedulable_stories(stories)], [2002])

    def test_available_slots_respect_max_workers(self) -> None:
        scheduler = StoryScheduler(max_workers=2)
        workers = [
            WorkerRecord(1, WorkerState.RUNNING, WorkerHealth.HEALTHY, "/w1"),
            WorkerRecord(2, WorkerState.IDLE, WorkerHealth.HEALTHY, "/w2"),
            WorkerRecord(3, WorkerState.IDLE, WorkerHealth.HEALTHY, "/w3"),
        ]
        snapshot = scheduler.evaluate(
            [Story(id=3001, title="Ready", state=StoryState.QUEUED)],
            workers,
        )
        self.assertEqual(snapshot.available_slots, 1)
        self.assertEqual(snapshot.active_workers, 1)


if __name__ == "__main__":
    unittest.main()
