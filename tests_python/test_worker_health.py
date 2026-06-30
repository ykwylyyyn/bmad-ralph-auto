from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import unittest

from ralph.common.db import StateStore
from ralph.common.db.store import WorkerRecord
from ralph.common.models import Story, StoryState, WorkerHealth, WorkerState
from ralph.pipeline.engine import PipelineEngine
from ralph.worker import SyncClaudeProcess, WorkerManager
from ralph.worker.health import classify_exit, pid_is_alive
from ralph.worker.process import ClaudeOutput

from helpers import fake_claude_process, init_git_repo


class HealthUtilityTests(unittest.TestCase):
    def test_classify_exit_distinguishes_crash_from_claude_failure(self) -> None:
        structured_failure = ClaudeOutput(
            stdout='{"type":"result","subtype":"error_max_turns","is_error":true}',
            stderr="",
            exit_code=1,
        )
        crash = ClaudeOutput(stdout="", stderr="segfault", exit_code=137)

        self.assertEqual(classify_exit(structured_failure, killed=False), "completed")
        self.assertEqual(classify_exit(crash, killed=False), "unexpected")
        self.assertEqual(classify_exit(crash, killed=True), "killed")

    def test_pid_is_alive_for_current_process(self) -> None:
        self.assertTrue(pid_is_alive(os.getpid()))
        self.assertFalse(pid_is_alive(None))
        self.assertFalse(pid_is_alive(999_999_999))


class WorkerHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.repo = self.root / "project"
        self.worktrees = self.root / ".ralph" / "worktrees"
        self.logs = self.root / ".ralph" / "logs"
        self.worktrees.mkdir(parents=True)
        self.logs.mkdir(parents=True)
        init_git_repo(self.repo)
        self.manager = WorkerManager(
            self.repo,
            self.worktrees,
            logs_dir=self.logs,
            process_factory=fake_claude_process(),
        )

    def tearDown(self) -> None:
        self.manager.shutdown()
        self.tempdir.cleanup()

    def test_output_capture_writes_log_file(self) -> None:
        story = Story(id=1001, title="Log Story", key="1-1-log-story")
        self.manager.spawn_for_story(1, story)
        self._wait_for_exits(count=1)

        log_file = self.logs / "worker-1.log"
        self.assertTrue(log_file.exists())
        self.assertIn(b"[stdout]", log_file.read_bytes())

    def test_kill_worker_only_affects_target(self) -> None:
        hang_script = Path(__file__).resolve().parent / "fixtures" / "fake_claude.py"

        class HangThenSuccess(SyncClaudeProcess):
            def spawn(self, worktree_path, prompt, **kwargs):
                return super().spawn(
                    worktree_path,
                    prompt,
                    env={"FAKE_CLAUDE_MODE": "hang"},
                )

        manager = WorkerManager(
            self.repo,
            self.worktrees,
            logs_dir=self.logs,
            process_factory=HangThenSuccess([sys.executable, str(hang_script)]),
        )
        try:
            first = manager.spawn_for_story(1, Story(id=1001, title="One", key="1-1-one"))
            second = manager.spawn_for_story(2, Story(id=1002, title="Two", key="1-2-two"))
            self.assertIsNotNone(first.session.pid)
            self.assertIsNotNone(second.session.pid)

            killed = manager.kill_worker(1)
            self.assertIsNotNone(killed)
            self.assertEqual(killed.exit_kind, "killed")
            self.assertIn(2, manager.active_sessions)
            self.assertNotIn(1, manager.active_sessions)

            manager.kill_worker(2)
        finally:
            manager.shutdown()

    def test_unexpected_exit_cleans_up_worktree(self) -> None:
        script = Path(__file__).resolve().parent / "fixtures" / "fake_claude.py"

        class CrashProcess(SyncClaudeProcess):
            def spawn(self, worktree_path, prompt, **kwargs):
                return super().spawn(
                    worktree_path,
                    prompt,
                    env={"FAKE_CLAUDE_MODE": "crash"},
                )

        manager = WorkerManager(
            self.repo,
            self.worktrees,
            logs_dir=self.logs,
            process_factory=CrashProcess([sys.executable, str(script)]),
        )
        try:
            active = manager.spawn_for_story(1, Story(id=1001, title="Crash", key="1-1-crash"))
            worktree = active.worktree_path
            exits = self._wait_for_exits(manager=manager, count=1)
            self.assertEqual(exits[0].exit_kind, "unexpected")
            self.assertFalse(worktree.exists())
        finally:
            manager.shutdown()

    def test_check_health_reports_running_workers(self) -> None:
        hang_script = Path(__file__).resolve().parent / "fixtures" / "fake_claude.py"

        class HangProcess(SyncClaudeProcess):
            def spawn(self, worktree_path, prompt, **kwargs):
                return super().spawn(
                    worktree_path,
                    prompt,
                    env={"FAKE_CLAUDE_MODE": "hang"},
                )

        manager = WorkerManager(
            self.repo,
            self.worktrees,
            logs_dir=self.logs,
            process_factory=HangProcess([sys.executable, str(hang_script)]),
        )
        try:
            manager.spawn_for_story(1, Story(id=1001, title="Hang", key="1-1-hang"))
            reports = manager.check_health()
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0].health, WorkerHealth.HEALTHY)
            self.assertTrue(reports[0].is_running)
            manager.kill_worker(1)
        finally:
            manager.shutdown()

    def _wait_for_exits(self, count: int = 1, timeout: float = 3.0, manager: WorkerManager | None = None):
        manager = manager or self.manager
        deadline = time.monotonic() + timeout
        exits: list = []
        while time.monotonic() < deadline:
            exits = manager.poll_exits()
            if len(exits) >= count:
                return exits
            time.sleep(0.05)
        return exits


