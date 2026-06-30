# Story 2.6: Worker Spawning & Git Worktree Isolation

Status: done

## Implementation Summary

### Git worktree lifecycle (`src/ralph/worker/worktree.py`)
- Creates `.ralph/worktrees/worker-N/` with branch `ralph/story-{id}-{slug}`
- Destroys worktree and deletes branch on cleanup

### Worker execution (`src/ralph/worker/manager.py`)
- `WorkerManager.spawn_for_story()` creates isolated worktree and launches Claude CLI
- `SyncClaudeProcess` uses subprocess for daemon-compatible process spawning
- Story prompt includes title and acceptance criteria
- Polls completions, cleans up worktrees, updates story state

### Pipeline integration
- `PipelineEngine` spawns workers after assignment
- Spawn failures roll story back to `QUEUED` and log `worker_spawn_failed` events
- Daemon shuts down active workers on exit

## Verification

- `make test-all` — all Python tests pass
- New: `tests_python/test_worktree.py`, `tests_python/test_worker_manager.py`
