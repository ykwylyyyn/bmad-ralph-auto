from __future__ import annotations

from pathlib import Path
import re

from ralph.common.subprocess_util import run_text_capture

from .errors import WorktreeError


def story_branch_name(story_id: int, story_key: str) -> str:
    slug_source = story_key.split("-", 2)[-1] if story_key else str(story_id)
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", slug_source).strip("-").lower()
    if not slug:
        slug = str(story_id)
    return f"ralph/story-{story_id}-{slug}"


class GitWorktreeManager:
    """Create and destroy isolated git worktrees for worker execution."""

    def create(self, repo_dir: Path, worktree_path: Path, branch_name: str) -> None:
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        if worktree_path.exists():
            self.destroy(repo_dir, worktree_path, branch_name)

        result = run_text_capture(
            ["git", "-C", str(repo_dir), "worktree", "add", "-B", branch_name, str(worktree_path)],
            check=False,
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"failed to create worktree {worktree_path} on {branch_name}: {result.stderr.strip()}"
            )

    def destroy(self, repo_dir: Path, worktree_path: Path, branch_name: str) -> None:
        if worktree_path.exists():
            result = run_text_capture(
                ["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(worktree_path)],
                check=False,
            )
            if result.returncode != 0:
                raise WorktreeError(
                    f"failed to remove worktree {worktree_path}: {result.stderr.strip()}"
                )

        run_text_capture(
            ["git", "-C", str(repo_dir), "branch", "-D", branch_name],
            check=False,
        )

    def is_git_repo(self, repo_dir: Path) -> bool:
        result = run_text_capture(
            ["git", "-C", str(repo_dir), "rev-parse", "--is-inside-work-tree"],
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
