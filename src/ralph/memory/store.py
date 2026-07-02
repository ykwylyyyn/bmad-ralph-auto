from __future__ import annotations

from typing import Any

from ralph.common.db.store import StateStore

CYCLE_STEP_INDEX_KEY = "cycle.step_index"
CYCLE_COMPLETED_KEY = "cycle.completed_steps"
CYCLE_WORKTREE_KEY = "cycle.worktree_path"
CYCLE_EVENTS_KEY = "cycle.events"


class MemoryStore:
    """Story-scoped context persisted across cycle steps and worker sessions."""

    def __init__(self, store: StateStore) -> None:
        self._store = store

    def get_context(self, story_id: int, key: str) -> Any | None:
        return self._store.get_story_memory(story_id, key)

    def set_context(self, story_id: int, key: str, value: object) -> None:
        self._store.set_story_memory(story_id, key, value)

    def append_event(self, story_id: int, event: dict[str, object]) -> None:
        events = self.get_context(story_id, CYCLE_EVENTS_KEY)
        if not isinstance(events, list):
            events = []
        events.append(event)
        self.set_context(story_id, CYCLE_EVENTS_KEY, events)

    def get_progress(self, story_id: int) -> dict[str, object]:
        step_index = self.get_context(story_id, CYCLE_STEP_INDEX_KEY)
        completed = self.get_context(story_id, CYCLE_COMPLETED_KEY)
        events = self.get_context(story_id, CYCLE_EVENTS_KEY)
        return {
            "step_index": int(step_index) if isinstance(step_index, int) else 0,
            "completed_steps": list(completed) if isinstance(completed, list) else [],
            "events": list(events) if isinstance(events, list) else [],
        }

    def get_step_index(self, story_id: int) -> int:
        value = self.get_context(story_id, CYCLE_STEP_INDEX_KEY)
        return int(value) if isinstance(value, int) else 0

    def set_step_index(self, story_id: int, index: int) -> None:
        self.set_context(story_id, CYCLE_STEP_INDEX_KEY, index)

    def get_completed_steps(self, story_id: int) -> list[str]:
        value = self.get_context(story_id, CYCLE_COMPLETED_KEY)
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    def add_completed_step(self, story_id: int, step: str) -> None:
        completed = self.get_completed_steps(story_id)
        if step not in completed:
            completed.append(step)
        self.set_context(story_id, CYCLE_COMPLETED_KEY, completed)

    def get_worktree_path(self, story_id: int) -> str | None:
        value = self.get_context(story_id, CYCLE_WORKTREE_KEY)
        return str(value) if isinstance(value, str) and value else None

    def set_worktree_path(self, story_id: int, path: str) -> None:
        self.set_context(story_id, CYCLE_WORKTREE_KEY, path)

    def clear_cycle(self, story_id: int) -> None:
        for key in (
            CYCLE_STEP_INDEX_KEY,
            CYCLE_COMPLETED_KEY,
            CYCLE_WORKTREE_KEY,
            CYCLE_EVENTS_KEY,
        ):
            self._store.delete_story_memory(story_id, key)
