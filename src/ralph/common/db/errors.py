from __future__ import annotations

from ralph.common.errors import RalphError


class DatabaseError(RalphError):
    """Base exception for SQLite persistence errors."""


class StoryNotFoundError(DatabaseError):
    def __init__(self, story_id: int) -> None:
        super().__init__(f"story not found: {story_id}")
        self.story_id = story_id


class WorkerNotFoundError(DatabaseError):
    def __init__(self, worker_id: int) -> None:
        super().__init__(f"worker not found: {worker_id}")
        self.worker_id = worker_id


class InvalidTransitionError(DatabaseError):
    def __init__(self, story_id: int, from_state: str, to_state: str) -> None:
        super().__init__(f"invalid story transition for {story_id}: {from_state} -> {to_state}")
        self.story_id = story_id
        self.from_state = from_state
        self.to_state = to_state


class ConcurrentModificationError(DatabaseError):
    def __init__(self, story_id: int, expected_state: str) -> None:
        super().__init__(f"story {story_id} state changed concurrently (expected {expected_state})")
        self.story_id = story_id
        self.expected_state = expected_state


class StoryAssignmentError(DatabaseError):
    def __init__(self, story_id: int, message: str) -> None:
        super().__init__(f"cannot assign story {story_id}: {message}")
        self.story_id = story_id
