from __future__ import annotations

import contextlib
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from ralph.cli import main
from ralph.common.db.store import StateStore
from ralph.common.models import DiagnosticReport, HealingAttempt, HealingLayer, Story, StoryState
from ralph.diagnose import (
    DiagnoseLoadError,
    DiagnoseLoadErrorKind,
    DiagnoseSnapshot,
    list_failed_story_ids,
    load_diagnose_snapshot,
    render_diagnose,
)
from ralph.init_project import init_project
from ralph.render import Theme


def _seed_exhausted_story(root: Path, story_id: int = 7) -> None:
    db_path = root / ".ralph" / "ralph.db"
    init_project(root, max_workers=2)
    store = StateStore.open(db_path)
    try:
        store.upsert_story(
            Story(id=story_id, title="Auth login flow", state=StoryState.FAILED, worker_id=None)
        )
        store.record_healing_attempt(
            HealingAttempt(story_id=story_id, layer=HealingLayer.STEP_RETRY, attempt=1, reason="timeout")
        )
        store.record_healing_attempt(
            HealingAttempt(story_id=story_id, layer=HealingLayer.STEP_RETRY, attempt=2, reason="timeout")
        )
        store.record_healing_attempt(
            HealingAttempt(
                story_id=story_id,
                layer=HealingLayer.WORKER_RESTART,
                attempt=1,
                reason="old_worker_id=2,new_worker_id=2",
            )
        )
        store.record_healing_attempt(
            HealingAttempt(
                story_id=story_id,
                layer=HealingLayer.DIAGNOSE,
                attempt=1,
                reason="diagnose flow triggered",
            )
        )
        store.save_diagnostic_report(
            DiagnosticReport(
                story_id=story_id,
                root_cause=f"Story #{story_id} exhausted all healing layers.",
                recommendation="Review worker logs and acceptance criteria.",
                suggested_fix=f"ralph retry {story_id}",
                analysis={"healing_layers_attempted": ["step_retry", "worker_restart", "diagnose"]},
            )
        )
    finally:
        store.close()


class DiagnoseSnapshotTests(unittest.TestCase):
    def test_load_snapshot_builds_exhausted_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_exhausted_story(root)
            result = load_diagnose_snapshot(root, 7)
            self.assertIsInstance(result, DiagnoseSnapshot)
            self.assertEqual(result.story_id, 7)
            self.assertTrue(result.exhausted)
            self.assertEqual(result.retry_count, 4)
            self.assertEqual(result.suggested_fix, "ralph retry 7")
            self.assertEqual(len(result.events), 4)

    def test_missing_story_returns_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            result = load_diagnose_snapshot(root, 99)
            self.assertIsInstance(result, DiagnoseLoadError)
            self.assertEqual(result.kind, DiagnoseLoadErrorKind.STORY_NOT_FOUND)

    def test_list_failed_story_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_exhausted_story(root)
            self.assertEqual(list_failed_story_ids(root), [7])


class DiagnoseDisplayTests(unittest.TestCase):
    def test_load_snapshot_includes_verification_failed_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_exhausted_story(root)
            db_path = root / ".ralph" / "ralph.db"
            store = StateStore.open(db_path)
            try:
                store.record_pipeline_event(
                    "verification_failed",
                    {
                        "story_id": 7,
                        "summary": "verification failed: make test (exit 1)",
                        "failures": [
                            {
                                "command": "make test",
                                "exit_code": 1,
                                "stderr": "line1\nline2\nFAILED",
                            }
                        ],
                    },
                )
            finally:
                store.close()

            result = load_diagnose_snapshot(root, 7)
            self.assertIsInstance(result, DiagnoseSnapshot)
            verifier_events = [event for event in result.events if event.layer_label == "Verifier"]
            self.assertEqual(len(verifier_events), 1)
            self.assertIn("make test", verifier_events[0].description)
            self.assertIn("exit 1", verifier_events[0].description)
            self.assertIn("FAILED", verifier_events[0].description)

    def test_render_includes_border_timeline_and_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_exhausted_story(root)
            snapshot = load_diagnose_snapshot(root, 7)
            rendered = render_diagnose(snapshot, theme=Theme(use_color=False))

            self.assertIn("※ Diagnose", rendered)
            self.assertIn("Story #7: Auth login flow", rendered)
            self.assertIn("failed (exhausted — all 3 healing layers attempted)", rendered)
            self.assertIn("Retries: 4 across workers", rendered)
            self.assertIn("※ Timeline", rendered)
            self.assertIn("Layer 1:", rendered)
            self.assertIn("Layer 2:", rendered)
            self.assertIn("Layer 3:", rendered)
            self.assertIn("※ Recommendation", rendered)
            self.assertIn("ralph retry 7", rendered)
            self.assertIn("story_id: 7", rendered)


class DiagnoseCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = main(args)
            except SystemExit as exc:
                code = int(exc.code)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_diagnose_without_id_reports_no_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            init_project(Path(tmp))
            code, stdout, _stderr = self.run_cli("diagnose", "--project-dir", tmp)
            self.assertEqual(code, 0)
            self.assertIn("No failed stories to diagnose", stdout)

    def test_diagnose_invalid_story_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            init_project(Path(tmp))
            code, stdout, _stderr = self.run_cli("diagnose", "99", "--project-dir", tmp)
            self.assertEqual(code, 1)
            self.assertIn("Story #99 not found in current sprint", stdout)
            self.assertIn("ralph status", stdout)

    def test_diagnose_renders_failed_story(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_exhausted_story(root)
            code, stdout, _stderr = self.run_cli("diagnose", "7", "--project-dir", tmp)
            self.assertEqual(code, 0)
            self.assertIn("※ Diagnose", stdout)
            self.assertIn("ralph retry 7", stdout)


if __name__ == "__main__":
    unittest.main()
