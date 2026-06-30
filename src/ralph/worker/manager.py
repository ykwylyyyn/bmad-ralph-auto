from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ralph.common.models import Story, StoryState, WorkerHealth, WorkerState

from .errors import WorkerSpawnError, WorktreeError
from .health import (
    ExitKind,
    WorkerHealthReport,
    classify_exit,
    health_for_active_worker,
    health_for_idle_worker,
    pid_is_alive,
)
from .output import ClaudeResult, parse_claude_output
from .process_sync import SyncClaudeProcess, SyncClaudeSessionHandle
from .prompt import build_story_prompt
from .worktree import GitWorktreeManager, story_branch_name


@dataclass(slots=True)
class ActiveWorkerSession:
    worker_id: int
    story_id: int
    branch: str
    worktree_path: Path
    session: SyncClaudeSessionHandle


@dataclass(frozen=True, slots=True)
class WorkerExit:
    worker_id: int
    story_id: int
    result: ClaudeResult | None
    exit_kind: ExitKind
    exit_code: int
    branch: str
    worktree_path: Path
    log_path: Path | None = None


class WorkerManager:
    """Spawns workers in isolated git worktrees with Claude CLI sessions."""

    def __init__(
        self,
        project_dir: str | Path,
        worktrees_dir: str | Path,
        *,
        logs_dir: str | Path | None = None,
        process_factory: SyncClaudeProcess | None = None,
        worktree_manager: GitWorktreeManager | None = None,
    ) -> None:
        self._project_dir = Path(project_dir).resolve()
        self._worktrees_dir = Path(worktrees_dir).resolve()
        self._logs_dir = Path(logs_dir).resolve() if logs_dir is not None else None
        self._process = process_factory or SyncClaudeProcess()
        self._worktrees = worktree_manager or GitWorktreeManager()
        self._active: dict[int, ActiveWorkerSession] = {}

    @property
    def active_sessions(self) -> dict[int, ActiveWorkerSession]:
        return dict(self._active)

    @property
    def logs_dir(self) -> Path | None:
        return self._logs_dir

    def spawn_for_story(self, worker_id: int, story: Story) -> ActiveWorkerSession:
        if worker_id in self._active:
            raise WorkerSpawnError(worker_id, story.id, "worker already has an active session")

        if not self._worktrees.is_git_repo(self._project_dir):
            raise WorkerSpawnError(worker_id, story.id, "project directory is not a git repository")

        branch = story_branch_name(story.id, story.key)
        worktree_path = self._worktrees_dir / f"worker-{worker_id}"

        process = self._process.with_context(logs_dir=self._logs_dir, worker_id=worker_id)
        try:
            self._worktrees.create(self._project_dir, worktree_path, branch)
            prompt = build_story_prompt(story)
            session = process.spawn(worktree_path, prompt)
        except (WorktreeError, OSError) as exc:
            self._safe_destroy(worktree_path, branch)
            raise WorkerSpawnError(worker_id, story.id, str(exc)) from exc

        active = ActiveWorkerSession(
            worker_id=worker_id,
            story_id=story.id,
            branch=branch,
            worktree_path=worktree_path,
            session=session,
        )
        self._active[worker_id] = active
        return active

    def check_health(self) -> list[WorkerHealthReport]:
        reports: list[WorkerHealthReport] = []
        for worker_id, active in self._active.items():
            is_running = active.session.poll() is None
            health = health_for_active_worker(active.session.pid, is_running=is_running)
            reports.append(
                WorkerHealthReport(
                    worker_id=worker_id,
                    state=WorkerState.RUNNING,
                    health=health,
                    pid=active.session.pid,
                    is_running=is_running,
                )
            )
        return reports

    def poll_exits(self) -> list[WorkerExit]:
        exits: list[WorkerExit] = []
        for worker_id in list(self._active):
            active = self._active[worker_id]
            if active.session.poll() is None:
                continue
            output = active.session.wait()
            exit_kind = classify_exit(output, killed=active.session.was_killed)
            result = parse_claude_output(output) if exit_kind == "completed" else None
            log_path = self._log_path_for_worker(worker_id)
            exits.append(
                WorkerExit(
                    worker_id=worker_id,
                    story_id=active.story_id,
                    result=result,
                    exit_kind=exit_kind,
                    exit_code=output.exit_code,
                    branch=active.branch,
                    worktree_path=active.worktree_path,
                    log_path=log_path,
                )
            )
            self.cleanup_session(worker_id, active.branch, active.worktree_path)
        return exits

    def poll_completions(self) -> list[WorkerExit]:
        """Backward-compatible alias that returns only completed (non-killed) exits."""
        return [item for item in self.poll_exits() if item.exit_kind == "completed"]

    def kill_worker(self, worker_id: int) -> WorkerExit | None:
        active = self._active.get(worker_id)
        if active is None:
            return None
        active.session.kill()
        output = active.session.wait()
        log_path = self._log_path_for_worker(worker_id)
        exit_event = WorkerExit(
            worker_id=worker_id,
            story_id=active.story_id,
            result=None,
            exit_kind="killed",
            exit_code=output.exit_code,
            branch=active.branch,
            worktree_path=active.worktree_path,
            log_path=log_path,
        )
        self.cleanup_session(worker_id, active.branch, active.worktree_path)
        return exit_event

    def cleanup_session(self, worker_id: int, branch: str, worktree_path: Path) -> None:
        self._active.pop(worker_id, None)
        self._safe_destroy(worktree_path, branch)

    def kill_session(self, worker_id: int) -> None:
        self.kill_worker(worker_id)

    def shutdown(self) -> None:
        for worker_id in list(self._active):
            self.kill_worker(worker_id)

    def is_process_alive(self, worker_id: int) -> bool:
        active = self._active.get(worker_id)
        if active is None:
            return False
        return pid_is_alive(active.session.pid)

    def idle_health(self, state: WorkerState) -> WorkerHealth:
        return health_for_idle_worker(state)

    def _log_path_for_worker(self, worker_id: int) -> Path | None:
        if self._logs_dir is None:
            return None
        return self._logs_dir / f"worker-{worker_id}.log"

    def _safe_destroy(self, worktree_path: Path, branch: str) -> None:
        try:
            self._worktrees.destroy(self._project_dir, worktree_path, branch)
        except WorktreeError:
            return


def story_state_for_result(result: ClaudeResult) -> StoryState:
    if result.kind == "success":
        return StoryState.IN_REVIEW
    return StoryState.FAILED
