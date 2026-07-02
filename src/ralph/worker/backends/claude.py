from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ralph.worker.backends.base import BackendRunInfo, WorkerBackend, WorkerSessionHandle
from ralph.worker.process import ClaudeOutput
from ralph.worker.process_sync import SyncClaudeProcess, SyncClaudeSessionHandle


@dataclass(frozen=True, slots=True)
class _ClaudeSessionAdapter:
    _handle: SyncClaudeSessionHandle
    _run_info: BackendRunInfo

    @property
    def pid(self) -> int | None:
        return self._handle.pid

    @property
    def was_killed(self) -> bool:
        return self._handle.was_killed

    @property
    def run_info(self) -> BackendRunInfo:
        return self._run_info

    def poll(self) -> int | None:
        return self._handle.poll()

    def wait(self) -> ClaudeOutput:
        return self._handle.wait()

    def kill(self) -> None:
        self._handle.kill()


@dataclass(slots=True)
class ClaudeBackend:
    """Claude CLI backend with JSON output format."""

    _command: list[str] | None = None
    _logs_dir: Path | None = None
    _worker_id: int | None = None
    _model_label: str | None = "claude"
    _process: SyncClaudeProcess | None = None

    @property
    def name(self) -> str:
        return "claude"

    def with_context(self, *, logs_dir: object | None, worker_id: int) -> WorkerBackend:
        resolved_logs = Path(logs_dir) if logs_dir is not None else self._logs_dir
        return ClaudeBackend(
            _command=self._command,
            _logs_dir=resolved_logs,
            _worker_id=worker_id,
            _model_label=self._model_label,
            _process=self._process.with_context(logs_dir=resolved_logs, worker_id=worker_id)
            if self._process is not None
            else None,
        )

    def spawn(
        self,
        worktree_path: str | object,
        prompt: str,
        *,
        env: dict[str, str] | None = None,
    ) -> WorkerSessionHandle:
        process = self._process or SyncClaudeProcess(
            self._command,
            logs_dir=self._logs_dir,
            worker_id=self._worker_id,
        )
        handle = process.spawn(worktree_path, prompt, env=env)
        return _ClaudeSessionAdapter(
            handle,
            BackendRunInfo(backend=self.name, model=self._model_label),
        )

    @classmethod
    def from_process(cls, process: SyncClaudeProcess) -> ClaudeBackend:
        return cls(
            _command=process._command,
            _logs_dir=process._logs_dir,
            _worker_id=process._worker_id,
            _process=process,
        )
