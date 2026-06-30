from __future__ import annotations

import unittest

from ralph.common.subprocess_util import TEXT_CAPTURE_KWARGS, run_text_capture


class SubprocessUtilTests(unittest.TestCase):
    def test_text_capture_kwargs_use_utf8(self) -> None:
        self.assertEqual(TEXT_CAPTURE_KWARGS["encoding"], "utf-8")
        self.assertEqual(TEXT_CAPTURE_KWARGS["errors"], "replace")
        self.assertTrue(TEXT_CAPTURE_KWARGS["text"])

    def test_run_text_capture_decodes_non_ascii_output(self) -> None:
        result = run_text_capture(
            ["python3", "-c", "import sys; sys.stdout.buffer.write(b'\\xe2\\x9c\\x85 ok\\n')"],
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
