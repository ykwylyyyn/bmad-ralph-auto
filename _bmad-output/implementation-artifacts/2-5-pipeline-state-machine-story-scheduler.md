# Story 2.5: Pipeline State Machine & Story Scheduler

Status: done

## Implementation Summary

### StoryScheduler (`src/ralph/pipeline/scheduler.py`)
- Identifies schedulable QUEUED stories with satisfied dependencies
- Enforces `max_workers` concurrency via available slot calculation

### PipelineEngine (`src/ralph/pipeline/engine.py`)
- Initializes worker pool and pipeline RUNNING state
- Assigns stories to idle workers (`QUEUED` → `IN_PROGRESS`) with atomic persistence
- Evaluates pipeline completion and records `sprint_complete` events

### Store extensions
- `assign_story_to_worker()` — atomic assignment + valid state transition
- `pipeline_state` and `pipeline_events` tables

### Daemon integration
- `run_daemon()` runs `PipelineEngine.tick()` on each heartbeat

## Verification

- `make test-all` — all Python tests pass
- New: `tests_python/test_scheduler.py`, `tests_python/test_pipeline_engine.py`
