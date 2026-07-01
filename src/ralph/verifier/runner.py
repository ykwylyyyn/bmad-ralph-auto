from __future__ import annotations

from dataclasses import dataclass
import shlex
import subprocess
from pathlib import Path

from ralph.common.subprocess_util import run_text_capture

from .config import VerifierConfig


@dataclass(frozen=True, slots=True)
class CommandFailure:
    command: str
    exit_code: int
    stderr: str


@dataclass(frozen=True, slots=True)
class VerifierResult:
    passed: bool
    failures: tuple[CommandFailure, ...] = ()

    @property
    def summary(self) -> str:
        if self.passed:
            return "verification passed"
        if not self.failures:
            return "verification failed"
        failure = self.failures[0]
        return f"verification failed: {failure.command} (exit {failure.exit_code})"


class VerifierRunner:
    """Runs configured verification commands inside a story worktree."""

    def __init__(self, config: VerifierConfig) -> None:
        self._config = config

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def run(self, worktree_path: str | Path) -> VerifierResult:
        if not self._config.enabled:
            return VerifierResult(passed=True)

        root = Path(worktree_path).resolve()
        if not root.is_dir():
            return VerifierResult(
                passed=False,
                failures=(
                    CommandFailure(
                        command="<worktree>",
                        exit_code=1,
                        stderr=f"worktree does not exist: {root}",
                    ),
                ),
            )

        failures: list[CommandFailure] = []
        for command in self._config.commands:
            result = self._run_command(root, command)
            if result is not None:
                failures.append(result)

        return VerifierResult(passed=not failures, failures=tuple(failures))

    def _run_command(self, worktree_path: Path, command: str) -> CommandFailure | None:
        argv = shlex.split(command, posix=True)
        if not argv:
            return CommandFailure(command=command, exit_code=1, stderr="empty command")

        try:
            completed = run_text_capture(
                argv,
                cwd=worktree_path,
                timeout=self._config.timeout_secs,
            )
        except subprocess.TimeoutExpired as exc:
            stderr = exc.stderr or ""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return CommandFailure(
                command=command,
                exit_code=124,
                stderr=stderr or f"timed out after {self._config.timeout_secs}s",
            )
        except OSError as exc:
            return CommandFailure(command=command, exit_code=1, stderr=str(exc))

        if completed.returncode == 0:
            return None

        stderr = completed.stderr or completed.stdout or ""
        return CommandFailure(
            command=command,
            exit_code=completed.returncode,
            stderr=stderr.strip(),
        )
