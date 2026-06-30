from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .errors import ProcessSpawnFailed


class OutputStream(StrEnum):
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass(frozen=True, slots=True)
class OutputLine:
    content: str
    stream: OutputStream


@dataclass(frozen=True, slots=True)
class ClaudeOutput:
    stdout: str
    stderr: str
    exit_code: int


class ClaudeSessionHandle:
    def __init__(self, process: asyncio.subprocess.Process):
        self._process = process

    async def is_running(self) -> bool:
        return self._process.returncode is None

    async def wait(self) -> ClaudeOutput:
        stdout, stderr = await self._process.communicate()
        return ClaudeOutput(
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=self._process.returncode or 0,
        )

    async def kill(self) -> None:
        if self._process.returncode is None:
            self._process.kill()
            await self._process.wait()

    @property
    def pid(self) -> int | None:
        return self._process.pid


class RealClaudeProcess:
    async def spawn(self, worktree_path: str | Path, prompt: str) -> ClaudeSessionHandle:
        try:
            process = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                "--output-format",
                "json",
                prompt,
                cwd=Path(worktree_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise ProcessSpawnFailed(f"failed to spawn Claude process in {worktree_path}: {exc}") from exc
        return ClaudeSessionHandle(process)
