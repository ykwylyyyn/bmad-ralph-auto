---
stepsCompleted: ['step-01-preflight', 'step-02-select-framework', 'step-03-scaffold-framework', 'step-04-docs-and-scripts', 'step-05-validate-and-summary']
lastStep: 'step-05-validate-and-summary'
lastSaved: '2026-02-28'
status: 'complete'
---

# Framework Setup Progress - bmad-ralph (Ralph)

## Step 1: Preflight Checks

### Stack Detection

- **Config `test_stack_type`:** auto
- **Detected Stack:** `backend` (Rust CLI + daemon)
- **Language:** Rust
- **Build System:** Cargo
- **Async Runtime:** Tokio

### Prerequisites Validation

| Prerequisite | Status |
|---|---|
| Backend manifest (`Cargo.toml`) | NOT YET CREATED (greenfield) |
| Existing test framework | None |
| Architecture docs available | YES |
| Project type identified | Rust CLI tool with daemon |

### Project Context

- **Project:** bmad-ralph (Ralph pipeline orchestrator)
- **Type:** Rust CLI tool with long-running daemon process
- **Architecture:** Daemon + Workers (Claude Code sessions) + State Machine + Self-Healing
- **Key Planned Dependencies:** Tokio, crossterm, indicatif, TOML parser
- **Distribution:** Standalone binary
- **Testing Approach:** Adapted TEA patterns for Rust ecosystem

### Architecture Docs Found

- `_bmad-output/planning-artifacts/architecture.md` (40 KB)
- `_bmad-output/planning-artifacts/prd.md` (22 KB)
- `_bmad-output/planning-artifacts/epics.md` (46 KB)
- `_bmad-output/planning-artifacts/ux-design-specification.md` (78 KB)
- `_bmad-output/planning-artifacts/implementation-readiness-report-2026-02-28.md` (26 KB)

### Decision

- TEA Framework workflow adapted for Rust backend testing patterns
- Will use: `cargo test`, `rstest` (fixtures + parametrize), `assert_cmd`, `predicates`, `tokio::test`, `tempfile`
- Directory structure follows Rust conventions (`tests/` for integration, `src/` inline for unit)

## Step 2: Framework Selection

### Selected Framework

**`cargo test` (Rust built-in)** + curated test crate stack

### Rationale

- `{detected_stack}` = `backend`, Language = Rust
- `config.test_framework` = `auto` → auto-detected as `cargo test`
- Rust's built-in test framework is the standard and only practical choice
- No browser-based testing needed (CLI tool)

### Test Crate Stack

| Crate | Version | Purpose | Category |
|---|---|---|---|
| `rstest` | 0.26.1 | Fixture injection, parametrized tests (`#[rstest]` + `#[case]`), async support (`#[future]`/`#[awt]`) | Core Framework |
| `rstest_reuse` | latest | Test templates via `#[template]`/`#[apply]` for reusable parametrization | Core Framework |
| `assert_cmd` | latest | CLI binary integration testing | Integration |
| `predicates` | latest | Fluent assertions for CLI output | Integration |
| `tokio::test` | (via tokio) | Async test runtime for daemon/worker tests | Async |
| `tempfile` | latest | Isolated temp directories for TOML configs and state files | Isolation |
| `mockall` | latest | Mock traits for unit testing (dependency injection) | Unit |
| `wiremock` | latest | HTTP mock server (for HTTP API endpoint tests) | Integration |

### Test Directory Structure (Rust Convention)

```
ralph/
├── src/
│   ├── lib.rs          # Library root (unit tests inline via #[cfg(test)])
│   ├── daemon/
│   │   ├── mod.rs      # #[cfg(test)] mod tests { ... }
│   │   └── ...
│   ├── pipeline/
│   ├── worker/
│   └── ...
├── tests/              # Integration tests (each file = separate crate)
│   ├── cli_tests.rs    # CLI integration tests (assert_cmd)
│   ├── daemon_tests.rs # Daemon lifecycle tests
│   ├── pipeline_tests.rs
│   └── common/
│       └── mod.rs      # Shared test utilities
├── Cargo.toml          # [dev-dependencies] for test crates
└── tests/README.md     # Test documentation
```

### Test Levels Mapping (TEA → Rust)

| TEA Level | Rust Equivalent | Tool |
|---|---|---|
| E2E Tests | CLI integration tests | `assert_cmd` + `predicates` |
| API Tests | HTTP endpoint integration tests | `wiremock` + `reqwest` |
| Component Tests | Module-level integration tests | `tests/*.rs` |
| Unit Tests | Inline `#[cfg(test)]` modules | Built-in |

