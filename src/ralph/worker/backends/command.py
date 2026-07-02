from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import subprocess

from ralph.worker.backends.base import BackendRunInfo, WorkerBackend, WorkerSessionHandle
from ralph.worker.errors import ProcessSpawnFailed
from ralph.worker.output_capture import StreamCapture
from ralph.worker.process import ClaudeOutput
from ralph.worker.process_sync import SyncClaudeSessionHandle


@dataclass(frozen=True, slots=True)
class CommandBackendConfig:
    name: str
    command: str
    args: tuple[str, ...] = ()
    output_format: str = "claude_json"
    model: str | None = None
    append_prompt: bool = False


@dataclass(frozen=True, slots=True)
class _CommandSessionAdapter:
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
class CommandBackend:
    """Generic CLI backend for codex, gemini, or custom commands."""

    _config: CommandBackendConfig
    _logs_dir: Path | None = None
    _worker_id: int | None = None

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def output_format(self) -> str:
        return self._config.output_format

    def with_context(self, *, logs_dir: object | None, worker_id: int) -> WorkerBackend:
        resolved_logs = Path(logs_dir) if logs_dir is not None else self._logs_dir
        return CommandBackend(self._config, logs_dir=resolved_logs, worker_id=worker_id)

    def spawn(
        self,
        worktree_path: str | object,
        prompt: str,
        *,
        env: dict[str, str] | None = None,
    ) -> WorkerSessionHandle:
        argv = [self._config.command, *self._config.args]
        if self._config.append_prompt:
            argv.append(prompt)
        else:
            argv.extend(["-p", prompt])

        spawn_env = os.environ.copy()
        if env is not None:
            spawn_env.update(env)

        try:
            process = subprocess.Popen(
                argv,
                cwd=Path(worktree_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=spawn_env,
            )
        except OSError as exc:
            raise ProcessSpawnFailed(
                f"failed to spawn {self._config.name} process in {worktree_path}: {exc}"
            ) from exc

        capture: StreamCapture | None = None
        if self._logs_dir is not None and self._worker_id is not None:
            log_path = self._logs_dir / f"worker-{self._worker_id}.log"
            capture = StreamCapture(process.stdout, process.stderr, log_path)
            capture.start()

        handle = SyncClaudeSessionHandle(process, capture=capture)
        return _CommandSessionAdapter(
            handle,
            BackendRunInfo(backend=self._config.name, model=self._config.model),
        )
