from __future__ import annotations

import json
import unittest

from ralph.worker import ClaudeOutput, parse_claude_output


class WorkerOutputTests(unittest.TestCase):
    def test_parses_success(self) -> None:
        output = ClaudeOutput(
            stdout=json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "result": "Task completed.",
                    "cost_usd": 0.05,
                    "duration_ms": 5000,
                    "is_error": False,
                    "num_turns": 3,
                    "session_id": "test-session-001",
                }
            ),
            stderr="",
            exit_code=0,
        )
        result = parse_claude_output(output)
        self.assertEqual(result.kind, "success")
        self.assertEqual(result.result, "Task completed.")
        self.assertEqual(result.session_id, "test-session-001")

    def test_parses_failure(self) -> None:
        output = ClaudeOutput(
            stdout=json.dumps({"subtype": "error_max_turns", "result": "Max turns reached.", "is_error": True}),
            stderr="",
            exit_code=1,
        )
        result = parse_claude_output(output)
        self.assertEqual(result.kind, "failure")
        self.assertEqual(result.subtype, "error_max_turns")

    def test_parses_malformed_json(self) -> None:
        result = parse_claude_output(ClaudeOutput(stdout="{bad", stderr="", exit_code=0))
        self.assertEqual(result.kind, "parse_error")

    def test_empty_stdout_with_stderr_is_failure(self) -> None:
        result = parse_claude_output(ClaudeOutput(stdout="", stderr="claude: command not found", exit_code=127))
        self.assertEqual(result.kind, "failure")
        self.assertEqual(result.error, "claude: command not found")


if __name__ == "__main__":
    unittest.main()
