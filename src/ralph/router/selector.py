from __future__ import annotations

from ralph.router.config import BackendDefinition, RouterConfig
from ralph.router.fallback import FallbackChain
from ralph.worker.backends.claude import ClaudeBackend
from ralph.worker.backends.command import CommandBackend, CommandBackendConfig
from ralph.worker.backends.base import WorkerBackend
from ralph.worker.claude_cmd import resolve_claude_command
from ralph.worker.process_sync import SyncClaudeProcess


class BackendSelector:
    """Selects a worker backend for a story cycle step."""

    def __init__(self, config: RouterConfig | None = None) -> None:
        self._config = (config or RouterConfig()).effective()
        self._backends = self._build_backends()
        self._fallback = FallbackChain(self)

    @property
    def fallback(self) -> FallbackChain:
        return self._fallback

    @classmethod
    def default(cls) -> BackendSelector:
        return cls(RouterConfig())

    @classmethod
    def from_process_factory(cls, process: SyncClaudeProcess) -> BackendSelector:
        selector = cls(RouterConfig())
        selector._backends = {"claude": ClaudeBackend.from_process(process)}
        return selector

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def select(self, step: str) -> tuple[str, WorkerBackend]:
        if not self._config.enabled:
            if "claude" in self._backends:
                return "claude", self._backends["claude"]
            return "claude", self._default_claude_backend()

        normalized = step.strip().lower()
        backend_name = self._config.rules.get(normalized, self._config.default)
        backend = self._backends.get(backend_name)
        if backend is None:
            backend_name = self._config.default
            backend = self._backends.get(backend_name)
        if backend is None:
            return "claude", self._default_claude_backend()
        return backend_name, backend

    def output_format_for(self, backend_name: str) -> str:
        definition = self._config.backends.get(backend_name)
        if definition is None:
            return "claude_json"
        return definition.output_format

    def _default_claude_backend(self) -> WorkerBackend:
        if "claude" in self._backends:
            return self._backends["claude"]
        return ClaudeBackend(resolve_claude_command())

    def _build_backends(self) -> dict[str, WorkerBackend]:
        if not self._config.enabled:
            return {}

        built: dict[str, WorkerBackend] = {}
        for name, definition in self._config.backends.items():
            if name == "claude" and not definition.append_prompt:
                command = [definition.command, *definition.args]
                built[name] = ClaudeBackend(_command=command, _model_label=definition.model)
                continue
            built[name] = CommandBackend(
                CommandBackendConfig(
                    name=name,
                    command=definition.command,
                    args=definition.args,
                    output_format=definition.output_format,
                    model=definition.model,
                    append_prompt=definition.append_prompt,
                )
            )
        return built
