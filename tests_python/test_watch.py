from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ralph.render import Theme
from ralph.status.snapshot import StatusSnapshot, StoryCounts
from ralph.watch import WatchExitKind, run_watch


class WatchTests(unittest.TestCase):
    def _snapshot(self, *, complete: bool = False) -> StatusSnapshot:
        now = datetime.now(timezone.utc).isoformat()
        counts = StoryCounts(completed=4, queued=0) if complete else StoryCounts(completed=1, running=1, queued=2)
        return StatusSnapshot(
            daemon_running=True,
            health_label="healthy",
            started_at=now,
            heartbeat_at=now,
            max_workers=3,
            active_workers=2,
            story_counts=counts,
            stories=[],
            workers=[],
        )

    def test_watch_without_daemon_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_watch(
                Path(tmp),
                theme=Theme(use_color=False),
                write_stream=StringIO(),
                load_snapshot=lambda _root, detail=False: None,
            )
            self.assertIsNone(result)

    def test_watch_renders_single_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stream = StringIO()
            result = run_watch(
                Path(tmp),
                theme=Theme(use_color=False),
                max_frames=1,
                write_stream=stream,
                load_snapshot=lambda _root, detail=False: self._snapshot(),
            )
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.kind, WatchExitKind.COMPLETE)
            self.assertEqual(result.frames_rendered, 1)
            output = stream.getvalue()
            self.assertIn("※ Ralph", output)
            self.assertIn("Refreshing every 2s", output)

    def test_watch_exits_when_sprint_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stream = StringIO()
            result = run_watch(
                Path(tmp),
                theme=Theme(use_color=False),
                write_stream=stream,
                load_snapshot=lambda _root, detail=False: self._snapshot(complete=True),
            )
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.kind, WatchExitKind.COMPLETE)
            self.assertEqual(result.frames_rendered, 1)

    def test_watch_handles_keyboard_interrupt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stream = StringIO()
            calls = {"count": 0}

            def load_snapshot(_root, detail=False):
                calls["count"] += 1
                if calls["count"] == 1:
                    return WatchTests._snapshot(self)
                raise KeyboardInterrupt

            result = run_watch(
                Path(tmp),
                theme=Theme(use_color=False),
                write_stream=stream,
                load_snapshot=load_snapshot,
                sleep_fn=lambda _secs: None,
            )
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.kind, WatchExitKind.INTERRUPTED)

    def test_cli_watch_requires_running_daemon(self) -> None:
        from ralph.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            stream = StringIO()
            with patch("sys.stdout", stream):
                with self.assertRaises(SystemExit) as ctx:
                    main(["--no-color", "watch", "--project-dir", tmp])
            self.assertEqual(ctx.exception.code, 1)
            self.assertIn("No running daemon found", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
