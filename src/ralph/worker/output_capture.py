from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

from .process import ClaudeOutput


@dataclass(slots=True)
class _StreamBuffer:
    chunks: list[bytes]
    total_bytes: int
    max_bytes: int

    def append(self, data: bytes) -> None:
        if not data:
            return
        remaining = self.max_bytes - self.total_bytes
        if remaining <= 0:
            return
        if len(data) > remaining:
            data = data[:remaining]
        self.chunks.append(data)
        self.total_bytes += len(data)


class StreamCapture:
    """Reads subprocess stdout/stderr on background threads and writes to a log file."""

    def __init__(
        self,
        stdout_pipe,
        stderr_pipe,
        log_path: Path,
        *,
        max_buffer_bytes: int = 1_000_000,
    ) -> None:
        self._stdout_pipe = stdout_pipe
        self._stderr_pipe = stderr_pipe
        self._log_path = log_path
        self._stdout_buffer = _StreamBuffer([], 0, max_buffer_bytes)
        self._stderr_buffer = _StreamBuffer([], 0, max_buffer_bytes)
        self._threads: list[threading.Thread] = []
        self._exit_code: int | None = None
        self._log_file = None

    def start(self) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_path.open("ab")
        self._threads = [
            threading.Thread(
                target=self._drain_stream,
                args=(self._stdout_pipe, self._stdout_buffer, b"[stdout] "),
                name=f"ralph-capture-stdout-{self._log_path.stem}",
                daemon=True,
            ),
            threading.Thread(
                target=self._drain_stream,
                args=(self._stderr_pipe, self._stderr_buffer, b"[stderr] "),
                name=f"ralph-capture-stderr-{self._log_path.stem}",
                daemon=True,
            ),
        ]
        for thread in self._threads:
            thread.start()

    def join(self, timeout: float | None = None) -> None:
        for thread in self._threads:
            thread.join(timeout=timeout)
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None

    def set_exit_code(self, exit_code: int) -> None:
        self._exit_code = exit_code

    def output(self) -> ClaudeOutput:
        stdout = b"".join(self._stdout_buffer.chunks).decode("utf-8", errors="replace")
        stderr = b"".join(self._stderr_buffer.chunks).decode("utf-8", errors="replace")
        return ClaudeOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=self._exit_code or 0,
        )

    def _drain_stream(self, pipe, buffer: _StreamBuffer, prefix: bytes) -> None:
        try:
            while True:
                chunk = pipe.read(4096)
                if not chunk:
                    break
                buffer.append(chunk)
                if self._log_file is not None:
                    self._log_file.write(prefix + chunk)
                    self._log_file.flush()
        finally:
            pipe.close()
