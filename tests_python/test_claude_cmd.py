from __future__ import annotations

import os
import unittest
from unittest import mock

from ralph.worker.claude_cmd import resolve_claude_command


class ClaudeCmdTests(unittest.TestCase):
    def test_defaults_to_claude_binary(self) -> None:
        env = os.environ.copy()
        env.pop("RALPH_CLAUDE_BIN", None)
        env.pop("RALPH_CLAUDE_ARGS", None)
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(resolve_claude_command(), ["claude"])

    def test_ralph_claude_bin_override(self) -> None:
        with mock.patch.dict(os.environ, {"RALPH_CLAUDE_BIN": "/opt/claude"}, clear=False):
            self.assertEqual(resolve_claude_command(), ["/opt/claude"])

    def test_ralph_claude_args_appended(self) -> None:
        env = {
            "RALPH_CLAUDE_BIN": "claude",
            "RALPH_CLAUDE_ARGS": "--dangerously-skip-permissions --model sonnet",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            self.assertEqual(
                resolve_claude_command(),
                ["claude", "--dangerously-skip-permissions", "--model", "sonnet"],
            )

    def test_explicit_list_override_skips_env(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"RALPH_CLAUDE_ARGS": "--dangerously-skip-permissions"},
            clear=False,
        ):
            self.assertEqual(resolve_claude_command(["fake-claude", "--fast"]), ["fake-claude", "--fast"])


if __name__ == "__main__":
    unittest.main()
