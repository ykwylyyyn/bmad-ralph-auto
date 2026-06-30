from __future__ import annotations

import io
import os
import unittest
from unittest.mock import patch

from ralph.render import (
    Semantic,
    Spinner,
    Theme,
    detect_terminal_width,
    error_message,
    layout_width,
    resolve_theme,
    section_border,
    story_name_limit,
    strip_ansi,
    truncate_text,
    visible_length,
)


class ThemeTests(unittest.TestCase):
    def test_color_theme_applies_ansi_codes(self) -> None:
        theme = Theme(use_color=True)
        styled = theme.green("healthy")
        self.assertIn("\033[32m", styled)
        self.assertEqual(strip_ansi(styled), "healthy")

    def test_plain_theme_suppresses_ansi_codes(self) -> None:
        theme = Theme(use_color=False)
        self.assertEqual(theme.bold_red("Error:"), "Error:")
        self.assertEqual(theme.magenta("※"), "※")

    def test_resolve_theme_honors_no_color_flag(self) -> None:
        theme = resolve_theme(no_color=True)
        self.assertFalse(theme.use_color)

    def test_resolve_theme_honors_no_color_env(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            theme = resolve_theme()
        self.assertFalse(theme.use_color)

    def test_resolve_theme_disables_for_non_tty(self) -> None:
        stream = io.StringIO()
        theme = resolve_theme(stream=stream)
        self.assertFalse(theme.use_color)

    def test_semantic_colors(self) -> None:
        theme = Theme(use_color=True)
        self.assertIn("[32m", theme.semantic("ok", Semantic.HEALTHY))
        self.assertIn("[33m", theme.semantic("active", Semantic.ACTIVE))
        self.assertIn("[31m", theme.semantic("bad", Semantic.FAILED))
        self.assertIn("[2m", theme.semantic("dim", Semantic.SECONDARY))


class WidthTests(unittest.TestCase):
    def test_layout_width_clamps_to_80_120(self) -> None:
        self.assertEqual(layout_width(60), 80)
        self.assertEqual(layout_width(90), 90)
        self.assertEqual(layout_width(140), 120)

    def test_story_name_limit_tiers(self) -> None:
        self.assertEqual(story_name_limit(70), 15)
        self.assertEqual(story_name_limit(85), 20)
        self.assertEqual(story_name_limit(110), 30)
        self.assertEqual(story_name_limit(200), 30)

    def test_truncate_text_adds_ellipsis(self) -> None:
        self.assertEqual(truncate_text("short", 20), "short")
        self.assertEqual(truncate_text("abcdefghijklmnopqrst", 10), "abcdefghi…")

    def test_detect_terminal_width_fallback(self) -> None:
        with patch("ralph.render.width.shutil.get_terminal_size", side_effect=OSError("nope")):
            self.assertEqual(detect_terminal_width(fallback=95), 95)


class SectionBorderTests(unittest.TestCase):
    def test_border_fills_to_layout_width(self) -> None:
        line = section_border("Ralph", context="healthy", context_semantic=Semantic.HEALTHY, width=80)
        self.assertEqual(visible_length(line), 80)
        self.assertTrue(strip_ansi(line).startswith("※ Ralph "))
        self.assertTrue(strip_ansi(line).endswith("healthy ※"))

    def test_border_without_context(self) -> None:
        plain = strip_ansi(section_border("Timeline", width=80, theme=Theme(use_color=False)))
        self.assertEqual(len(plain), 80)
        self.assertTrue(plain.startswith("※ Timeline "))
        self.assertTrue(plain.endswith(" ※"))

    def test_border_plain_text_remains_readable(self) -> None:
        line = section_border(
            "Workers",
            context="3/3 healthy",
            context_semantic=Semantic.HEALTHY,
            width=90,
            theme=Theme(use_color=False),
        )
        plain = strip_ansi(line)
        self.assertEqual(len(plain), 90)
        self.assertIn("※ Workers ", plain)
        self.assertIn("3/3 healthy ※", plain)


class ErrorMessageTests(unittest.TestCase):
    def test_error_message_structure(self) -> None:
        rendered = error_message(
            "No sprint plan found in project",
            detail_lines=["Ralph looks for sprint plans in _bmad-output/implementation-artifacts/"],
            suggestion="Run BMAD sprint planning first, then try ralph start again.",
            theme=Theme(use_color=False),
        )
        self.assertIn("Error: No sprint plan found in project", rendered)
        self.assertIn("Ralph looks for sprint plans", rendered)
        self.assertIn("Run BMAD sprint planning first", rendered)
        self.assertNotIn("Traceback", rendered)

    def test_error_message_uses_red_bold_label_with_color(self) -> None:
        rendered = error_message("boom", theme=Theme(use_color=True))
        self.assertIn("\033[1;31mError:\033[0m", rendered)


class SpinnerTests(unittest.TestCase):
    def test_spinner_completes_with_success_marker(self) -> None:
        stream = io.StringIO()
        with Spinner("Starting daemon", theme=Theme(use_color=False), stream=stream, animate=False):
            pass
        self.assertIn("✓ Starting daemon done", stream.getvalue())

    def test_spinner_completes_with_failure_marker(self) -> None:
        stream = io.StringIO()
        with self.assertRaises(RuntimeError):
            with Spinner("Starting daemon", theme=Theme(use_color=False), stream=stream, animate=False):
                raise RuntimeError("boom")
        self.assertIn("✗ Starting daemon failed", stream.getvalue())

    def test_spinner_frames_cover_braille_set(self) -> None:
        from ralph.render.components import SPINNER_FRAMES

        self.assertEqual(len(SPINNER_FRAMES), 10)


if __name__ == "__main__":
    unittest.main()
