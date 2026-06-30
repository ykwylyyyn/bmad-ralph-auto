from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ralph.common.models import StoryState
from ralph.config import RalphConfig
from ralph.daemon import start_daemon, stop_daemon
from ralph.render import Theme, completion_summary, health_line, progress_bar, summary_line
from ralph.render.theme import Semantic
from ralph.status import load_status_snapshot, render_status_overview
from ralph.status.snapshot import StatusSnapshot, StoryCounts, _build_snapshot


class RenderComponentExtensionTests(unittest.TestCase):
    def test_progress_bar_renders_thirty_characters(self) -> None:
        lines = progress_bar(3, 5, theme=Theme(use_color=False))
        self.assertEqual(lines[0], "  Stories")
        bar_line = lines[1]
        self.assertIn("60% completed", bar_line)
        self.assertEqual(bar_line.count("█") + bar_line.count("░"), 30)

    def test_summary_line_uses_fixed_order(self) -> None:
        rendered = summary_line(
            {
                "failed": 1,
                "completed": 2,
                "running": 1,
                "queued": 3,
            },
            theme=Theme(use_color=False),
        )
        self.assertLess(rendered.index("completed"), rendered.index("running"))
        self.assertLess(rendered.index("running"), rendered.index("queued"))
        self.assertLess(rendered.index("queued"), rendered.index("failed"))

    def test_health_line_applies_semantic_color(self) -> None:
        rendered = health_line("healthy", theme=Theme(use_color=True), semantic=Semantic.HEALTHY)
        self.assertIn("\033[32m", rendered)

    def test_completion_summary_includes_failed_guidance(self) -> None:
        lines = completion_summary(
            success_percent=90,
            self_healed=2,
            failed=1,
            runtime="8h 14m",
            worker_count=3,
            failed_stories=[7],
            theme=Theme(use_color=False),
        )
        joined = "\n".join(lines)
        self.assertIn("Success: 90%", joined)
        self.assertIn("2 self-healed", joined)
        self.assertIn("ralph diagnose 7", joined)


class StatusSnapshotTests(unittest.TestCase):
    def test_build_snapshot_maps_story_states(self) -> None:
        daemon = _daemon_stub()
        story_rows = [
            {"id": 1, "state": StoryState.DONE.value},
            {"id": 2, "state": StoryState.IN_PROGRESS.value},
            {"id": 3, "state": StoryState.QUEUED.value},
            {"id": 4, "state": StoryState.FAILED.value},
        ]
        snapshot = _build_snapshot(daemon, story_rows, [], [])
        self.assertEqual(snapshot.story_counts.completed, 1)
        self.assertEqual(snapshot.story_counts.running, 1)
        self.assertEqual(snapshot.story_counts.queued, 1)
        self.assertEqual(snapshot.story_counts.failed, 1)
        self.assertEqual(snapshot.health_label, "healthy")

    def test_build_snapshot_detects_healing(self) -> None:
        daemon = _daemon_stub()
        story_rows = [{"id": 10, "state": StoryState.IN_PROGRESS.value}]
        healing_rows = [{"story_id": 10, "layer": "step_retry", "attempt": 1, "created_at": "now"}]
        snapshot = _build_snapshot(daemon, story_rows, [], healing_rows)
        self.assertEqual(snapshot.health_label, "healing")
        self.assertEqual(snapshot.story_counts.retrying, 1)
        self.assertEqual(snapshot.recovery_story_count, 1)

    def test_load_status_snapshot_returns_none_when_daemon_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(load_status_snapshot(str(root)))


class StatusDisplayTests(unittest.TestCase):
    def test_render_status_overview_for_running_sprint(self) -> None:
        now = datetime.now(timezone.utc)
        started = (now - timedelta(hours=2, minutes=3)).isoformat()
        snapshot = StatusSnapshot(
            daemon_running=True,
            health_label="healthy",
            started_at=started,
            heartbeat_at=now.isoformat(),
            max_workers=3,
            active_workers=2,
            story_counts=StoryCounts(completed=2, running=1, queued=1),
        )
        rendered = render_status_overview(snapshot, theme=Theme(use_color=False))
        self.assertIn("※ Ralph", rendered)
        self.assertIn("healthy", rendered)
        self.assertIn("Running for", rendered)
        self.assertIn("Stories", rendered)
        self.assertIn("50% completed", rendered)
        self.assertIn("2 completed", rendered)
        self.assertIn("1 running", rendered)

    def test_render_status_overview_for_completed_sprint(self) -> None:
        snapshot = StatusSnapshot(
            daemon_running=True,
            health_label="complete",
            started_at=datetime.now(timezone.utc).isoformat(),
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            max_workers=3,
            active_workers=0,
            story_counts=StoryCounts(completed=9, failed=1),
            failed_story_ids=[7],
            self_healed_count=2,
        )
        rendered = render_status_overview(snapshot, theme=Theme(use_color=False))
        self.assertIn("complete", rendered)
        self.assertIn("Sprint finished", rendered)
        self.assertIn("Success: 90%", rendered)
        self.assertIn("ralph diagnose 7", rendered)


class StatusIntegrationTests(unittest.TestCase):
    def test_status_query_reads_database_while_daemon_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                start_daemon(root, RalphConfig(max_workers=2))
                _seed_stories(root, [(1001, "Demo", StoryState.DONE.value), (1002, "Next", StoryState.QUEUED.value)])
                snapshot = load_status_snapshot(str(root))
                assert snapshot is not None
                self.assertEqual(snapshot.story_counts.completed, 1)
                self.assertEqual(snapshot.story_counts.queued, 1)
                rendered = render_status_overview(snapshot, theme=Theme(use_color=False))
                self.assertIn("50% completed", rendered)
            finally:
                stop_daemon(root)


def _daemon_stub():
    class _Stub:
        started_at = datetime.now(timezone.utc).isoformat()
        heartbeat_at = datetime.now(timezone.utc).isoformat()
        max_workers = 3

    return _Stub()


def _seed_stories(root: Path, rows: list[tuple[int, str, str]]) -> None:
    db_path = root / ".ralph" / "ralph.db"
    connection = sqlite3.connect(db_path)
    try:
        for story_id, title, state in rows:
            connection.execute(
                "INSERT INTO stories (id, title, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (story_id, title, state, "now", "now"),
            )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    unittest.main()
