from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_VERIFIER_TIMEOUT_SECS = 300.0


@dataclass(frozen=True, slots=True)
class VerifierConfig:
    enabled: bool = False
    commands: tuple[str, ...] = ()
    timeout_secs: float = DEFAULT_VERIFIER_TIMEOUT_SECS

    @classmethod
    def from_mapping(cls, data: object) -> "VerifierConfig":
        if not isinstance(data, dict):
            raise ValueError("verifier must be a table")

        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("verifier.enabled must be a boolean")

        timeout_secs = data.get("timeout_secs", DEFAULT_VERIFIER_TIMEOUT_SECS)
        if not isinstance(timeout_secs, (int, float)) or timeout_secs <= 0:
            raise ValueError("verifier.timeout_secs must be a positive number")

        raw_commands = data.get("commands", [])
        if raw_commands is None:
            raw_commands = []
        if not isinstance(raw_commands, list) or not all(isinstance(item, str) for item in raw_commands):
            raise ValueError("verifier.commands must be a list of strings")

        return cls(
            enabled=enabled,
            commands=tuple(raw_commands),
            timeout_secs=float(timeout_secs),
        )

    def effective(self) -> "VerifierConfig":
        if not self.enabled:
            return self
        if self.commands:
            return self
        return VerifierConfig(
            enabled=False,
            commands=self.commands,
            timeout_secs=self.timeout_secs,
        )
