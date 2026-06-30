# Story 4.5: Retry Command & Story Re-ingestion

## Summary

Implemented `ralph retry <id>` to re-queue failed stories with reset healing state and confirmation output.

## Changes

### `src/ralph/retry/`
- `retry_story()` — validates daemon, story state, clears healing/report data, re-queues story
- `render_retry_confirmation()` — Section Border with retrying context, worker assignment, status hint

### `src/ralph/common/db/store.py`
- `reset_healing_state()` — deletes `healing_attempts` + `diagnostic_reports`, requeues story

### `src/ralph/cli.py`
- Wired `ralph retry <id>` with error handling per acceptance criteria

## Tests

- `tests_python/test_retry.py` (7 tests)
- Updated `tests_python/test_cli.py`
- **92 tests pass** (`make test-all`)

## Verification

```bash
make test-all
ralph start
ralph retry 7
ralph status
```
