from __future__ import annotations

import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

from ralph.init_project import init_project
from ralph.planning import (
    integrate_bmad,
    list_planning_workflows,
    read_bmad_pin,
    submodule_update_hint,
    validate_bmad_layout,
)


class PlanningBmadTests(unittest.TestCase):
    def test_validate_bmad_layout_requires_workflows_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bmad = root / "_bmad"
            (bmad / "bmm" / "workflows").mkdir(parents=True)
            self.assertFalse(validate_bmad_layout(bmad))
            (bmad / "bmm" / "config.yaml").write_text("project: demo\n", encoding="utf-8")
            self.assertTrue(validate_bmad_layout(bmad))

    def test_init_creates_bmad_output_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = init_project(root, integrate_bmad_submodule=False)
            self.assertTrue((result.project_dir / "_bmad-output" / "planning-artifacts").is_dir())
            self.assertTrue((result.project_dir / "_bmad-output" / "implementation-artifacts").is_dir())

    def test_integrate_validates_existing_bmad_and_writes_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = Path("/workspace/_bmad")
            if not source.is_dir():
                self.skipTest("workspace BMAD checkout unavailable")
            shutil.copytree(source, root / "_bmad", dirs_exist_ok=True)

            result = integrate_bmad(root)
            self.assertEqual(result.action, "validated")
            self.assertTrue(result.planning_workflows)

            pin = read_bmad_pin(root)
            self.assertIsNotNone(pin)
            assert pin is not None
            self.assertEqual(pin["path"], "_bmad")
            self.assertIn("update_command", pin)

    def test_list_planning_workflows_finds_sprint_planning(self) -> None:
        source = Path("/workspace/_bmad")
        if not source.is_dir():
            self.skipTest("workspace BMAD checkout unavailable")
        workflows = list_planning_workflows(source)
        self.assertTrue(any("sprint-planning" in item for item in workflows))

    def test_submodule_update_hint_matches_documentation(self) -> None:
        self.assertEqual(submodule_update_hint(), "git submodule update --remote _bmad")

    def test_integrate_skips_submodule_add_for_non_git_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = integrate_bmad(root)
            self.assertEqual(result.action, "skipped")
            self.assertIn("not a git repository", result.message)

    def test_git_init_can_add_local_bmad_submodule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = Path("/workspace/_bmad")
            if not source.is_dir():
                self.skipTest("workspace BMAD checkout unavailable")

            bmad_src = Path(tmp) / "bmad-src"
            shutil.copytree(source, bmad_src)
            subprocess.run(["git", "init"], cwd=bmad_src, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "ralph@test"], cwd=bmad_src, check=True)
            subprocess.run(["git", "config", "user.name", "ralph"], cwd=bmad_src, check=True)
            subprocess.run(["git", "add", "."], cwd=bmad_src, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=bmad_src, check=True, capture_output=True)

            bare = Path(tmp) / "bmad-bare.git"
            subprocess.run(["git", "clone", "--bare", str(bmad_src), str(bare)], check=True, capture_output=True)

            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "ralph@test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "ralph"], cwd=root, check=True)
            subprocess.run(["git", "config", "protocol.file.allow", "always"], cwd=root, check=True)

            result = integrate_bmad(root, submodule_url=str(bare.resolve()))
            self.assertEqual(result.action, "initialized")
            self.assertTrue((root / "_bmad" / "bmm" / "workflows").is_dir())
            pin = read_bmad_pin(root)
            self.assertIsNotNone(pin)
            assert pin is not None
            self.assertEqual(pin["url"], str(bare))


if __name__ == "__main__":
    unittest.main()
