from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from ralph.router.config import BackendDefinition, RouterConfig
from ralph.router.selector import BackendSelector
from ralph.worker.backends.command import CommandBackend, CommandBackendConfig
from ralph.worker.output import parse_worker_output
from ralph.worker.process import ClaudeOutput


class RouterConfigTests(unittest.TestCase):
    def test_parse_router_section(self) -> None:
        config = RouterConfig.from_mapping(
            {
                "default": "claude",
                "backends": {
                    "claude": {"command": "claude", "args": ["--dangerously-skip-permissions"]},
                    "gemini": {
                        "command": "gemini",
                        "args": ["-p"],
                        "model": "gemini-pro",
                    },
                },
                "rules": {"dev": "claude", "qa": "gemini"},
            }
        ).effective()
        self.assertTrue(config.enabled)
        self.assertEqual(config.rules["qa"], "gemini")
        self.assertEqual(config.backends["gemini"].model, "gemini-pro")

    def test_disabled_when_no_backends(self) -> None:
        self.assertFalse(RouterConfig().effective().enabled)


class BackendSelectorTests(unittest.TestCase):
    def test_selects_rule_backend_for_step(self) -> None:
        selector = BackendSelector(
            RouterConfig(
                default="claude",
                backends={
                    "claude": BackendDefinition(command="claude"),
                    "codex": BackendDefinition(command="codex", args=["-p"]),
                },
                rules={"qa": "codex"},
            )
        )
        name, backend = selector.select("qa")
        self.assertEqual(name, "codex")
        self.assertEqual(backend.name, "codex")

    def test_default_selector_uses_claude(self) -> None:
        name, _backend = BackendSelector.default().select("dev")
        self.assertEqual(name, "claude")


class CommandBackendTests(unittest.TestCase):
    def test_spawn_and_parse_fake_gemini(self) -> None:
        script = Path(__file__).resolve().parent / "fixtures" / "fake_gemini.py"
        backend = CommandBackend(
            CommandBackendConfig(
                name="gemini",
                command=sys.executable,
                args=(str(script),),
                append_prompt=True,
                model="gemini-test",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            session = backend.spawn(worktree, "ignored prompt")
            output = session.wait()
            result = parse_worker_output(output, output_format="claude_json", model="gemini-test")
            self.assertEqual(result.kind, "success")
            self.assertEqual(result.model, "gemini-test")
            self.assertEqual(result.cost_usd, 0.12)


if __name__ == "__main__":
    unittest.main()
