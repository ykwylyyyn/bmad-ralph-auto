from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ralph.worker.process import ClaudeOutput


@dataclass(frozen=True, slots=True)
class BackendRunInfo:
    backend: str
    model: str | None = None


class WorkerSessionHandle(Protocol):
    @property
    def pid(self) -> int | None: ...

    @property
    def was_killed(self) -> bool: ...

    @property
    def run_info(self) -> BackendRunInfo: ...

    def poll(self) -> int | None: ...

    def wait(self) -> ClaudeOutput: ...

    def kill(self) -> None: ...


class WorkerBackend(Protocol):
    @property
    def name(self) -> str: ...

    def with_context(self, *, logs_dir: object | None, worker_id: int) -> WorkerBackend: ...

    def spawn(
        self,
        worktree_path: str | object,
        prompt: str,
        *,
        env: dict[str, str] | None = None,
    ) -> WorkerSessionHandle: ...
