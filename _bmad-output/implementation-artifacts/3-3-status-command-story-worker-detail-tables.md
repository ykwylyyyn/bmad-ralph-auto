# Story 3.3: Status Command — Story & Worker Detail Tables

## Summary

Extended `ralph status` with Story Table, Worker Table, `--detail` expanded view, and progressive Hint Line.

## Changes

### `src/ralph/status/snapshot.py`
- `StoryDetail`, `WorkerDetail`, `StoryEvent` models
- Extended DB load with title, worker assignment, healing events, log excerpts
- Hint tracking via `.ralph/hint-state.json` (first 5 invocations)
- Respects `hints = false` in `ralph.toml`

### `src/ralph/status/tables.py`
- `story_table()` — ID, Name, State, Worker, Duration, Retries columns
- `worker_table()` — `※ Workers ═══ N/N healthy ※` with assignment + uptime
- `story_detail_sections()` / `worker_detail_sections()` for `--detail`
- `hint_line()` footer component

### `src/ralph/status/display.py`
- `render_status()` composes overview + tables + detail + hint

### `src/ralph/cli.py`
- `ralph status` uses full render pipeline; `--detail` shows timelines and worker logs

## Tests

- Extended `tests_python/test_status.py` (15 tests total in file)
- **59 tests pass** (`make test-all`)

## Verification

```bash
make test-all
ralph status            # overview + tables + hint
ralph status --detail   # + story timelines + worker log excerpts
```
