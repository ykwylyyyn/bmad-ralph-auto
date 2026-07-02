from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from ralph.common.db import StateStore
from ralph.common.models import Story, StoryState, WorkerHealth, WorkerState
from ralph.common.db.store import WorkerRecord
from ralph.pipeline.engine import PipelineEngine
from ralph.worker import SyncClaudeProcess, WorkerManager

from helpers import fake_claude_process, init_git_repo, worker_manager_for_repo


class WorkerManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.repo = self.root / "project"
        self.repo.mkdir()
        self.worktrees = self.root / ".ralph" / "worktrees"
        self.worktrees.mkdir(parents=True)
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "ralph@test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Ralph"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.repo, check=True, capture_output=True)
        self.manager = worker_manager_for_repo(self.repo, self.worktrees)

    def tearDown(self) -> None:
        self.manager.shutdown()
        self.tempdir.cleanup()

    def test_spawn_creates_isolated_worktree_and_completes(self) -> None:
        story = Story(id=1001, title="Demo Story", key="1-1-demo-story")
        active = self.manager.spawn_for_story(1, story)
        self.assertTrue(active.worktree_path.exists())
        self.assertEqual(active.branch, "ralph/story-1001-demo-story")
        self.assertIsNotNone(active.session.pid)

        completions = self._wait_for_completions()
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].result.kind, "success")
        self.manager.release_worktree(completions[0])
        self.assertFalse(active.worktree_path.exists())

    def test_concurrent_workers_use_separate_worktrees(self) -> None:
        first = self.manager.spawn_for_story(
            1, Story(id=1001, title="One", key="1-1-one")
        )
        second = self.manager.spawn_for_story(
            2, Story(id=1002, title="Two", key="1-2-two")
        )
        self.assertNotEqual(first.worktree_path, second.worktree_path)
        self.assertNotEqual(first.branch, second.branch)
        completions = self._wait_for_completions(count=2)
        for completion in completions:
            self.manager.release_worktree(completion)

    def _wait_for_completions(self, count: int = 1, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        completions: list = []
        while time.monotonic() < deadline:
            completions = self.manager.poll_completions()
            if len(completions) >= count:
                return completions
            time.sleep(0.05)
        return completions


class WorkerEngineIntegrationTests(unittest.TestCase):
    def test_spawn_failure_returns_story_to_queue(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=1001, title="Demo", state=StoryState.QUEUED, key="1-1-demo"))
            store.replace_story_dependencies({1001: []})
            store.upsert_worker(
                WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, "/tmp/worker-1")
            )

            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "not-a-git-repo"
                root.mkdir()
                worktrees = root / ".ralph" / "worktrees"
                worktrees.mkdir(parents=True)
                manager = WorkerManager(root, worktrees, process_factory=SyncClaudeProcess(["false"]))
                engine = PipelineEngine(
                    store,
                    project_dir=root,
                    max_workers=1,
                    worktrees_dir=worktrees,
                    worker_manager=manager,
                )
                engine.initialize()
                tick = engine.tick()

            self.assertEqual(len(tick.spawn_failures), 1)
            story = store.get_story(1001)
            self.assertEqual(story.state, StoryState.QUEUED)
            self.assertIsNone(story.worker_id)
        finally:
            store.close()

    def test_successful_worker_moves_story_to_in_review(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            root.mkdir()
            worktrees = root / ".ralph" / "worktrees"
            worktrees.mkdir(parents=True)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "ralph@test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Ralph"], cwd=root, check=True)
            (root / "README.md").write_text("demo\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

            store.upsert_story(
                Story(id=1001, title="Demo", state=StoryState.QUEUED, key="1-1-demo")
            )
            store.replace_story_dependencies({1001: []})
            store.upsert_worker(
                WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, str(worktrees / "worker-1"))
            )

            fake_claude = fake_claude_process()
            manager = WorkerManager(root, worktrees, process_factory=fake_claude)
            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
                worker_manager=manager,
            )
            engine.initialize()
            first_tick = engine.tick()
            self.assertEqual(len(first_tick.assignments), 1)

            time.sleep(0.3)
            second_tick = engine.tick()
            self.assertEqual(len(second_tick.completions), 1)
            story = store.get_story(1001)
            self.assertEqual(story.state, StoryState.IN_REVIEW)
            worker = store.get_worker(1)
            self.assertEqual(worker.state, WorkerState.IDLE)
        finally:
            store.close()
            tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
