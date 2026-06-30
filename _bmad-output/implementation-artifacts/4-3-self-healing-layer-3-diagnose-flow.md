# Story 4.3: Self-Healing Layer 3 — Diagnose Flow

## Summary

Implemented Layer 3 automated diagnostic analysis with structured report persistence and exhausted story marking.

## Changes

### `src/ralph/pipeline/healing/diagnose.py`
- `Layer3Diagnose` — triggers diagnose flow on Layer 3 escalation, records `diagnose` healing attempt
- `FailureAnalyzer` — examines healing history, worker log signals, and acceptance criteria
- Stores structured `DiagnosticReport` with root cause, recommendation, and `ralph retry <id>` fix
- Marks story `failed` (exhausted) after assessment

### `src/ralph/common/db/schema.py`
- Added `diagnostic_reports` table

### `src/ralph/common/models.py`
- Added `DiagnosticReport` model

### `src/ralph/common/db/store.py`
- `save_diagnostic_report()`, `get_diagnostic_report()`, `mark_story_exhausted()`

## Tests

- 5 new Layer 3 tests in `tests_python/test_healing.py`
- **78 tests pass** (`make test-all`)

## Verification

```bash
make test-all
```
