from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from ralph.memory.progress import sync_story_progress
from ralph.pipeline.artifact.reader import default_sprint_status_path


class ProgressSyncTests(unittest.TestCase):
    def test_updates_sprint_status_and_writes_progress_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sprint_status = default_sprint_status_path(root)
            sprint_status.parent.mkdir(parents=True, exist_ok=True)
            sprint_status.write_text(
                yaml.safe_dump(
                    {
                        "development_status": {
                            "1-1-demo": "ready-for-dev",
                        }
                    }
                ),
                encoding="utf-8",
            )

            updated = sync_story_progress(root, "1-1-demo", "dev")
            self.assertTrue(updated)

            data = yaml.safe_load(sprint_status.read_text(encoding="utf-8"))
            self.assertEqual(data["development_status"]["1-1-demo"], "in-progress")

            progress_md = (
                root
                / "_bmad-output"
                / "implementation-artifacts"
                / "test-artifacts"
                / "story-1-1-demo-progress.md"
            )
            self.assertTrue(progress_md.is_file())
            self.assertIn("last_step: dev", progress_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
