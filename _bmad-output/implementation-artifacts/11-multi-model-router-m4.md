# Story 11.1–11.4: Multi-Model Router (M4)

## Summary

Implements Milestone M4 from `epic-8-11-agent-os-roadmap.md`:

- **WorkerBackend abstraction** — `ClaudeBackend` + generic `CommandBackend`
- **Router config** — `[router]` TOML with backends and per-step rules
- **Gemini/custom adapters** — command-based backends with `claude_json` or `plain` output
- **Observability** — `ralph status --detail` shows backend, model, cost per story/worker

## Changes

### `src/ralph/worker/backends/`
- `WorkerBackend` protocol, `ClaudeBackend`, `CommandBackend`

### `src/ralph/router/`
- `RouterConfig`, `BackendSelector` — step → backend routing

### `src/ralph/worker/manager.py`
- Routed spawn via `BackendSelector`; `step` parameter for rule lookup

### `src/ralph/pipeline/engine.py`
- Passes cycle `step` to worker spawn; records run metadata in `story_memory` + `workers` table

### `src/ralph/status/snapshot.py`
- Story timeline includes backend/model/cost; worker table shows backend label

### Schema
- `workers.backend`, `workers.model`, `workers.cost_usd` columns (auto-migrate)

## Tests

- `tests_python/test_router.py`
- `tests_python/fixtures/fake_gemini.py`
- **All tests pass** (`make test-all`)

## Usage

```toml
[router]
default = "claude"

[router.backends.claude]
command = "claude"
args = ["--dangerously-skip-permissions"]

[router.backends.gemini]
command = "gemini"
args = ["-p"]
model = "gemini-pro"
output_format = "claude_json"

[router.rules]
dev = "claude"
qa = "gemini"
```

No `[router]` section → legacy Claude-only behavior (unchanged).
