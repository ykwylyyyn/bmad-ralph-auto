from ralph.common import RalphError


class WorkerError(RalphError):
    """Base exception for worker process failures."""


class ProcessSpawnFailed(WorkerError):
    pass


class ProcessTimeout(WorkerError):
    pass


class OutputParseFailed(WorkerError):
    pass


class WorktreeError(WorkerError):
    pass


class WorkerSpawnError(WorkerError):
    def __init__(self, worker_id: int, story_id: int, reason: str) -> None:
        super().__init__(f"worker {worker_id} failed to spawn story {story_id}: {reason}")
        self.worker_id = worker_id
        self.story_id = story_id
        self.reason = reason
