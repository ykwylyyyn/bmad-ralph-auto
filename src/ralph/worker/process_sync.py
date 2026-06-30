from __future__ import annotations

import os
from pathlib import Path
import subprocess

from .errors import ProcessSpawnFailed
from .process import ClaudeOutput


class SyncClaudeSessionHandle:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process

    @property
    def pid(self) -> int | None:
        return self._process.pid

    def poll(self) -> int | None:
        return self._process.poll()

    def wait(self) -> ClaudeOutput:
        stdout, stderr = self._process.communicate()
        return ClaudeOutput(
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=self._process.returncode or 0,
        )

    def kill(self) -> None:
        if self._process.poll() is None:
            self._process.kill()
            self._process.wait()


class SyncClaudeProcess:
    def __init__(self, claude_bin: str | list[str] | None = None) -> None:
        if isinstance(claude_bin, list):
            self._command = claude_bin
        elif claude_bin is not None:
            self._command = [claude_bin]
        else:
            self._command = [os.environ.get("RALPH_CLAUDE_BIN", "claude")]

    def spawn(self, worktree_path: str | Path, prompt: str) -> SyncClaudeSessionHandle:
        try:
            process = subprocess.Popen(
                [*self._command, "-p", "--output-format", "json", prompt],
                cwd=Path(worktree_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise ProcessSpawnFailed(
                f"failed to spawn Claude process in {worktree_path}: {exc}"
            ) from exc
        return SyncClaudeSessionHandle(process)
