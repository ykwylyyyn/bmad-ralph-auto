# Story 2.7: Worker Health Monitoring & Lifecycle Management

## Summary

Implemented worker health monitoring, unexpected exit handling, targeted kill API, async output capture, and cattle-model replacement scheduling.

## Changes

### `src/ralph/worker/health.py`
- `WorkerHealthReport`, `classify_exit()`, `pid_is_alive()`, health evaluation helpers

### `src/ralph/worker/output_capture.py`
- `StreamCapture` — background threads drain stdout/stderr to `.ralph/logs/worker-N.log` with bounded in-memory buffers

### `src/ralph/worker/process_sync.py`
- Optional per-spawn `env` override; `with_context()` preserves subclass type; integrated `StreamCapture`

### `src/ralph/worker/manager.py`
- `poll_exits()`, `check_health()`, `kill_worker()`; `WorkerExit` replaces `WorkerCompletion`
- Logs directory wired into spawn for diagnostic capture

### `src/ralph/pipeline/engine.py`
- Health sync to DB each tick; unexpected/killed exit handling with `worker_exit_unexpected` / `worker_killed` events
- `kill_worker()` public API; failed workers recovered to IDLE at end of tick (next heartbeat replacement)

### `src/ralph/daemon/lifecycle.py`
- Passes `logs_dir` into `PipelineEngine`

## Tests

- `tests_python/test_worker_health.py` — 9 tests covering health utilities, output capture, kill isolation, crash recovery, engine integration

## Verification

```bash
make test-all  # 73 tests pass
```
