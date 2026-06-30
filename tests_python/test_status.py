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
from ralph.status import (
    load_status_snapshot,
    render_status,
    render_status_detail,
    render_status_tables,
    should_show_status_hint,
    story_table,
    worker_table,
)
from ralph.status.snapshot import (
    StatusSnapshot,
    StoryCounts,
    StoryDetail,
    StoryEvent,
    WorkerDetail,
    _build_snapshot,
    record_status_invocation,
)


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


class StoryTableTests(unittest.TestCase):
    def test_story_table_sorts_by_id_and_truncates_name(self) -> None:
        stories = [
            StoryDetail(1002, "A very long story title here", "queued", None, "—", "0"),
            StoryDetail(1001, "Short", "running", 1, "12m", "0"),
        ]
        lines = story_table(stories, theme=Theme(use_color=False), width=80)
        joined = "\n".join(lines)
        self.assertIn("※ Stories", joined)
        self.assertLess(joined.index("#1001"), joined.index("#1002"))
        self.assertIn("A very long story t…", joined)
        self.assertIn("W1", joined)

    def test_worker_table_shows_health_context(self) -> None:
        workers = [
            WorkerDetail(1, "healthy", 1001, "1h 2m"),
            WorkerDetail(2, "idle", None, "1h 2m"),
        ]
        lines = worker_table(workers, theme=Theme(use_color=False), healthy_count=1)
        joined = "\n".join(lines)
        self.assertIn("1/2 healthy", joined)
        self.assertIn("Story #1001", joined)


class StatusSnapshotTests(unittest.TestCase):
    def test_build_snapshot_maps_story_states(self) -> None:
        daemon = _daemon_stub()
        story_rows = [
            {"id": 1, "title": "One", "state": StoryState.DONE.value, "worker_id": None, "created_at": "t", "updated_at": "t"},
            {"id": 2, "title": "Two", "state": StoryState.IN_PROGRESS.value, "worker_id": 1, "created_at": "t", "updated_at": "t"},
            {"id": 3, "title": "Three", "state": StoryState.QUEUED.value, "worker_id": None, "created_at": "t", "updated_at": "t"},
            {"id": 4, "title": "Four", "state": StoryState.FAILED.value, "worker_id": None, "created_at": "t", "updated_at": "t"},
        ]
        snapshot = _build_snapshot(daemon, story_rows, [], [], logs_dir=None)
        self.assertEqual(snapshot.story_counts.completed, 1)
        self.assertEqual(snapshot.story_counts.running, 1)
        self.assertEqual(len(snapshot.stories), 4)

    def test_build_snapshot_detects_healing(self) -> None:
        daemon = _daemon_stub()
        story_rows = [
            {
                "id": 10,
                "title": "Heal",
                "state": StoryState.IN_PROGRESS.value,
                "worker_id": 1,
                "created_at": "t",
                "updated_at": "t",
            }
        ]
        healing_rows = [
            {
                "story_id": 10,
                "layer": "step_retry",
                "attempt": 1,
                "reason": "timeout",
                "created_at": "2026-06-30T10:15:00+00:00",
            }
        ]
        snapshot = _build_snapshot(daemon, story_rows, [], healing_rows, logs_dir=None)
        self.assertEqual(snapshot.health_label, "healing")
        self.assertEqual(snapshot.stories[0].display_state, "retrying")

    def test_load_status_snapshot_returns_none_when_daemon_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(load_status_snapshot(str(root)))


class StatusDisplayTests(unittest.TestCase):
    def test_render_status_includes_tables_and_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = _sample_snapshot()
            rendered = render_status(snapshot, theme=Theme(use_color=False), project_dir=root, detail=False)
            self.assertIn("※ Stories", rendered)
            self.assertIn("※ Workers", rendered)
            self.assertIn("Tip: ralph status --detail for expanded view", rendered)

    def test_render_status_detail_includes_timeline(self) -> None:
        snapshot = _sample_snapshot()
        rendered = render_status_detail(snapshot, theme=Theme(use_color=False))
        self.assertIn("Story #1001", rendered)
        self.assertIn("Assigned to W1", rendered)

    def test_hint_suppressed_after_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _ in range(6):
                record_status_invocation(root)
            self.assertFalse(should_show_status_hint(root))


class StatusIntegrationTests(unittest.TestCase):
    def test_status_query_reads_database_while_daemon_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                start_daemon(root, RalphConfig(max_workers=2))
                _seed_stories(
                    root,
                    [
                        (1001, "Demo story", StoryState.DONE.value, None),
                        (1002, "Next story", StoryState.QUEUED.value, None),
                    ],
                )
                _seed_workers(root, [(1, "idle", "healthy"), (2, "running", "healthy")])
                snapshot = load_status_snapshot(root)
                assert snapshot is not None
                rendered = render_status_tables(snapshot, theme=Theme(use_color=False))
                self.assertIn("#1001", rendered)
                self.assertIn("Demo story", rendered)
                self.assertIn("W1", rendered)
            finally:
                stop_daemon(root)


def _daemon_stub():
    class _Stub:
        started_at = datetime.now(timezone.utc).isoformat()
        heartbeat_at = datetime.now(timezone.utc).isoformat()
        max_workers = 3

    return _Stub()


def _sample_snapshot() -> StatusSnapshot:
    now = datetime.now(timezone.utc)
    started = (now - timedelta(hours=1)).isoformat()
    return StatusSnapshot(
        daemon_running=True,
        health_label="healthy",
        started_at=started,
        heartbeat_at=now.isoformat(),
        max_workers=2,
        active_workers=1,
        story_counts=StoryCounts(completed=1, running=1),
        stories=[
            StoryDetail(
                1001,
                "Auth login flow",
                "running",
                1,
                "12m",
                "0",
                events=[StoryEvent("10:15", "Assigned to W1")],
            )
        ],
        workers=[WorkerDetail(1, "healthy", 1001, "1h 0m")],
    )


def _seed_stories(
    root: Path,
    rows: list[tuple[int, str, str, int | None]],
) -> None:
    db_path = root / ".ralph" / "ralph.db"
    connection = sqlite3.connect(db_path)
    try:
        for story_id, title, state, worker_id in rows:
            connection.execute(
                """
                INSERT INTO stories (id, title, state, worker_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (story_id, title, state, worker_id, "now", "now"),
            )
        connection.commit()
    finally:
        connection.close()


def _seed_workers(root: Path, rows: list[tuple[int, str, str]]) -> None:
    db_path = root / ".ralph" / "ralph.db"
    connection = sqlite3.connect(db_path)
    try:
        for worker_id, state, health in rows:
            connection.execute(
                """
                INSERT INTO workers (id, state, health, worktree_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (worker_id, state, health, f"/tmp/worker-{worker_id}", "now", "now"),
            )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    unittest.main()
