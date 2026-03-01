# Story 1-2: Mock Claude Code Strategy

> **Status**: Completed
> **Date**: 2026-03-01

## What Was Implemented

### Two-Layer Trait Abstraction

**`crates/ralph-worker/src/process.rs`** — Two async traits with `#[automock]` support:

- `ClaudeProcess` — Factory trait for spawning Claude CLI sessions (`Command` equivalent)
- `ClaudeSessionHandle` — Handle to a running session (`Child` equivalent)

Supporting types: `ClaudeOutput`, `OutputLine`, `OutputStream`.

### Production Implementation

**`crates/ralph-worker/src/process_real.rs`** — `RealClaudeProcess` spawns actual `claude -p --output-format json` processes via `tokio::process::Command` with `kill_on_drop(true)`, piped stdout/stderr, and optional streaming via `mpsc::Sender<OutputLine>`.

### Output Parsing

**`crates/ralph-worker/src/output.rs`** — `parse_claude_output()` pure function parses Claude CLI JSON output into `ClaudeResult` enum (Success / Failure / ParseError). 8 unit tests covering success, error, malformed JSON, missing fields, and edge cases.

### Worker Dependency Injection

**`crates/ralph-worker/src/worker.rs`** — `Worker` now accepts `Arc<dyn ClaudeProcess>` via constructor. 6 unit tests using `MockClaudeProcess`.

### Error Types

**`crates/ralph-worker/src/error.rs`** — `Error` enum: `ProcessSpawnFailed`, `ProcessTimeout`, `KillFailed`, `OutputParseFailed`, `ProcessFailed`, `Io`.

### Fake Claude CLI Binary

**`tests/fake-claude/`** — Environment-variable-driven fake binary supporting 7 modes: `success`, `failure`, `hang`, `crash`, `malformed`, `slow`, `partial`.

### Cross-Crate Mock Support

`ralph-worker` exposes a `mock` feature flag (`dep:mockall`) so downstream crates like `ralph-pipeline` can use `MockClaudeProcess` / `MockClaudeSessionHandle` via `features = ["mock"]` in dev-dependencies.

## Files Changed

| File | Operation |
|------|-----------|
| `crates/ralph-worker/src/error.rs` | Created |
| `crates/ralph-worker/src/process.rs` | Created |
| `crates/ralph-worker/src/process_real.rs` | Created |
| `crates/ralph-worker/src/output.rs` | Created |
| `crates/ralph-worker/src/worker.rs` | Modified |
| `crates/ralph-worker/src/worker_tests.rs` | Modified |
| `crates/ralph-worker/src/lib.rs` | Modified |
| `crates/ralph-worker/Cargo.toml` | Modified |
| `crates/ralph-pipeline/Cargo.toml` | Modified |
| `tests/fake-claude/Cargo.toml` | Created |
| `tests/fake-claude/src/main.rs` | Created |
| `tests/workspace_structure.rs` | Modified |
| `Cargo.toml` (workspace) | Modified |

## Verification

- `cargo test -p ralph-worker` — 14 tests pass (8 output + 6 worker)
- `cargo build -p fake-claude` — compiles successfully
- `make test-all` — full gate passes (65 tests + clippy + fmt)
