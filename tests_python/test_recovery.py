from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ralph.common.db.store import StateStore, WorkerRecord
from ralph.common.models import PipelineState, Story, StoryState, WorkerHealth, WorkerState
from ralph.pipeline.engine import PipelineEngine
from ralph.pipeline.recovery import recover_orphaned_stories

from helpers import init_git_repo, worker_manager_for_repo


class RecoveryModuleTests(unittest.TestCase):
    def test_requeues_orphaned_in_progress_story(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(
                Story(id=1, title="Orphan", state=StoryState.IN_PROGRESS, worker_id=1)
            )
            store.upsert_worker(
                WorkerRecord(1, WorkerState.RUNNING, WorkerHealth.HEALTHY, "/tmp/worker-1", pid=999)
            )

            result = recover_orphaned_stories(store, active_worker_ids=set())

            self.assertEqual(result.requeued_story_ids, [1])
            self.assertEqual(result.reset_worker_ids, [1])
            story = store.get_story(1)
            self.assertEqual(story.state, StoryState.QUEUED)
            self.assertIsNone(story.worker_id)
            worker = store.get_worker(1)
            self.assertEqual(worker.state, WorkerState.IDLE)
            self.assertEqual(worker.health, WorkerHealth.DEGRADED)
            events = store.list_pipeline_events("orphan_recovery")
            self.assertEqual(len(events), 1)
        finally:
            store.close()

    def test_skips_stories_with_active_workers(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(
                Story(id=2, title="Active", state=StoryState.IN_PROGRESS, worker_id=1)
            )
            store.upsert_worker(
                WorkerRecord(1, WorkerState.RUNNING, WorkerHealth.HEALTHY, "/tmp/worker-1", pid=42)
            )

            result = recover_orphaned_stories(store, active_worker_ids={1})

            self.assertEqual(result.requeued_story_ids, [])
            self.assertEqual(result.reset_worker_ids, [])
            self.assertEqual(store.get_story(2).state, StoryState.IN_PROGRESS)
        finally:
            store.close()

    def test_requeues_verifying_story_without_worker(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(
                Story(id=3, title="Verify orphan", state=StoryState.VERIFYING, worker_id=None)
            )

            result = recover_orphaned_stories(store, active_worker_ids=set())

            self.assertEqual(result.requeued_story_ids, [3])
            self.assertEqual(store.get_story(3).state, StoryState.QUEUED)
        finally:
            store.close()


class EngineRecoveryTests(unittest.TestCase):
    def test_shutdown_requeues_in_progress_and_verifying(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            init_git_repo(root)
            store.upsert_story(
                Story(id=10, title="Running", state=StoryState.IN_PROGRESS, worker_id=1, key="1-0-run")
            )
            store.upsert_story(
                Story(id=11, title="Verifying", state=StoryState.VERIFYING, worker_id=None, key="1-1-ver")
            )
            store.replace_story_dependencies({10: [], 11: []})
            store.upsert_worker(
                WorkerRecord(1, WorkerState.RUNNING, WorkerHealth.HEALTHY, str(worktrees / "worker-1"))
            )

            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
            )
            engine.shutdown()

            self.assertEqual(store.get_story(10).state, StoryState.QUEUED)
            self.assertEqual(store.get_story(11).state, StoryState.QUEUED)
            worker = store.get_worker(1)
            self.assertEqual(worker.state, WorkerState.IDLE)
            self.assertEqual(worker.health, WorkerHealth.HEALTHY)
        finally:
            store.close()
            tempdir.cleanup()

    def test_initialize_recovers_orphans_then_resumes(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            init_git_repo(root)
            store.upsert_story(
                Story(id=20, title="Stale", state=StoryState.IN_PROGRESS, worker_id=1, key="2-0-stale")
            )
            store.replace_story_dependencies({20: []})
            store.upsert_worker(
                WorkerRecord(1, WorkerState.RUNNING, WorkerHealth.HEALTHY, str(worktrees / "worker-1"))
            )

            manager = worker_manager_for_repo(root, worktrees)
            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
                worker_manager=manager,
            )
            state = engine.initialize()
            self.assertEqual(store.get_story(20).state, StoryState.QUEUED)
            self.assertEqual(state, PipelineState.RUNNING)

            tick = engine.tick()
            self.assertEqual(len(tick.assignments), 1)
            self.assertEqual(tick.assignments[0].story_id, 20)
        finally:
            store.close()
            tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
