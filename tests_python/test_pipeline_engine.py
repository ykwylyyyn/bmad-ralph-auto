from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ralph.common.db import StateStore
from ralph.common.models import PipelineState, Story, StoryState, WorkerHealth, WorkerState
from ralph.common.db.store import WorkerRecord
from ralph.pipeline.engine import PipelineEngine
from ralph.pipeline.ingestion import build_dependency_graph


class PipelineEngineTests(unittest.TestCase):
    def test_assigns_parallel_stories_up_to_worker_limit(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=1001, title="One", state=StoryState.QUEUED))
            store.upsert_story(Story(id=1002, title="Two", state=StoryState.QUEUED))
            store.upsert_story(Story(id=1003, title="Three", state=StoryState.QUEUED))
            store.replace_story_dependencies({1001: [], 1002: [], 1003: []})

            with tempfile.TemporaryDirectory() as tmp:
                engine = PipelineEngine(store, max_workers=2, worktrees_dir=Path(tmp))
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
                engine = PipelineEngine(store, max_workers=1, worktrees_dir=Path(tmp))
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
        try:
            store.upsert_story(Story(id=4001, title="First", state=StoryState.QUEUED))
            store.upsert_story(Story(id=4002, title="Second", state=StoryState.QUEUED, dependencies=[4001]))
            store.replace_story_dependencies({4001: [], 4002: [4001]})

            with tempfile.TemporaryDirectory() as tmp:
                engine = PipelineEngine(store, max_workers=1, worktrees_dir=Path(tmp))
                engine.initialize()
                first_tick = engine.tick()
                self.assertEqual([item.story_id for item in first_tick.assignments], [4001])

                store.transition_story_state(4001, StoryState.IN_REVIEW)
                store.transition_story_state(4001, StoryState.DONE)
                store.upsert_worker(
                    WorkerRecord(1, WorkerState.IDLE, WorkerHealth.HEALTHY, str(Path(tmp) / "worker-1"))
                )

                second_tick = engine.tick()
                self.assertEqual([item.story_id for item in second_tick.assignments], [4002])
        finally:
            store.close()

    def test_dependency_graph_matches_store(self) -> None:
        stories = [
            Story(id=5001, title="A", state=StoryState.QUEUED),
            Story(id=5002, title="B", state=StoryState.QUEUED, dependencies=[5001]),
        ]
        graph = build_dependency_graph(stories)
        self.assertEqual(graph.dependency_count, 1)
        self.assertEqual(graph.edges[5002], [5001])


if __name__ == "__main__":
    unittest.main()
