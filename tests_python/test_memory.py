from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ralph.common.db.store import StateStore
from ralph.common.models import Story, StoryState
from ralph.memory.store import CYCLE_EVENTS_KEY, MemoryStore


class MemoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = StateStore.open_in_memory()
        self.store.upsert_story(Story(id=1, title="Memory test"))
        self.memory = MemoryStore(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def test_set_and_get_context(self) -> None:
        self.memory.set_context(1, "note", {"value": 42})
        self.assertEqual(self.memory.get_context(1, "note"), {"value": 42})

    def test_append_event_accumulates(self) -> None:
        self.store.upsert_story(Story(id=2, title="Events"))
        self.memory.append_event(2, {"type": "step_complete", "step": "dev"})
        self.memory.append_event(2, {"type": "step_complete", "step": "verify"})
        events = self.memory.get_context(2, CYCLE_EVENTS_KEY)
        self.assertEqual(len(events), 2)

    def test_progress_tracks_step_index_and_completed(self) -> None:
        self.store.upsert_story(Story(id=3, title="Progress"))
        self.memory.set_step_index(3, 1)
        self.memory.add_completed_step(3, "dev")
        progress = self.memory.get_progress(3)
        self.assertEqual(progress["step_index"], 1)
        self.assertEqual(progress["completed_steps"], ["dev"])

    def test_clear_cycle_removes_keys(self) -> None:
        self.store.upsert_story(Story(id=4, title="Clear"))
        self.memory.set_step_index(4, 2)
        self.memory.set_worktree_path(4, "/tmp/worktree")
        self.memory.clear_cycle(4)
        self.assertIsNone(self.memory.get_worktree_path(4))
        self.assertEqual(self.memory.get_step_index(4), 0)


if __name__ == "__main__":
    unittest.main()
