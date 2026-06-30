from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    project_dir: Path

    @property
    def runtime_dir(self) -> Path:
        return self.project_dir / ".ralph"

    @property
    def pid_file(self) -> Path:
        return self.runtime_dir / "ralph.pid"

    @property
    def status_file(self) -> Path:
        return self.runtime_dir / "daemon.json"

    @property
    def stop_file(self) -> Path:
        return self.runtime_dir / "stop.request"

    @property
    def socket_file(self) -> Path:
        return self.runtime_dir / "ralph.sock"

    @property
    def port_file(self) -> Path:
        return self.runtime_dir / "ralph.port"

    @property
    def database_file(self) -> Path:
        return self.runtime_dir / "ralph.db"

    @property
    def logs_dir(self) -> Path:
        return self.runtime_dir / "logs"

    @property
    def worktrees_dir(self) -> Path:
        return self.runtime_dir / "worktrees"

    def ensure(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.worktrees_dir.mkdir(exist_ok=True)
