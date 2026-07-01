from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ralph.config import RalphConfig, load_config, render_config, resolve_config
from ralph.verifier.config import VerifierConfig


class ConfigTests(unittest.TestCase):
    def test_default_config_has_no_max_workers(self) -> None:
        self.assertIsNone(RalphConfig().max_workers)

    def test_parse_max_workers(self) -> None:
        self.assertEqual(RalphConfig.from_mapping({"max_workers": 5}).max_workers, 5)

    def test_load_config_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ralph.toml"
            path.write_text("max_workers = 3", encoding="utf-8")
            self.assertEqual(load_config(path).max_workers, 3)

    def test_resolve_config_uses_default_when_files_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.toml"
            self.assertEqual(
                resolve_config(user_config_path=missing, project_config_path=missing).max_workers,
                5,
            )

    def test_resolve_config_precedence_is_cli_project_user_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_config = root / "user.toml"
            project_config = root / "project.toml"
            user_config.write_text("max_workers = 2", encoding="utf-8")
            project_config.write_text("max_workers = 4", encoding="utf-8")

            resolved = resolve_config(
                user_config_path=user_config,
                project_config_path=project_config,
                overrides=RalphConfig(max_workers=8),
            )

            self.assertEqual(resolved.max_workers, 8)

    def test_render_config_writes_toml(self) -> None:
        self.assertEqual(render_config(RalphConfig(max_workers=6)), "max_workers = 6\n")

    def test_parse_verifier_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ralph.toml"
            path.write_text(
                """
[verifier]
enabled = true
timeout_secs = 120
commands = ["make test-all", "python -m pytest -q"]
""".strip(),
                encoding="utf-8",
            )
            config = load_config(path).effective()
            self.assertTrue(config.verifier.enabled)
            self.assertEqual(config.verifier.timeout_secs, 120)
            self.assertEqual(config.verifier.commands, ("make test-all", "python -m pytest -q"))

    def test_verifier_enabled_without_commands_is_disabled(self) -> None:
        config = RalphConfig(verifier=VerifierConfig(enabled=True, commands=())).effective()
        self.assertFalse(config.verifier.enabled)


if __name__ == "__main__":
    unittest.main()
