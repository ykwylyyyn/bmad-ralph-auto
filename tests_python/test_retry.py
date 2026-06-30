from __future__ import annotations

import contextlib
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from ralph.cli import main
from ralph.common.db.store import StateStore
from ralph.common.models import DiagnosticReport, HealingAttempt, HealingLayer, Story, StoryState
from ralph.config import RalphConfig
from ralph.daemon import start_daemon, stop_daemon
from ralph.init_project import init_project
from ralph.render import Theme
from ralph.common.db.errors import StoryNotFoundError
from ralph.retry import RetryError, RetryErrorKind, RetryResult, render_retry_confirmation, retry_story


def _seed_failed_story(root: Path, story_id: int = 7) -> None:
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
        store.save_diagnostic_report(
            DiagnosticReport(
                story_id=story_id,
                root_cause="exhausted",
                recommendation="fix it",
                suggested_fix=f"ralph retry {story_id}",
            )
        )
    finally:
        store.close()


class RetryServiceTests(unittest.TestCase):
    def test_retry_resets_healing_state_and_requeues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_failed_story(root)
            start_daemon(root, RalphConfig(max_workers=2))
            try:
                result = retry_story(root, 7)
                self.assertIsInstance(result, RetryResult)

                store = StateStore.open(root / ".ralph" / "ralph.db")
                try:
                    story = store.get_story(7)
                    self.assertEqual(story.state, StoryState.QUEUED)
                    self.assertIsNone(story.worker_id)
                    self.assertEqual(store.list_healing_attempts(story_id=7), [])
                    with self.assertRaises(StoryNotFoundError):
                        store.get_diagnostic_report(7)
                finally:
                    store.close()
            finally:
                stop_daemon(root)

    def test_retry_requires_running_daemon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_failed_story(root)
            result = retry_story(root, 7)
            self.assertIsInstance(result, RetryError)
            self.assertEqual(result.kind, RetryErrorKind.NO_DAEMON)

    def test_retry_rejects_non_failed_story(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            store = StateStore.open(root / ".ralph" / "ralph.db")
            store.upsert_story(Story(id=3, title="Running", state=StoryState.IN_PROGRESS, worker_id=1))
            store.close()
            start_daemon(root, RalphConfig(max_workers=2))
            try:
                result = retry_story(root, 3)
                self.assertIsInstance(result, RetryError)
                self.assertEqual(result.kind, RetryErrorKind.INVALID_STATE)
                self.assertEqual(result.state_label, "running")
            finally:
                stop_daemon(root)


class RetryDisplayTests(unittest.TestCase):
    def test_render_confirmation_includes_border_and_hint(self) -> None:
        rendered = render_retry_confirmation(
            RetryResult(story_id=7, title="Auth login flow", worker_assignment="pending assignment"),
            theme=Theme(use_color=False),
        )
        self.assertIn("※ Retry", rendered)
        self.assertIn("Story #7: Auth login flow", rendered)
        self.assertIn("retrying", rendered)
        self.assertIn("pending assignment", rendered)
        self.assertIn("ralph status", rendered)


class RetryCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = main(args)
            except SystemExit as exc:
                code = int(exc.code)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_retry_without_daemon_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_failed_story(root)
            code, stdout, _stderr = self.run_cli("retry", "7", "--project-dir", tmp)
            self.assertEqual(code, 1)
            self.assertIn("No running daemon found", stdout)

    def test_retry_requeues_failed_story(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_failed_story(root)
            start_daemon(root, RalphConfig(max_workers=2))
            try:
                code, stdout, _stderr = self.run_cli("retry", "7", "--project-dir", tmp)
                self.assertEqual(code, 0)
                self.assertIn("※ Retry", stdout)
                self.assertIn("retrying", stdout)
            finally:
                stop_daemon(root)

    def test_retry_invalid_story(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            start_daemon(root, RalphConfig(max_workers=2))
            try:
                code, stdout, _stderr = self.run_cli("retry", "99", "--project-dir", tmp)
                self.assertEqual(code, 1)
                self.assertIn("Story #99 not found", stdout)
            finally:
                stop_daemon(root)


if __name__ == "__main__":
    unittest.main()
