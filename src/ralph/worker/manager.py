from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ralph.common.models import Story, StoryState

from .errors import WorkerSpawnError, WorktreeError
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
class WorkerCompletion:
    worker_id: int
    story_id: int
    result: ClaudeResult
    branch: str
    worktree_path: Path


class WorkerManager:
    """Spawns workers in isolated git worktrees with Claude CLI sessions."""

    def __init__(
        self,
        project_dir: str | Path,
        worktrees_dir: str | Path,
        *,
        process_factory: SyncClaudeProcess | None = None,
        worktree_manager: GitWorktreeManager | None = None,
    ) -> None:
        self._project_dir = Path(project_dir).resolve()
        self._worktrees_dir = Path(worktrees_dir).resolve()
        self._process = process_factory or SyncClaudeProcess()
        self._worktrees = worktree_manager or GitWorktreeManager()
        self._active: dict[int, ActiveWorkerSession] = {}

    @property
    def active_sessions(self) -> dict[int, ActiveWorkerSession]:
        return dict(self._active)

    def spawn_for_story(self, worker_id: int, story: Story) -> ActiveWorkerSession:
        if worker_id in self._active:
            raise WorkerSpawnError(worker_id, story.id, "worker already has an active session")

        if not self._worktrees.is_git_repo(self._project_dir):
            raise WorkerSpawnError(worker_id, story.id, "project directory is not a git repository")

        branch = story_branch_name(story.id, story.key)
        worktree_path = self._worktrees_dir / f"worker-{worker_id}"

        try:
            self._worktrees.create(self._project_dir, worktree_path, branch)
            prompt = build_story_prompt(story)
            session = self._process.spawn(worktree_path, prompt)
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

    def poll_completions(self) -> list[WorkerCompletion]:
        completions: list[WorkerCompletion] = []
        for worker_id in list(self._active):
            active = self._active[worker_id]
            if active.session.poll() is None:
                continue
            output = active.session.wait()
            result = parse_claude_output(output)
            completions.append(
                WorkerCompletion(
                    worker_id=worker_id,
                    story_id=active.story_id,
                    result=result,
                    branch=active.branch,
                    worktree_path=active.worktree_path,
                )
            )
            self.cleanup_session(worker_id, active.branch, active.worktree_path)
        return completions

    def cleanup_session(self, worker_id: int, branch: str, worktree_path: Path) -> None:
        self._active.pop(worker_id, None)
        self._safe_destroy(worktree_path, branch)

    def kill_session(self, worker_id: int) -> None:
        active = self._active.get(worker_id)
        if active is None:
            return
        active.session.kill()
        self.cleanup_session(worker_id, active.branch, active.worktree_path)

    def shutdown(self) -> None:
        for worker_id in list(self._active):
            self.kill_session(worker_id)

    def _safe_destroy(self, worktree_path: Path, branch: str) -> None:
        try:
            self._worktrees.destroy(self._project_dir, worktree_path, branch)
        except WorktreeError:
            return


def story_state_for_result(result: ClaudeResult) -> StoryState:
    if result.kind == "success":
        return StoryState.IN_REVIEW
    return StoryState.FAILED
