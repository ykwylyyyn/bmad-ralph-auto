# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ralph is an autonomous SDLC pipeline runner — a **Python CLI** with a long-running daemon that orchestrates parallel Claude Code worker sessions to execute BMAD stories 24/7 with self-healing capabilities. It pairs with BMAD-METHOD for planning and shifts delivery from human-in-the-loop to human-on-the-loop.

## Build & Test Commands

```bash
make test-all          # Run all Python tests (tests_python/)
make test              # Alias for test-all
make check             # Alias for test-all
make clean             # Remove __pycache__ directories

# Run directly without install
PYTHONPATH=src python -m ralph --help

# Reproduce CI locally
./scripts/ci-local.sh
```

## Architecture

Python package under `src/ralph/`:

```text
src/ralph/cli.py          # CLI entry (start/stop/status/diagnose/retry/init/watch)
src/ralph/config/         # TOML config (three-tier precedence)
src/ralph/daemon/         # Process lifecycle, IPC, SQLite init
src/ralph/pipeline/       # State machine, scheduler, ingestion, healing
src/ralph/worker/         # Claude process spawn, worktree isolation, health
src/ralph/status/         # Status snapshots and terminal tables
src/ralph/render/         # Theme, borders, spinners
src/ralph/diagnose/       # Layer-3 diagnostic reports
src/ralph/retry/          # Manual story re-ingestion
src/ralph/planning/       # BMAD installer integration
src/ralph/watch/          # Live dashboard
src/ralph/common/         # Models, protocol, SQLite schema/store
```

## Key Technical Decisions

Authoritative source: `_bmad-output/planning-artifacts/architecture.md`

- **State persistence**: SQLite + WAL mode (crash-safe, atomic)
- **Daemon IPC**: Unix domain socket with JSON (loopback fallback on Windows)
- **Worker isolation**: Git worktrees (stateless, replaceable)
- **Process model**: `subprocess` for Claude CLI (`claude -p --output-format json`)
- **Claude args**: `RALPH_CLAUDE_ARGS` for permission modes (workers need bypass in non-interactive mode)
- **Async store**: background thread for SQLite writes (`AsyncStateStore`)

## Coding Conventions

- **Python**: 3.11+, stdlib `unittest` for tests
- **Dependencies**: `pyyaml` only (see `pyproject.toml`)
- **Errors**: crate-local exception types in `ralph.common.errors` / module `errors.py`; catch at CLI with user-facing messages
- **Logging**: use structured fields where tracing is added; CLI uses render theme for user output
- **SQLite naming**: snake_case plural tables, `id INTEGER PRIMARY KEY`, `{table_singular}_id` for FKs, ISO 8601 timestamps, 0/1 booleans
- **No bare `except:`** — catch specific exceptions; avoid `print()` in library code (use CLI render layer)

## Testing Patterns

- **Unit/integration tests**: `tests_python/` with stdlib `unittest`
- **Isolation**: every test uses its own `tempfile.TemporaryDirectory()`
- **Fixtures**: `tests_python/helpers.py`, `tests_python/fixtures/fake_claude.py`
- **Run**: `make test-all` before completing any story

## Conventions

- `_bmad/` — BMAD modules installed via `npx bmad-method install` (not a git submodule of BMAD-METHOD source)
- Planning artifacts: `_bmad-output/planning-artifacts/`
- Implementation artifacts: `_bmad-output/implementation-artifacts/` (`sprint-status.yaml`, story `.md` files)
- Workflow sequence: see `WORKFLOW.md` / `WORKFLOW.zh-CN.md`
- **Workflow next-step judgment**: Cross-reference `sprint-status.yaml` with quality artifacts in `_bmad-output/`. A story is not `done` until QA, CR, RV, NR, TR artifacts exist. See `WORKFLOW.md` § "Determining Next Step".
