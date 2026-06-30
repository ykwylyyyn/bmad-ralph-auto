# Story 5.1: BMAD Submodule Integration & Planning Workflow Access

## Summary

Extended `ralph init` to integrate BMAD planning workflows via git submodule setup, validation, and pinned version tracking.

## Changes

### `src/ralph/planning/bmad.py`
- `integrate_bmad()` — validates existing `_bmad`, or adds git submodule with pinned ref in `.ralph/bmad-pin.json`
- `ensure_planning_output_dirs()` — creates `_bmad-output/planning-artifacts` and `implementation-artifacts`
- `list_planning_workflows()` — discovers PRD/architecture/UX/sprint planning workflows under `_bmad/bmm/workflows`
- `submodule_update_hint()` — documents `git submodule update --remote _bmad`

### `src/ralph/init_project.py` + `cli.py`
- Init now integrates BMAD and prints planning workflow availability + update hint

## Tests

- `tests_python/test_planning.py` (7 tests)
- Updated `tests_python/test_cli.py`
- **99 tests pass** (`make test-all`)

## Verification

```bash
make test-all
ralph init
```