## Step 3: Scaffold Framework

### Files Created

#### Workspace Configuration
- `Cargo.toml` — workspace root with 5 crate members + all dev-dependencies
- `rust-toolchain.toml` — stable channel with clippy + rustfmt

#### Crate Cargo.toml Files (with dev-dependencies)
- `crates/ralph/Cargo.toml` — binary crate (assert_cmd, predicates, wiremock)
- `crates/ralph-common/Cargo.toml` — shared types (rstest, tempfile)
- `crates/ralph-config/Cargo.toml` — config resolution (rstest, tempfile)
- `crates/ralph-worker/Cargo.toml` — worker management (rstest, tempfile, mockall, tokio test-util)
- `crates/ralph-pipeline/Cargo.toml` — state machine (rstest, tempfile, mockall, tokio test-util)

#### Minimal Source Stubs
- `crates/ralph-common/src/lib.rs` + `error.rs`
- `crates/ralph-config/src/lib.rs` + `config.rs` (RalphConfig struct)
- `crates/ralph-worker/src/lib.rs` + `worker.rs` (Worker struct)
- `crates/ralph-pipeline/src/lib.rs` + `state.rs` (StoryState enum)
- `crates/ralph/src/main.rs`

#### Test Infrastructure
- `tests/common/mod.rs` — shared test utilities (setup_project_dir, setup_git_repo, default_config)
- `tests/cli/mod.rs` — CLI integration tests (assert_cmd + predicates)

#### Sample Tests (demonstrating rstest patterns)
- `crates/ralph-config/src/config_tests.rs` — fixtures, parametrized tests, file-based tests
- `crates/ralph-pipeline/src/state_tests.rs` — state transition parametrized tests
- `crates/ralph-worker/src/worker_tests.rs` — async tests, fixture composition

### Patterns Demonstrated

| Pattern | File | rstest Feature |
|---|---|---|
| Fixture injection | `config_tests.rs` | `#[fixture]` → `config_dir()`, `valid_toml()` |
| Parametrized tests | `config_tests.rs` | `#[rstest] #[case]` → `parse_max_workers` |
| Fixture composition | `worker_tests.rs` | `test_worker` uses `worktree_dir` fixture |
| Async + rstest | `worker_tests.rs` | `#[rstest] #[tokio::test]` |
| CLI black-box | `tests/cli/mod.rs` | `assert_cmd::Command` + `predicates` |
| Temp dir isolation | `tests/common/mod.rs` | `tempfile::TempDir` with auto-cleanup |

## Step 4: Documentation & Scripts

### Files Created
- `tests/README.md` — test suite documentation (setup, running, architecture, best practices, CI)
- `Makefile` — test/lint/format targets (test, test-unit, test-integration, test-cli, clippy, fmt)

## Step 5: Validation & Summary

### Validation Result: PASS

All checklist items validated (adapted for Rust backend context). See validation table above.

### Completion Summary

**Framework:** `cargo test` (Rust built-in) + rstest 0.26 + curated crate stack

**Artifacts Created:**

| Category | Files | Count |
|---|---|---|
| Workspace config | `Cargo.toml`, `rust-toolchain.toml` | 2 |
| Crate Cargo.toml | `crates/ralph*/Cargo.toml` | 5 |
| Source stubs | `crates/ralph*/src/*.rs` | 9 |
| Test infrastructure | `tests/common/mod.rs`, `tests/cli/mod.rs` | 2 |
| Sample unit tests | `*_tests.rs` (config, state, worker) | 3 |
| Documentation | `tests/README.md` | 1 |
| Build scripts | `Makefile` | 1 |
| **Total** | | **23** |

**Next Steps:**

1. Run `cargo build --workspace` to verify compilation
2. Run `cargo test --workspace` to verify test infrastructure
3. Proceed to **ATDD workflow** to generate failing acceptance tests for a story
4. Or proceed to **test-design workflow** to plan comprehensive test coverage

**Knowledge Base References Applied:**
- TEA test levels framework → adapted for Rust (E2E=CLI, API=wiremock, Component=integration, Unit=inline)
- TEA fixture patterns → adapted to rstest `#[fixture]` injection
- TEA data factory patterns → adapted to Rust test utilities in `tests/common/`
- TEA test quality principles → one-assertion-per-test, determinism, isolation via tempfile

---

**Generated by BMad TEA Agent** — 2026-02-28
**Framework Workflow: COMPLETE**
