# Story 5.2: Sprint Plan Generation & Pipeline Artifact Handoff

## Summary

Implemented BMAD artifact parsing and automatic sprint plan ingestion on `ralph start`, enabling seamless planning-to-execution handoff from `_bmad-output/implementation-artifacts/`.

## Changes

### `src/ralph/pipeline/artifact/`
- YAML frontmatter and story markdown parsing
- `sprint-status.yaml` loading with `development_status` validation
- Story key iteration, location resolution, and missing-artifact fallbacks

### `src/ralph/pipeline/ingestion.py`
- `ingest_sprint_plan()` — builds `SprintPlan`, dependency graph, and validates cycles
- `persist_ingested_plan()` — writes stories and dependencies to SQLite

### `src/ralph/cli.py`
- `ralph start` auto-detects and ingests sprint plan before daemon launch
- UX-compliant errors when sprint plan is missing or malformed

### Schema / store
- `story_key`, `acceptance_criteria` columns on `stories`
- `story_dependencies` table with `replace_story_dependencies()`

## Tests

- `tests_python/test_artifact.py` (6 tests)
- `tests_python/test_ingestion.py` (7 tests)
- Updated `tests_python/test_cli.py`, `test_common.py`, `test_daemon.py`
- **113 tests pass** (`make test-all`)

## Verification

```bash
pip install pyyaml
make test-all
ralph start   # ingests _bmad-output/implementation-artifacts/sprint-status.yaml
```
