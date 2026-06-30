# Story 3.2: Status Command — Health Overview & Sprint Progress

## Summary

Implemented rich `ralph status` output with health overview, sprint progress bar, summary counts, and completion summary. Reads pipeline state from SQLite while verifying daemon liveness.

## Changes

### `src/ralph/status/snapshot.py`
- `StatusSnapshot` / `StoryCounts` models
- `load_status_snapshot()` reads daemon status + stories/workers/healing_attempts tables

### `src/ralph/status/display.py`
- `render_status_overview()` composes Section Border, Health Line, Progress Bar, Summary Line, Completion Summary

### `src/ralph/render/components.py`
- `health_line()`, `progress_bar()`, `summary_line()`, `completion_summary()`

### `src/ralph/render/timefmt.py`
- Duration formatting for health/completion lines

### `src/ralph/cli.py`
- `ralph status` renders overview; shows error when daemon not running

## Tests

- `tests_python/test_status.py` (10 tests)
- Updated `tests_python/test_cli.py`

## Verification

```bash
make test-all  # 56 tests pass
```
