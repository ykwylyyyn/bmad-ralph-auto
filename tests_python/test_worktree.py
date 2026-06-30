from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from ralph.common.models import Story
from ralph.worker import GitWorktreeManager, build_story_prompt, story_branch_name


class WorktreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "ralph@test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Ralph"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("demo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.repo, check=True, capture_output=True)
        self.manager = GitWorktreeManager()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_story_branch_name_uses_slug(self) -> None:
        self.assertEqual(
            story_branch_name(2004, "2-4-bmad-artifact-parsing"),
            "ralph/story-2004-bmad-artifact-parsing",
        )

    def test_create_and_destroy_worktree(self) -> None:
        branch = "ralph/story-1001-demo"
        worktree_path = self.repo / ".ralph" / "worktrees" / "worker-1"
        self.manager.create(self.repo, worktree_path, branch)
        self.assertTrue(worktree_path.exists())
        self.assertTrue((worktree_path / "README.md").exists())

        branches = subprocess.run(
            ["git", "-C", str(self.repo), "branch", "--list", branch],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn(branch, branches.stdout)

        self.manager.destroy(self.repo, worktree_path, branch)
        self.assertFalse(worktree_path.exists())

    def test_build_story_prompt_includes_acceptance_criteria(self) -> None:
        prompt = build_story_prompt(
            Story(
                id=1001,
                title="Demo",
                key="1-1-demo",
                acceptance_criteria=["Given a user, when login, then success"],
            )
        )
        self.assertIn("Demo", prompt)
        self.assertIn("Given a user", prompt)


if __name__ == "__main__":
    unittest.main()
