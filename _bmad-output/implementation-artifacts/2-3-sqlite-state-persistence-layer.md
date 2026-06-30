# Story 2.3: SQLite State Persistence Layer

Status: done

## Story

As a developer,
I want pipeline state to persist across daemon restarts,
So that no progress is lost if the daemon crashes or is restarted.

## Implementation Summary

### StateStore (`src/ralph/common/db/store.py`)

- Opens `.ralph/ralph.db` with WAL mode and foreign keys enabled
- CRUD for stories and workers with transactional upserts
- Atomic `transition_story_state()` with pipeline validation and optimistic locking
- Healing attempt recording and retention pruning for bounded database growth
- `load_snapshot()` for daemon crash recovery

### AsyncStateStore (`src/ralph/common/db/async_store.py`)

- Wraps blocking SQLite I/O with `asyncio.to_thread` (Python equivalent of Rust `spawn_blocking`)

### Daemon integration

- `run_daemon()` loads persisted stories/workers on startup and reports recovery in status message
- `start_daemon()` initializes database via `StateStore.open()`
- IPC `request_daemon()` returns graceful error when Unix socket is unavailable

## Verification

- `make test-all` — 36 Python tests pass
- New `tests_python/test_persistence.py` covers WAL mode, atomic transitions, crash recovery, concurrent reads, pruning, and async wrapper
