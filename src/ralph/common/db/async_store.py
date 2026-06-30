from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Self

from ralph.common.models import HealingAttempt, Story, StoryState

from .store import PipelineSnapshot, StateStore, WorkerRecord


class AsyncStateStore:
    """Async wrapper around StateStore using asyncio.to_thread for blocking SQLite I/O."""

    def __init__(self, store: StateStore) -> None:
        self._store = store

    @classmethod
    async def open(cls, database_path: str | Path) -> Self:
        store = await asyncio.to_thread(StateStore.open, database_path)
        return cls(store)

    async def close(self) -> None:
        await asyncio.to_thread(self._store.close)

    async def is_wal_enabled(self) -> bool:
        return await asyncio.to_thread(self._store.is_wal_enabled)

    async def upsert_story(self, story: Story) -> Story:
        return await asyncio.to_thread(self._store.upsert_story, story)

    async def get_story(self, story_id: int) -> Story:
        return await asyncio.to_thread(self._store.get_story, story_id)

    async def list_stories(self) -> list[Story]:
        return await asyncio.to_thread(self._store.list_stories)

    async def transition_story_state(self, story_id: int, to_state: StoryState) -> Story:
        return await asyncio.to_thread(self._store.transition_story_state, story_id, to_state)

    async def upsert_worker(self, worker: WorkerRecord) -> WorkerRecord:
        return await asyncio.to_thread(self._store.upsert_worker, worker)

    async def get_worker(self, worker_id: int) -> WorkerRecord:
        return await asyncio.to_thread(self._store.get_worker, worker_id)

    async def list_workers(self) -> list[WorkerRecord]:
        return await asyncio.to_thread(self._store.list_workers)

    async def record_healing_attempt(self, attempt: HealingAttempt) -> None:
        await asyncio.to_thread(self._store.record_healing_attempt, attempt)

    async def load_snapshot(self) -> PipelineSnapshot:
        return await asyncio.to_thread(self._store.load_snapshot)

    async def prune_healing_attempts(self, **kwargs: object) -> int:
        return await asyncio.to_thread(self._store.prune_healing_attempts, **kwargs)
