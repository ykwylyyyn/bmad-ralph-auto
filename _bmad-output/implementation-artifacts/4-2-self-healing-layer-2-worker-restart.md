# Story 4.2: Self-Healing Layer 2 — Worker Restart

## Summary

Implemented Layer 2 worker restart coordinator with kill/destroy/spawn gateway abstraction, story requeue for scratch execution, and escalation to Layer 3.

## Changes

### `src/ralph/pipeline/healing/worker_restart.py`
- `Layer2WorkerRestart` — kills worker, destroys worktree, records `worker_restart` healing attempt, requeues story, spawns fresh worktree
- `WorkerRestartGateway` protocol for integration with real `WorkerManager` (Story 4.2+ engine wiring)
- `handle_restart_success()` marks story `done` with self-healed event
- `handle_restart_failure()` returns `ESCALATE_LAYER3`
- Warn-level structured logging on activation

### `src/ralph/common/db/store.py`
- `WorkerRecord` + worker upsert/get/list
- `requeue_story()` and `assign_story_to_worker()` for scratch re-execution

### `src/ralph/pipeline/healing/types.py`
- Added `RESTART`, `ESCALATE_LAYER3` outcome kinds
- Extended `HealingOutcome` with `old_worker_id`, `new_worker_id`, `worktree_path`

## Tests

- 7 new Layer 2 tests in `tests_python/test_healing.py`
- **73 tests pass** (`make test-all`)

## Verification

```bash
make test-all
```
