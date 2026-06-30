from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .process import RealClaudeProcess


@dataclass(slots=True)
class Worker:
    id: int
    worktree_path: Path
    process_factory: RealClaudeProcess
