from __future__ import annotations


class StoreError(Exception):
    """Base class for state store errors."""


class StoryNotFoundError(StoreError):
    def __init__(self, story_id: int) -> None:
        super().__init__(f"story {story_id} not found")
        self.story_id = story_id


class WorkerNotFoundError(StoreError):
    def __init__(self, worker_id: int) -> None:
        super().__init__(f"worker {worker_id} not found")
        self.worker_id = worker_id
