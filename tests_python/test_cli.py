from __future__ import annotations

import contextlib
from io import StringIO
import unittest

from ralph.cli import main


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
        for subcommand in ["start", "stop", "status", "diagnose", "retry", "init", "watch"]:
            self.assertIn(subcommand, stdout)

    def test_version(self) -> None:
        code, stdout, _stderr = self.run_cli("--version")
        self.assertEqual(code, 0)
        self.assertIn("ralph 0.1.0", stdout)

    def test_subcommands_run(self) -> None:
        for subcommand in ["start", "stop", "status", "init", "watch"]:
            with self.subTest(subcommand=subcommand):
                code, stdout, _stderr = self.run_cli(subcommand)
                self.assertEqual(code, 0)
                self.assertIn(subcommand, stdout)

    def test_story_id_commands_require_numeric_id(self) -> None:
        code, _stdout, stderr = self.run_cli("diagnose", "abc")
        self.assertNotEqual(code, 0)
        self.assertIn("invalid value", stderr)

    def test_story_id_commands_run(self) -> None:
        code, stdout, _stderr = self.run_cli("retry", "7")
        self.assertEqual(code, 0)
        self.assertIn("story 7", stdout)


if __name__ == "__main__":
    unittest.main()
