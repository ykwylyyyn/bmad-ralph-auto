from __future__ import annotations

import os
from pathlib import Path
import subprocess

from .claude_cmd import resolve_claude_command
from .errors import ProcessSpawnFailed
from .output_capture import StreamCapture
from .process import ClaudeOutput


class SyncClaudeSessionHandle:
    def __init__(
        self,
        process: subprocess.Popen[bytes],
        *,
        capture: StreamCapture | None = None,
    ) -> None:
        self._process = process
        self._capture = capture
        self._killed = False

    @property
    def pid(self) -> int | None:
        return self._process.pid

    @property
    def was_killed(self) -> bool:
        return self._killed

    def poll(self) -> int | None:
        return self._process.poll()

    def wait(self) -> ClaudeOutput:
        exit_code = self._process.wait()
        if self._capture is not None:
            self._capture.set_exit_code(exit_code)
            self._capture.join()
            return self._capture.output()
        stdout, stderr = self._process.communicate()
        return ClaudeOutput(
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=exit_code,
        )

    def kill(self) -> None:
        if self._process.poll() is None:
            self._killed = True
            self._process.kill()
            self._process.wait()


class SyncClaudeProcess:
    def __init__(
        self,
        claude_bin: str | list[str] | None = None,
        *,
        logs_dir: Path | None = None,
        worker_id: int | None = None,
    ) -> None:
        if isinstance(claude_bin, list):
            self._command = claude_bin
        elif claude_bin is not None:
            self._command = [claude_bin]
        else:
            self._command = resolve_claude_command()
        self._logs_dir = logs_dir
        self._worker_id = worker_id

    def with_context(self, *, logs_dir: Path | None, worker_id: int) -> SyncClaudeProcess:
        return type(self)(
            self._command,
            logs_dir=logs_dir or self._logs_dir,
            worker_id=worker_id,
        )

    def spawn(
        self,
        worktree_path: str | Path,
        prompt: str,
        *,
        env: dict[str, str] | None = None,
    ) -> SyncClaudeSessionHandle:
        spawn_env = os.environ.copy()
        if env is not None:
            spawn_env.update(env)
        try:
            process = subprocess.Popen(
                [*self._command, "-p", "--output-format", "json", prompt],
                cwd=Path(worktree_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=spawn_env,
            )
        except OSError as exc:
            raise ProcessSpawnFailed(
                f"failed to spawn Claude process in {worktree_path}: {exc}"
            ) from exc

        capture: StreamCapture | None = None
        if self._logs_dir is not None and self._worker_id is not None:
            log_path = self._logs_dir / f"worker-{self._worker_id}.log"
            capture = StreamCapture(process.stdout, process.stderr, log_path)
            capture.start()

        return SyncClaudeSessionHandle(process, capture=capture)
