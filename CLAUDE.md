# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ralph is an autonomous SDLC pipeline runner — a Rust CLI tool with a long-running daemon that orchestrates parallel Claude Code worker sessions to execute stories 24/7 with self-healing capabilities. It pairs with BMAD-METHOD for planning and shifts delivery from human-in-the-loop to human-on-the-loop.

## Build & Test Commands

```bash
make test              # Run all tests (unit + integration)
make test-unit         # Unit tests only (inline #[cfg(test)] modules)
make test-integration  # Integration tests only (tests/ directory)
make test-cli          # CLI integration tests (ralph binary crate)
make test-all          # All tests + clippy + fmt-check (gate check)
make clippy            # cargo clippy --workspace -- -D warnings
make fmt               # Auto-format
make fmt-check         # Format check without modifying

# Run a specific crate's tests
cargo test -p ralph-pipeline

# Run a specific test by name
cargo test -p ralph-pipeline -- state_tests::tests::valid_transition

# Run tests with output visible
cargo test --workspace -- --nocapture
```

## Architecture

5-crate Cargo workspace with unidirectional dependency flow:

```
ralph (binary)  →  ralph-pipeline  →  ralph-worker  →  ralph-common
      ↘           ralph-config    →  ralph-common
```

| Crate | Role |
|-------|------|
| `ralph-common` | Shared error types (thiserror), state models, SQLite schema, protocol types. No internal deps. |
| `ralph-config` | TOML config resolution with three-tier precedence: CLI flags > project `ralph.toml` > user defaults. |
| `ralph-worker` | Process spawning, health monitoring, git worktree isolation for workers. |
| `ralph-pipeline` | State machine (`StoryState`: Queued→InProgress→InReview→Done/Blocked/Failed), story sequencing, dependency analysis, three-layer self-healing (retry→restart→diagnose). |
| `ralph` | Binary entry point, clap CLI (7 subcommands: start/stop/status/diagnose/retry/init/watch), daemon lifecycle, Unix socket IPC, terminal rendering. |

## Key Technical Decisions

Authoritative source: `_bmad-output/planning-artifacts/architecture.md`

- **State persistence**: SQLite + WAL mode (crash-safe, atomic)
- **Daemon IPC**: Unix Domain Socket with JSON (serde_json)
- **Worker isolation**: Git worktrees (cattle model — stateless, replaceable)
- **Process model**: tokio::process::Command for child processes
- **Async**: tokio full features; mpsc channels for inter-component communication; `spawn_blocking` for all rusqlite calls
- **Shared state**: `Arc<RwLock<T>>` for read-heavy, `Arc<Mutex<T>>` for write-heavy

## Coding Conventions

- **Edition**: Rust 2024, resolver = "3"
- **Toolchain**: stable (pinned via `rust-toolchain.toml` with clippy + rustfmt)
- **Zero warnings**: All code must pass `cargo clippy -- -D warnings` and `cargo fmt --check` before completing any story
- **No `unwrap()`/`panic!()` outside tests** — use thiserror enums per crate, convert with `#[from]`, catch at binary level with anyhow
- **Logging**: structured tracing fields (not format! strings); spans as `tracing::info_span!("pipeline::execute")`; levels: error=user-actionable, warn=healing, info=transitions, debug=logic, trace=verbose
- **SQLite naming**: snake_case plural tables, `id INTEGER PRIMARY KEY`, `{table_singular}_id` for FKs, ISO 8601 timestamps, 0/1 booleans

## Testing Patterns

- **Unit tests**: inline `#[cfg(test)]` modules with rstest fixtures + mockall
- **Integration tests**: `tests/` directory with rstest + tempfile (auto-cleanup TempDir)
- **CLI E2E**: `tests/cli/` with assert_cmd + predicates (black-box binary testing)
- **Async tests**: `#[rstest]` + `#[tokio::test]` combined
- **Parametrized tests**: use `#[case]` instead of multiple assertions per test
- **Isolation**: every test creates its own temp directory, no shared state

## Conventions

- `_bmad/` is a submodule — upgrade via `git submodule update --remote _bmad`
- Planning artifacts live in `_bmad-output/planning-artifacts/` (PRD, architecture, epics, UX design)
- All paths should use environment variables (`$WORKSPACE_ROOT`, `$TOOLS_ROOT`, `$PROJECT_DIR`), not hardcoded project paths
- Workflow execution sequence: see `WORKFLOW.md` for interleaved BMM + TEA step-by-step reference
- **Workflow next-step judgment**: When determining the next workflow step, always cross-reference `sprint-status.yaml` with quality step artifacts in `_bmad-output/`. A story is not truly `done` unless all quality gate artifacts (QA, CR, RV, NR, TR) exist. See `WORKFLOW.md` § "Determining Next Step" for details.
