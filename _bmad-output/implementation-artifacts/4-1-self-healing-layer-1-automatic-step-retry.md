# Story 4.1: Self-Healing Layer 1 — Automatic Step Retry

## Summary

Implemented Layer 1 step retry coordinator with SQLite persistence, configurable retry limit, and structured warn logging.

## Changes

### `src/ralph/config/config.py`
- Added `retry_limit` setting (default 3) with three-tier precedence support

### `src/ralph/common/db/store.py`
- `StateStore` with story upsert/get and `healing_attempts` recording
- `count_healing_attempts()` excludes self-healed marker rows

### `src/ralph/pipeline/healing/`
- `Layer1StepRetry` — handles step failures, schedules same-worker retries, escalates to Layer 2 when exhausted
- `handle_retry_success()` records self-healed events
- Warn-level log: `story_id`, `attempt`, `layer="step_retry"`, "healing activated"

## Tests

- `tests_python/test_healing.py` (7 tests)
- **66 tests pass** (`make test-all`)

## Verification

```bash
make test-all
```
