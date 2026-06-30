from ralph.common import RalphError


class WorkerError(RalphError):
    """Base exception for worker process failures."""


class ProcessSpawnFailed(WorkerError):
    pass


class ProcessTimeout(WorkerError):
    pass


class OutputParseFailed(WorkerError):
    pass