class WorkerHealthEngineTests(unittest.TestCase):
    def test_unexpected_exit_returns_story_to_queue_and_logs_event(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            logs = root / ".ralph" / "logs"
            worktrees.mkdir(parents=True)
            logs.mkdir(parents=True)
            init_git_repo(root)

            store.upsert_story(Story(id=1001, title="Crash", state=StoryState.QUEUED, key="1-1-crash"))
            store.replace_story_dependencies({1001: []})
            store.upsert_worker(
                WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, str(worktrees / "worker-1"))
            )

            script = Path(__file__).resolve().parent / "fixtures" / "fake_claude.py"

            class CrashProcess(SyncClaudeProcess):
                def spawn(self, worktree_path, prompt, **kwargs):
                    return super().spawn(
                        worktree_path,
                        prompt,
                        env={"FAKE_CLAUDE_MODE": "crash"},
                    )

            manager = WorkerManager(
                root, worktrees, logs_dir=logs, process_factory=CrashProcess([sys.executable, str(script)])
            )
            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
                logs_dir=logs,
                worker_manager=manager,
            )
            engine.initialize()
            engine.tick()
            time.sleep(0.5)
            second = engine.tick()

            self.assertEqual(len(second.worker_failures), 1)
            story = store.get_story(1001)
            self.assertEqual(story.state, StoryState.QUEUED)
            events = store.list_pipeline_events("worker_exit_unexpected")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["payload"]["worker_id"], 1)
        finally:
            store.close()
            tempdir.cleanup()

    def test_failed_worker_is_replaced_with_fresh_worktree(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            logs = root / ".ralph" / "logs"
            worktrees.mkdir(parents=True)
            logs.mkdir(parents=True)
            init_git_repo(root)

            store.upsert_story(Story(id=1001, title="Crash", state=StoryState.QUEUED, key="1-1-crash"))
            store.replace_story_dependencies({1001: []})
            store.upsert_worker(
                WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, str(worktrees / "worker-1"))
            )

            script = Path(__file__).resolve().parent / "fixtures" / "fake_claude.py"
            modes = iter(["crash", "success"])

            class ModeProcess(SyncClaudeProcess):
                def spawn(self, worktree_path, prompt, **kwargs):
                    return super().spawn(
                        worktree_path,
                        prompt,
                        env={"FAKE_CLAUDE_MODE": next(modes)},
                    )

            manager = WorkerManager(
                root, worktrees, logs_dir=logs, process_factory=ModeProcess([sys.executable, str(script)])
            )
            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
                logs_dir=logs,
                worker_manager=manager,
            )
            engine.initialize()
            engine.tick()
            time.sleep(0.5)
            second = engine.tick()
            self.assertEqual(len(second.worker_failures), 1)

            story = store.get_story(1001)
            deadline = time.monotonic() + 5.0
            while story.state != StoryState.IN_REVIEW and time.monotonic() < deadline:
                time.sleep(0.3)
                engine.tick()
                story = store.get_story(1001)

            self.assertEqual(story.state, StoryState.IN_REVIEW)
            worker = store.get_worker(1)
            self.assertEqual(worker.state, WorkerState.IDLE)
        finally:
            store.close()
            tempdir.cleanup()

    def test_kill_worker_via_engine_updates_story_and_records_event(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            logs = root / ".ralph" / "logs"
            worktrees.mkdir(parents=True)
            logs.mkdir(parents=True)
            init_git_repo(root)

            store.upsert_story(Story(id=1001, title="Hang", state=StoryState.QUEUED, key="1-1-hang"))
            store.replace_story_dependencies({1001: []})
            store.upsert_worker(
                WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, str(worktrees / "worker-1"))
            )

            script = Path(__file__).resolve().parent / "fixtures" / "fake_claude.py"

            class HangProcess(SyncClaudeProcess):
                def spawn(self, worktree_path, prompt, **kwargs):
                    return super().spawn(
                        worktree_path,
                        prompt,
                        env={"FAKE_CLAUDE_MODE": "hang"},
                    )

            manager = WorkerManager(
                root, worktrees, logs_dir=logs, process_factory=HangProcess([sys.executable, str(script)])
            )
            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
                logs_dir=logs,
                worker_manager=manager,
            )
            engine.initialize()
            engine.tick()
            self.assertTrue(engine.kill_worker(1))

            story = store.get_story(1001)
            self.assertEqual(story.state, StoryState.QUEUED)
            events = store.list_pipeline_events("worker_killed")
            self.assertEqual(len(events), 1)
        finally:
            store.close()
            tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
