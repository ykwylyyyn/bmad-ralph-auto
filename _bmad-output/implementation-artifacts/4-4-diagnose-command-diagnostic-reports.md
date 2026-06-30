# Story 4.4: Diagnose Command & Diagnostic Reports

## Summary

Implemented `ralph diagnose` CLI command with structured terminal report rendering from SQLite diagnostic data.

## Changes

### `src/ralph/diagnose/`
- `load_diagnose_snapshot()` — loads story, healing history, and diagnostic report from `.ralph/ralph.db`
- `render_diagnose()` — Section Border, state summary, Timeline, Recommendation, machine-readable Context
- `diagnose_event_timeline()` — dense 2-space indented events with bold Layer labels

### `src/ralph/cli.py`
- `ralph diagnose [STORY_ID]` — optional story ID; lists all failed stories when omitted
- Error handling for missing stories and empty failure set

## Tests

- `tests_python/test_diagnose.py` (7 tests)
- Updated `tests_python/test_cli.py`
- **85 tests pass** (`make test-all`)

## Verification

```bash
make test-all
ralph diagnose              # no failures message
ralph diagnose 7            # structured report for failed story
```
