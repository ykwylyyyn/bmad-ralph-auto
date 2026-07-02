from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_BACKEND = "claude"


@dataclass(frozen=True, slots=True)
class BackendDefinition:
    command: str
    args: tuple[str, ...] = ()
    output_format: str = "claude_json"
    model: str | None = None
    append_prompt: bool = False

    @classmethod
    def from_mapping(cls, name: str, data: object) -> BackendDefinition:
        if not isinstance(data, dict):
            raise ValueError(f"router.backends.{name} must be a table")

        command = data.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"router.backends.{name}.command must be a non-empty string")

        raw_args = data.get("args", [])
        if raw_args is None:
            raw_args = []
        if not isinstance(raw_args, list) or not all(isinstance(item, str) for item in raw_args):
            raise ValueError(f"router.backends.{name}.args must be a list of strings")

        output_format = data.get("output_format", "claude_json")
        if output_format not in {"claude_json", "plain"}:
            raise ValueError(f"router.backends.{name}.output_format must be claude_json or plain")

        model = data.get("model")
        if model is not None and not isinstance(model, str):
            raise ValueError(f"router.backends.{name}.model must be a string")

        append_prompt = data.get("append_prompt", False)
        if not isinstance(append_prompt, bool):
            raise ValueError(f"router.backends.{name}.append_prompt must be a boolean")

        return cls(
            command=command.strip(),
            args=tuple(raw_args),
            output_format=str(output_format),
            model=model,
            append_prompt=append_prompt,
        )


@dataclass(frozen=True, slots=True)
class RouterConfig:
    default: str = DEFAULT_BACKEND
    backends: dict[str, BackendDefinition] = field(default_factory=dict)
    rules: dict[str, str] = field(default_factory=dict)
    fallback: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: object) -> RouterConfig:
        if not isinstance(data, dict):
            raise ValueError("router must be a table")

        default = data.get("default", DEFAULT_BACKEND)
        if not isinstance(default, str) or not default.strip():
            raise ValueError("router.default must be a non-empty string")

        raw_backends = data.get("backends", {})
        if raw_backends is None:
            raw_backends = {}
        if not isinstance(raw_backends, dict):
            raise ValueError("router.backends must be a table")

        backends: dict[str, BackendDefinition] = {}
        for name, backend_data in raw_backends.items():
            if not isinstance(name, str):
                continue
            backends[name.strip()] = BackendDefinition.from_mapping(name, backend_data)

        raw_rules = data.get("rules", {})
        if raw_rules is None:
            raw_rules = {}
        if not isinstance(raw_rules, dict):
            raise ValueError("router.rules must be a table")

        rules: dict[str, str] = {}
        for step, backend_name in raw_rules.items():
            if not isinstance(step, str) or not isinstance(backend_name, str):
                continue
            rules[step.strip().lower()] = backend_name.strip()

        raw_fallback = data.get("fallback", {})
        if raw_fallback is None:
            raw_fallback = {}
        if not isinstance(raw_fallback, dict):
            raise ValueError("router.fallback must be a table")

        fallback: dict[str, tuple[str, ...]] = {}
        for step, chain in raw_fallback.items():
            if not isinstance(step, str):
                continue
            if isinstance(chain, str):
                fallback[step.strip().lower()] = (chain.strip(),)
            elif isinstance(chain, list) and all(isinstance(item, str) for item in chain):
                fallback[step.strip().lower()] = tuple(item.strip() for item in chain if item.strip())

        return cls(default=default.strip(), backends=backends, rules=rules, fallback=fallback)

    @property
    def enabled(self) -> bool:
        return bool(self.backends)

    def effective(self) -> RouterConfig:
        if not self.backends:
            return RouterConfig()
        return RouterConfig(
            default=self.default if self.default in self.backends else next(iter(self.backends)),
            backends=self.backends,
            rules=self.rules,
            fallback=self.fallback,
        )
