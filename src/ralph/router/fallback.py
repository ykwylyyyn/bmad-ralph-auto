from __future__ import annotations

from dataclasses import dataclass

from ralph.router.config import RouterConfig
from ralph.worker.backends.base import WorkerBackend


@dataclass(frozen=True, slots=True)
class FallbackSelection:
  backend_name: str
  backend: WorkerBackend
  attempt: int
  chain: tuple[str, ...]


class FallbackChain:
  """Runtime backend fallback: primary → alternates on spawn/exit failure."""

  def __init__(self, selector) -> None:  # noqa: ANN001 — avoids circular import
    self._selector = selector
    self._config: RouterConfig = selector._config  # noqa: SLF001

  def chain_for(self, step: str) -> tuple[str, ...]:
    normalized = step.strip().lower()
    primary, _ = self._selector.select(normalized)
    fallbacks = self._config.fallback.get(normalized) or self._config.fallback.get("*") or ()
    chain: list[str] = [primary]
    for name in fallbacks:
      if name not in chain and name in self._selector._backends:  # noqa: SLF001
        chain.append(name)
    if self._config.default not in chain and self._config.default in self._selector._backends:
      chain.append(self._config.default)
    return tuple(chain)

  def select_with_fallback(self, step: str, failed_backends: set[str] | None = None) -> FallbackSelection:
    failed = failed_backends or set()
    chain = self.chain_for(step)
    for attempt, backend_name in enumerate(chain):
      if backend_name in failed:
        continue
      backend = self._selector._backends.get(backend_name)  # noqa: SLF001
      if backend is None:
        continue
      return FallbackSelection(
        backend_name=backend_name,
        backend=backend,
        attempt=attempt,
        chain=chain,
      )
    name, backend = self._selector.select(step)
    return FallbackSelection(backend_name=name, backend=backend, attempt=0, chain=chain)
