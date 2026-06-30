# Story 6.1: Ralph Watch Live Dashboard

## Summary

Implemented `ralph watch` — a live-refreshed terminal dashboard that polls daemon status and reuses the status rendering engine.

## Changes

### `src/ralph/watch/__init__.py`
- `run_watch()` — polls `load_status_snapshot`, clears screen, renders status overview/tables
- Exits on sprint completion, daemon stop, or Ctrl+C
- Configurable `--refresh` interval and `--detail` mode via CLI

### `src/ralph/cli.py`
- Wired `ralph watch` with `--detail` and `--refresh` flags
- Shows error when no daemon is running (consistent with `ralph status`)

## Tests

- `tests_python/test_watch.py` (5 tests)
- Updated `tests_python/test_cli.py`

## Verification

```bash
make test-all
ralph start
ralph watch          # live dashboard, Ctrl+C to exit
ralph watch --detail # expanded view
```
