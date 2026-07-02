# Story 9.2 + 10.1–10.3: Story Cycle + Memory (M3)

## Summary

Implements Milestone M3 from `epic-8-11-agent-os-roadmap.md`:

- **Story cycle orchestrator** — configurable multi-step BMAD-equivalent pipeline (`atdd` → `dev` → `verify` → `qa`)
- **MemoryStore** — SQLite `story_memory` for step index, worktree path, cycle events
- **Skill injection** — dev/atdd/qa prompts include `.claude/skills/bmad-*/SKILL.md` excerpt
- **Progress sync** — updates `sprint-status.yaml` + optional `story-{key}-progress.md`

## Changes

### `src/ralph/pipeline/story_cycle/`
- `StoryCycleConfig` — `[story_cycle]` TOML; `enabled=false` by default

### `src/ralph/pipeline/orchestrator.py`
- `StoryCycleOrchestrator` — per-story step tracking via MemoryStore

### `src/ralph/memory/`
- `MemoryStore` — `get_context`, `append_event`, `get_progress`, cycle keys
- `skill_loader.py` — BMAD skill discovery + excerpt
- `progress.py` — `sync_story_progress()` for sprint-status + progress md

### `src/ralph/worker/prompt.py`
- `build_step_prompt()` + `load_prompt_context()` — skill, story body, ATDD path

### `src/ralph/pipeline/engine.py`
- Cycle-aware assignment, completion, verify step
- Legacy path unchanged when `story_cycle.enabled=false`

### `src/ralph/common/db/schema.py`
- `story_memory` table

## Tests

- `tests_python/test_memory.py`
- `tests_python/test_story_cycle.py`
- `tests_python/test_progress.py`
- `tests_python/test_config.py` (+1)
- `tests_python/test_pipeline_engine.py` (+2)

## Usage

```toml
[story_cycle]
enabled = true
steps = ["dev", "verify"]
max_step_retries = 3

[verifier]
enabled = true
commands = ["make test-all"]
```

When `story_cycle.enabled=false` (default), behavior matches pre-M3: single dev worker + optional post-dev verifier.

When enabled, verifier runs only at the `verify` step (requires `[verifier]` commands).
