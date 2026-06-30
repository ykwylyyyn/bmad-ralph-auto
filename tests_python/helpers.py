from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from ralph.worker import SyncClaudeProcess, WorkerManager


def init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ralph@test"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Ralph"], cwd=path, check=True)
    readme = path / "README.md"
    readme.write_text("demo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def fake_claude_process() -> SyncClaudeProcess:
    script = Path(__file__).resolve().parent / "fixtures" / "fake_claude.py"
    return SyncClaudeProcess([sys.executable, str(script)])


def worker_manager_for_repo(repo: Path, worktrees: Path) -> WorkerManager:
    return WorkerManager(repo, worktrees, process_factory=fake_claude_process())
