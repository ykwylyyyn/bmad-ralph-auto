# Story 2.4: BMAD Artifact Parsing & Sprint Plan Ingestion

Status: done

## Implementation Summary

### Artifact parsing (`src/ralph/pipeline/artifact/`)

- `parser.py` — YAML frontmatter parsing (`---` delimited) and story markdown extraction (title, status, acceptance criteria, dependencies)
- `reader.py` — sprint-status.yaml discovery/loading and story file resolution from `story_location`

### Sprint ingestion (`src/ralph/pipeline/ingestion.py`)

- Loads `development_status` from `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Builds `SprintPlan` with numeric story IDs (`epic * 1000 + story`)
- Constructs `DependencyGraph` from explicit frontmatter dependencies or sequential epic defaults
- Persists stories and dependencies via `StateStore`

### CLI integration

- `ralph start` ingests sprint plan before daemon launch
- Missing plan: UX-compliant error with guidance
- Malformed plan: error includes file path and parse detail

## Verification

- `make test-all` — all Python tests pass
- New tests: `tests_python/test_artifact.py`, `tests_python/test_ingestion.py`
