from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from ralph.verifier import VerifierRunner
from ralph.verifier.config import VerifierConfig


class VerifierRunnerTests(unittest.TestCase):
    def test_disabled_verifier_short_circuits(self) -> None:
        runner = VerifierRunner(VerifierConfig(enabled=False, commands=("false",)))
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(tmp)
        self.assertTrue(result.passed)
        self.assertEqual(result.failures, ())

    def test_runs_commands_in_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = VerifierRunner(
                VerifierConfig(
                    enabled=True,
                    commands=(f'{sys.executable} -c "import sys; sys.exit(0)"',),
                )
            )
            passing = runner.run(root)
            self.assertTrue(passing.passed)

            runner_fail = VerifierRunner(
                VerifierConfig(
                    enabled=True,
                    commands=(
                        f'{sys.executable} -c "import sys; sys.stderr.write(\'boom\\n\'); sys.exit(2)"',
                    ),
                )
            )
            failing = runner_fail.run(root)
            self.assertFalse(failing.passed)
            self.assertEqual(len(failing.failures), 1)
            self.assertEqual(failing.failures[0].exit_code, 2)
            self.assertIn("boom", failing.failures[0].stderr)

    def test_missing_worktree_fails(self) -> None:
        runner = VerifierRunner(VerifierConfig(enabled=True, commands=("echo ok",)))
        result = runner.run("/tmp/does-not-exist-ralph-verifier")
        self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main()
