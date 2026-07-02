from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from ralph.common.db.store import StateStore
from ralph.common.models import HealingAttempt, HealingLayer, Story, StoryState, WorkerHealth, WorkerState
from ralph.common.db.store import WorkerRecord
from ralph.pipeline.engine import PipelineEngine
from ralph.pipeline.ingestion import build_dependency_graph
from ralph.common.models import PipelineState
from ralph.pipeline.story_cycle import StoryCycleConfig
from ralph.verifier.config import VerifierConfig
from ralph.worker.prompt import build_step_prompt, load_prompt_context

from helpers import fake_claude_process, init_git_repo, worker_manager_for_repo


class PipelineEngineTests(unittest.TestCase):
    def test_assigns_parallel_stories_up_to_worker_limit(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=1001, title="One", state=StoryState.QUEUED, key="1-1-one"))
            store.upsert_story(Story(id=1002, title="Two", state=StoryState.QUEUED, key="1-2-two"))
            store.upsert_story(Story(id=1003, title="Three", state=StoryState.QUEUED, key="1-3-three"))
            store.replace_story_dependencies({1001: [], 1002: [], 1003: []})

            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "project"
                worktrees = root / ".ralph" / "worktrees"
                init_git_repo(root)
                manager = worker_manager_for_repo(root, worktrees)
                engine = PipelineEngine(
                    store,
                    project_dir=root,
                    max_workers=2,
                    worktrees_dir=worktrees,
                    worker_manager=manager,
                )
                engine.initialize()
                tick = engine.tick()

            self.assertEqual(len(tick.assignments), 2)
            assigned_ids = {item.story_id for item in tick.assignments}
            self.assertEqual(assigned_ids, {1001, 1002})

            running = [story for story in store.list_stories() if story.state == StoryState.IN_PROGRESS]
            self.assertEqual(len(running), 2)
            for story in running:
                self.assertIsNotNone(story.worker_id)
        finally:
            store.close()

    def test_assign_story_persists_valid_transition(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=2001, title="Queued", state=StoryState.QUEUED))
            store.upsert_worker(
                WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, "/tmp/worker-1")
            )
            updated = store.assign_story_to_worker(2001, 1)
            self.assertEqual(updated.state, StoryState.IN_PROGRESS)
            self.assertEqual(updated.worker_id, 1)
        finally:
            store.close()

    def test_pipeline_completes_when_all_stories_terminal(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=3001, title="Done", state=StoryState.DONE))
            store.upsert_story(Story(id=3002, title="Failed", state=StoryState.FAILED))

            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "project"
                worktrees = root / ".ralph" / "worktrees"
                init_git_repo(root)
                engine = PipelineEngine(
                    store,
                    project_dir=root,
                    max_workers=1,
                    worktrees_dir=worktrees,
                )
                engine.initialize()
                tick = engine.tick()

            self.assertEqual(tick.pipeline_state, PipelineState.COMPLETE)
            self.assertTrue(tick.sprint_completed)
            events = store.list_pipeline_events("sprint_complete")
            self.assertEqual(len(events), 1)
            self.assertEqual(store.get_pipeline_state(), PipelineState.COMPLETE)
        finally:
            store.close()

    def test_sequential_dependencies_assign_in_order(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            init_git_repo(root)
            store.upsert_story(Story(id=4001, title="First", state=StoryState.QUEUED, key="4-1-first"))
            store.upsert_story(
                Story(id=4002, title="Second", state=StoryState.QUEUED, dependencies=[4001], key="4-2-second")
            )
            store.replace_story_dependencies({4001: [], 4002: [4001]})

            manager = worker_manager_for_repo(root, worktrees)
            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
                worker_manager=manager,
            )
            engine.initialize()
            first_tick = engine.tick()
            self.assertEqual([item.story_id for item in first_tick.assignments], [4001])

            time.sleep(0.3)
            second_tick = engine.tick()
            self.assertEqual(len(second_tick.completions), 1)
            store.transition_story_state(4001, StoryState.DONE)
            store.upsert_worker(
                WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, str(worktrees / "worker-1"))
            )

            third_tick = engine.tick()
            self.assertEqual([item.story_id for item in third_tick.assignments], [4002])
        finally:
            store.close()
            tempdir.cleanup()

    def test_dependency_graph_matches_store(self) -> None:
        stories = [
            Story(id=5001, title="A", state=StoryState.QUEUED),
            Story(id=5002, title="B", state=StoryState.QUEUED, dependencies=[5001]),
        ]
        graph = build_dependency_graph(stories)
        self.assertEqual(graph.dependency_count, 1)
        self.assertEqual(graph.edges[5002], [5001])

    def test_verifier_marks_story_done_when_checks_pass(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            init_git_repo(root)
            store.upsert_story(Story(id=6001, title="Verify me", state=StoryState.QUEUED, key="6-1-verify"))
            store.replace_story_dependencies({6001: []})

            manager = worker_manager_for_repo(root, worktrees)
            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
                worker_manager=manager,
                verifier_config=VerifierConfig(
                    enabled=True,
                    commands=(f'{sys.executable} -c "import sys; sys.exit(0)"',),
                ),
            )
            engine.initialize()
            engine.tick()
            for _ in range(20):
                time.sleep(0.15)
                engine.tick()
                if store.get_story(6001).state == StoryState.DONE:
                    break

            story = store.get_story(6001)
            self.assertEqual(story.state, StoryState.DONE)
        finally:
            store.close()
            tempdir.cleanup()

    def test_pipeline_reports_healing_when_story_has_active_retries(self) -> None:
        store = StateStore.open_in_memory()
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "project"
            worktrees = root / ".ralph" / "worktrees"
            init_git_repo(root)
            store.upsert_story(Story(id=7001, title="Healing", state=StoryState.QUEUED, key="7-1-heal"))
            store.replace_story_dependencies({7001: []})
            store.record_healing_attempt(
                HealingAttempt(
                    story_id=7001,
                    layer=HealingLayer.STEP_RETRY,
                    attempt=1,
                    reason="verification failed",
                )
            )

            engine = PipelineEngine(
                store,
                project_dir=root,
                max_workers=1,
                worktrees_dir=worktrees,
            )
            engine.initialize()
            self.assertEqual(store.get_pipeline_state(), PipelineState.HEALING)
        finally:
            store.close()
            tempdir.cleanup()

    def test_story_cycle_builds_step_prompt_with_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            skill_dir = root / ".claude" / "skills" / "bmad-bmm-dev-story"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Dev skill\nUse TDD.\n", encoding="utf-8")

            story = Story(id=8001, title="Cycle", key="8-1-cycle", acceptance_criteria=["works"])
            context = load_prompt_context(root, story, "dev")
            prompt = build_step_prompt(story, "dev", context)
            self.assertIn("cycle step `dev`", prompt)
            self.assertIn("bmad-bmm-dev-story", prompt)
            self.assertIn("Use TDD", prompt)

    def test_story_cycle_config_disabled_preserves_legacy_path(self) -> None:
        config = StoryCycleConfig().effective()
        self.assertFalse(config.enabled)


if __name__ == "__main__":
    unittest.main()
