from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ralph.config import RalphConfig, load_config


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


if __name__ == "__main__":
    unittest.main()
