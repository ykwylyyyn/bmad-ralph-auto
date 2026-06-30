from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from ralph.common.db import (
    AsyncStateStore,
    InvalidTransitionError,
    StateStore,
    StoryNotFoundError,
)
from ralph.common.models import HealingAttempt, HealingLayer, Story, StoryState, WorkerHealth, WorkerState
from ralph.common.db.store import WorkerRecord


class PersistenceTests(unittest.TestCase):
    def test_wal_mode_enabled_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.open(Path(tmp) / "ralph.db")
            try:
                self.assertTrue(store.is_wal_enabled())
            finally:
                store.close()

    def test_atomic_story_transition(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=1, title="Story 1"))
            updated = store.transition_story_state(1, StoryState.IN_PROGRESS)
            self.assertEqual(updated.state, StoryState.IN_PROGRESS)

            with self.assertRaises(InvalidTransitionError):
                store.transition_story_state(1, StoryState.DONE)
            self.assertEqual(store.get_story(1).state, StoryState.IN_PROGRESS)
        finally:
            store.close()

    def test_invalid_transition_does_not_mutate_state(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=2, title="Story 2", state=StoryState.QUEUED))
            with self.assertRaises(InvalidTransitionError):
                store.transition_story_state(2, StoryState.DONE)
            self.assertEqual(store.get_story(2).state, StoryState.QUEUED)
        finally:
            store.close()

    def test_crash_recovery_reopens_last_persisted_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "ralph.db"
            store = StateStore.open(db_path)
            store.upsert_story(Story(id=3, title="Recover me"))
            store.transition_story_state(3, StoryState.IN_PROGRESS)
            store.upsert_worker(
                WorkerRecord(
                    id=1,
                    state=WorkerState.RUNNING,
                    health=WorkerHealth.HEALTHY,
                    worktree_path=str(Path(tmp) / "worktree-1"),
                    pid=4242,
                )
            )
            store.close()

            recovered = StateStore.open(db_path)
            try:
                snapshot = recovered.load_snapshot()
                self.assertEqual(len(snapshot.stories), 1)
                self.assertEqual(snapshot.stories[0].state, StoryState.IN_PROGRESS)
                self.assertEqual(len(snapshot.workers), 1)
                self.assertEqual(snapshot.workers[0].pid, 4242)
            finally:
                recovered.close()

    def test_concurrent_reads_during_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.open(Path(tmp) / "ralph.db")
            try:
                store.upsert_story(Story(id=4, title="Concurrent"))
                errors: list[BaseException] = []
                reads: list[int] = []

                def reader() -> None:
                    reader_store = StateStore.open(Path(tmp) / "ralph.db")
                    try:
                        for _ in range(20):
                            reads.append(len(reader_store.list_stories()))
                    except BaseException as exc:  # pragma: no cover - test helper
                        errors.append(exc)
                    finally:
                        reader_store.close()

                thread = threading.Thread(target=reader)
                thread.start()
                for _ in range(20):
                    store.transition_story_state(4, StoryState.IN_PROGRESS)
                    store.transition_story_state(4, StoryState.FAILED)
                    store.transition_story_state(4, StoryState.QUEUED)
                thread.join(timeout=5)
                self.assertFalse(errors)
                self.assertTrue(reads)
            finally:
                store.close()

    def test_healing_attempt_pruning_bounds_database_growth(self) -> None:
        store = StateStore.open_in_memory()
        try:
            store.upsert_story(Story(id=5, title="Healing"))
            for index in range(12):
                store.record_healing_attempt(
                    HealingAttempt(
                        story_id=5,
                        layer=HealingLayer.STEP_RETRY,
                        attempt=index + 1,
                        reason=f"attempt-{index}",
                    )
                )
            deleted = store.prune_healing_attempts(retention_days=365, max_rows=5)
            self.assertGreaterEqual(deleted, 7)
            self.assertLessEqual(len(store.list_healing_attempts(5)), 5)
        finally:
            store.close()

    def test_async_store_uses_background_thread(self) -> None:
        async def exercise() -> None:
            store = StateStore.open_in_memory()
            async_store = AsyncStateStore(store)
            try:
                await async_store.upsert_story(Story(id=6, title="Async"))
                story = await async_store.transition_story_state(6, StoryState.IN_PROGRESS)
                self.assertEqual(story.state, StoryState.IN_PROGRESS)
                snapshot = await async_store.load_snapshot()
                self.assertEqual(len(snapshot.stories), 1)
            finally:
                await async_store.close()

        asyncio.run(exercise())

    def test_missing_story_raises(self) -> None:
        store = StateStore.open_in_memory()
        try:
            with self.assertRaises(StoryNotFoundError):
                store.get_story(999)
        finally:
            store.close()


class SchemaJournalModeTests(unittest.TestCase):
    def test_schema_sets_wal_pragma_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            connection = sqlite3.connect(str(Path(tmp) / "ralph.db"))
            try:
                from ralph.common.db import apply_schema

                apply_schema(connection)
                mode = connection.execute("PRAGMA journal_mode").fetchone()
                self.assertEqual(str(mode[0]).lower(), "wal")
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
