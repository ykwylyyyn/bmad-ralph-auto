# Story 8.1–9.3: Verifier Gate + VERIFYING State + Healing Wire-up (M1)

## Summary

Implements Milestone M1 from `epic-8-11-agent-os-roadmap.md`:

- **Verifier** — configurable `test/lint/build` commands in `ralph.toml`
- **VERIFYING state** — worker success → verify → `done` (when enabled)
- **Healing coordinator** — Layer 1/2/3 wired into `PipelineEngine`
- **Worktree lifecycle** — defer destroy until after verification

## Changes

### `src/ralph/verifier/`
- `VerifierConfig`, `VerifierRunner` — run commands in story worktree with UTF-8 subprocess

### `src/ralph/config/config.py`
- Parse `[verifier]` table; `enabled=false` by default

### `src/ralph/common/models.py` / `pipeline/state.py`
- New `StoryState.VERIFYING` and transitions

### `src/ralph/pipeline/healing/coordinator.py`
- `HealingCoordinator` + `EngineRestartGateway` integrated in engine

### `src/ralph/pipeline/engine.py`
- Post-worker verification; healing on Claude/verifier/unexpected failures
- `shutdown()` requeues `IN_PROGRESS` / `VERIFYING` stories

### `src/ralph/worker/manager.py`
- `release_worktree()` — destroy worktree after engine handles completion

## Tests

- `tests_python/test_verifier.py` (3)
- `tests_python/test_config.py` (+2)
- `tests_python/test_pipeline_engine.py` (+1 verifier integration)
- **166 tests pass** (`make test-all`)

## Usage

```toml
[verifier]
enabled = true
commands = ["make test-all"]
```

```powershell
$env:RALPH_CLAUDE_ARGS="--dangerously-skip-permissions"
ralph start
```
