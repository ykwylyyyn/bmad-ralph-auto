from __future__ import annotations

import contextlib
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from ralph.cli import generate_completion, main
from ralph.init_project import init_project


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = main(args)
            except SystemExit as exc:
                code = int(exc.code)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_help_shows_subcommands(self) -> None:
        code, stdout, _stderr = self.run_cli("--help")
        self.assertEqual(code, 0)
        for subcommand in ["start", "stop", "status", "diagnose", "retry", "init", "watch", "completions"]:
            self.assertIn(subcommand, stdout)

    def test_version(self) -> None:
        code, stdout, _stderr = self.run_cli("--version")
        self.assertEqual(code, 0)
        self.assertIn("ralph 0.1.0", stdout)

    def test_subcommands_run(self) -> None:
        code, stdout, _stderr = self.run_cli("watch")
        self.assertEqual(code, 0)
        self.assertIn("watch", stdout)

        code, stdout, _stderr = self.run_cli("status")
        self.assertEqual(code, 1)
        self.assertIn("No running daemon found", stdout)

    def test_story_id_commands_require_numeric_id(self) -> None:
        code, _stdout, stderr = self.run_cli("diagnose", "abc")
        self.assertNotEqual(code, 0)
        self.assertIn("invalid value", stderr)

    def test_story_id_commands_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            init_project(Path(tmp))
            code, stdout, _stderr = self.run_cli("diagnose", "99", "--project-dir", tmp)
            self.assertEqual(code, 1)
            self.assertIn("Story #99 not found", stdout)

        code, stdout, _stderr = self.run_cli("retry", "7")
        self.assertEqual(code, 0)
        self.assertIn("story 7", stdout)

    def test_init_creates_config_and_runtime_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, stdout, _stderr = self.run_cli("init", "--project-dir", tmp)
            root = Path(tmp)

            self.assertEqual(code, 0)
            self.assertIn("init: created", stdout)
            self.assertTrue((root / "ralph.toml").exists())
            self.assertTrue((root / ".ralph" / "logs").is_dir())
            self.assertTrue((root / ".ralph" / "worktrees").is_dir())

    def test_init_keeps_existing_config_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "ralph.toml"
            config_path.write_text("max_workers = 9\n", encoding="utf-8")

            code, stdout, _stderr = self.run_cli("init", "--project-dir", tmp)

            self.assertEqual(code, 0)
            self.assertIn("init: kept", stdout)
            self.assertEqual(config_path.read_text(encoding="utf-8"), "max_workers = 9\n")

    def test_completions_generates_shell_script(self) -> None:
        code, stdout, _stderr = self.run_cli("completions", "bash")
        self.assertEqual(code, 0)
        self.assertIn("complete -F _ralph_complete ralph", stdout)

    def test_start_status_stop_use_daemon_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                code, stdout, _stderr = self.run_cli("start", "--project-dir", tmp)
                self.assertEqual(code, 0)
                self.assertIn("✓ Starting daemon done", stdout)
                self.assertIn("※ Ralph", stdout)

                code, stdout, _stderr = self.run_cli("status", "--project-dir", tmp)
                self.assertEqual(code, 0)
                self.assertIn("※ Ralph", stdout)
                self.assertIn("healthy", stdout)

                code, stdout, _stderr = self.run_cli("stop", "--project-dir", tmp)
                self.assertEqual(code, 0)
                self.assertIn("✓ Stopping daemon done", stdout)
                self.assertIn("stopped", stdout)
            finally:
                self.run_cli("stop", "--project-dir", tmp)

    def test_no_color_suppresses_ansi_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, stdout, _stderr = self.run_cli("--no-color", "start", "--project-dir", tmp)
            self.assertEqual(code, 0)
            self.assertNotIn("\033[", stdout)
            self.assertIn("※ Ralph", stdout)
            self.run_cli("--no-color", "stop", "--project-dir", tmp)

    def test_generate_completion_rejects_unknown_shell(self) -> None:
        with self.assertRaises(ValueError):
            generate_completion("unknown")


if __name__ == "__main__":
    unittest.main()
