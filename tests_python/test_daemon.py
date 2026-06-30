from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from ralph.config import RalphConfig
from ralph.common.protocol import Request
from ralph.daemon import RuntimePaths, read_status, request_daemon, start_daemon, stop_daemon


class DaemonLifecycleTests(unittest.TestCase):
    def test_start_status_stop_daemon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                started = start_daemon(root, RalphConfig(max_workers=2))
                self.assertEqual(started.state, "running")
                self.assertIsNotNone(started.pid)

                status = read_status(root)
                self.assertEqual(status.state, "running")
                self.assertEqual(status.max_workers, 2)

                stopped = stop_daemon(root)
                self.assertEqual(stopped.state, "stopped")
            finally:
                stop_daemon(root)

    def test_status_request_uses_socket_ipc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                start_daemon(root, RalphConfig(max_workers=3))
                paths = RuntimePaths(root)

                response = request_daemon(paths, Request(type="status"))

                self.assertEqual(response.type, "ok")
                self.assertEqual(response.data["state"], "running")
                self.assertEqual(response.data["max_workers"], 3)
            finally:
                stop_daemon(root)

    def test_start_initializes_sqlite_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                start_daemon(root, RalphConfig(max_workers=1))
                db_path = root / ".ralph" / "ralph.db"
                self.assertTrue(db_path.exists())

                connection = sqlite3.connect(db_path)
                try:
                    rows = connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
                    ).fetchall()
                finally:
                    connection.close()
                self.assertEqual(
                    [row[0] for row in rows],
                    [
                        "diagnostic_reports",
                        "healing_attempts",
                        "pipeline_events",
                        "pipeline_state",
                        "stories",
                        "story_dependencies",
                        "workers",
                    ],
                )
            finally:
                stop_daemon(root)


if __name__ == "__main__":
    unittest.main()
