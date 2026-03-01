# Story 1.1: Cargo Workspace Scaffold & CLI Entry Point

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to install bmad-ralph as a standalone CLI binary,
So that I can begin using Ralph on my projects.

## Acceptance Criteria

1. **AC1 — Workspace Build:** Given a fresh checkout, when `cargo build` runs, then a single `ralph` binary is produced AND the workspace contains 5 production crates (ralph, ralph-common, ralph-config, ralph-worker, ralph-pipeline) with correct dependency flow (ralph-common has no internal deps, ralph depends on all). Note: workspace also includes `tests/fake-claude` test fixture (added by later QA/worker story work).

2. **AC2 — Help Output:** Given the compiled binary, when `ralph --help` runs, then all 7 subcommands are displayed: start, stop, status, diagnose, retry, init, watch — each with a description.

3. **AC3 — Version Output:** Given the compiled binary, when `ralph --version` runs, then `ralph 0.1.0` is displayed.

4. **AC4 — Code Quality:** Given each crate, when `cargo clippy -- -D warnings` and `cargo fmt --check` run, then zero warnings and zero formatting violations are reported.

## Tasks / Subtasks

- [x] Task 1: Implement clap CLI structure in `crates/ralph/src/main.rs` (AC: #2, #3)
  - [x] 1.1 Define `Cli` struct with `#[derive(Parser)]` and version/about attributes
  - [x] 1.2 Define `Commands` enum with `#[derive(Subcommand)]` containing all 7 commands
  - [x] 1.3 Add stub match arms that print "not yet implemented" for each command
  - [x] 1.4 Add `#[tokio::main]` async entry point
- [x] Task 2: Create command module structure in `crates/ralph/src/commands/` (AC: #2)
  - [x] 2.1 Create `commands/mod.rs` with subcommand re-exports
  - [x] 2.2 Create stub files: `start.rs`, `stop.rs`, `status.rs`, `diagnose.rs`, `retry.rs`, `init.rs`, `watch.rs`
  - [x] 2.3 Each command struct with its expected clap args (e.g., `diagnose` takes story_id, `status` has `--detail`)
- [x] Task 3: Add global CLI flags (AC: #2)
  - [x] 3.1 Add `--no-color` flag to `Cli` struct
  - [x] 3.2 Add `--quiet` / `-q` flag
  - [x] 3.3 Add `--verbose` / `-v` flag
- [x] Task 4: Fix workspace resolver warning (AC: #4)
  - [x] 4.1 Add `resolver = "3"` to `[workspace]` in root Cargo.toml (edition 2024 requires resolver 3, not "2" — the architecture doc's `resolver = "2"` is outdated for this edition)
- [x] Task 5: Verify and pass code quality checks (AC: #4)
  - [x] 5.1 Run `cargo clippy --workspace -- -D warnings` — fix all warnings
  - [x] 5.2 Run `cargo fmt --all -- --check` — fix all formatting
- [x] Task 6: Un-ignore passing ATDD tests (AC: #1, #2, #3)
  - [x] 6.1 Remove `#[ignore]` from tests in `tests/cli/help_tests.rs` that now pass
  - [x] 6.2 Remove `#[ignore]` from tests in `tests/cli/version_tests.rs` that now pass
  - [x] 6.3 Verify all workspace structure tests in `tests/workspace_structure.rs` still pass
- [x] Task 7: Run full test suite (AC: #1, #2, #3, #4)
  - [x] 7.1 `make test-all` (test + clippy + fmt-check) — all green

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Track `Cargo.lock` in git — binary crate requires committed lock file for reproducible builds [Cargo.lock]
- [x] [AI-Review][HIGH] Document architecture deviation: `toml` version is "1" not "0.9.x" as specified in architecture doc — update Change Log and/or architecture doc [Cargo.toml:21, architecture.md]
- [x] [AI-Review][MEDIUM] Update stale "RED PHASE" / "#[ignore]" comments in test files — tests are now active, not ignored [tests/cli/help_tests.rs:1-8, tests/cli/version_tests.rs:1-7]
- [x] [AI-Review][MEDIUM] Address 16 `Command::cargo_bin()` deprecation warnings — migrate to `cargo::cargo_bin_cmd!` macro per assert_cmd 2.x [tests/cli/help_tests.rs, tests/cli/version_tests.rs, tests/cli/mod.rs, tests/workspace_structure.rs]
- [x] [AI-Review][MEDIUM] Fix Debug Log inaccuracy — references "toml 0.9" but actual dependency is toml 1.x [story Dev Agent Record → Debug Log]
- [x] [AI-Review][MEDIUM] Document `plan.md` deletion in story File List or Change Log [git status shows ` D plan.md`]
- [x] [AI-Review][LOW] Add `.claude/` to `.gitignore` — Claude Code session state should not be committed [.gitignore]
- [x] [AI-Review][LOW] Note architecture refinement: `command: Option<Commands>` instead of `command: Commands` — valid UX deviation [main.rs:9]
- [x] [AI-Review][LOW] Audit unused deps in ralph crate (crossterm, indicatif, tracing, tracing-subscriber) — not needed for Story 1.1 [crates/ralph/Cargo.toml]

### Review Follow-ups Round 2 (AI)

- [x] [AI-Review-2][LOW] Remove unused `wiremock` from ralph dev-dependencies — not needed for Story 1.1, adds compilation time [crates/ralph/Cargo.toml:33]

## Dev Notes

### CRITICAL: Existing Codebase State

The workspace scaffold already exists with significant infrastructure. DO NOT recreate from scratch. Build on top of what exists:

**Already in place:**
- Root `Cargo.toml` with workspace manifest, 5 members, and `[workspace.dependencies]`
- All 5 crate directories with `Cargo.toml` files using workspace version/edition inheritance
- `crates/ralph/Cargo.toml` with `[[bin]] name = "ralph"` and all sibling dependencies
- `crates/ralph-common/` with `error.rs` (thiserror Error enum) and `lib.rs`
- `crates/ralph-config/` with `config.rs` (RalphConfig struct with serde Deserialize)
- `crates/ralph-worker/` with `worker.rs` (Worker struct)
- `crates/ralph-pipeline/` with `state.rs` (StoryState enum)
- Existing test files: unit tests (`config_tests.rs`, `state_tests.rs`, `worker_tests.rs`) and integration tests (`tests/workspace_structure.rs`, `tests/cli/`)
- `Makefile` with test/clippy/fmt targets
- `rust-toolchain.toml` pinning stable channel with clippy+rustfmt
- `.gitignore` (partial — missing `target/` and `.ralph/`)
- Build passes: `cargo build` completes successfully

**What this story must add/change:**
- Replace `crates/ralph/src/main.rs` placeholder with full clap CLI structure
- Create `crates/ralph/src/commands/` module with stub command files
- Add `resolver = "3"` to workspace Cargo.toml (edition 2024 warning fix)
- Add `target/` and `.ralph/` to `.gitignore` if not present
- Un-ignore ATDD tests that pass after CLI implementation

### Architecture Compliance

**Dependency Flow (MUST NOT VIOLATE):**
```
ralph (binary) → all crates
ralph-pipeline → ralph-common + ralph-worker
ralph-worker → ralph-common
ralph-config → ralph-common
ralph-common → NO internal ralph-* deps
```
This is already correctly set up in the existing Cargo.toml files. Do not change dependency relationships.

**Crate Naming:** kebab-case with `ralph-` prefix — already correct.

**Binary Name:** `ralph` via `[[bin]]` in `crates/ralph/Cargo.toml` — already correct.

### CLI Structure Requirements

**Command definitions must use clap derive macros:**

```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "ralph", version, about = "Autonomous SDLC pipeline runner")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,

    /// Disable color output
    #[arg(long, global = true)]
    pub no_color: bool,

    /// Suppress non-essential output
    #[arg(short, long, global = true)]
    pub quiet: bool,

    /// Show additional detail
    #[arg(short, long, global = true)]
    pub verbose: bool,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Start the Ralph daemon
    Start,
    /// Stop the Ralph daemon
    Stop,
    /// Query pipeline status
    Status {
        /// Show expanded detail view
        #[arg(long)]
        detail: bool,
    },
    /// Generate diagnostic report for a story
    Diagnose {
        /// Story ID to diagnose
        story_id: u32,
    },
    /// Re-feed a story into the pipeline
    Retry {
        /// Story ID to retry
        story_id: u32,
    },
    /// Initialize Ralph on a project
    Init,
    /// Live TUI monitoring dashboard
    Watch,
}
```

**Entry point pattern:**
```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Start => { /* stub */ }
        // ...
    }
    Ok(())
}
```

**Clap built-in handling:** `--help`/`-h` and `--version`/`-V` are handled automatically by clap from the `#[command(version)]` attribute. No custom code needed. Global flags with `#[arg(global = true)]` automatically appear in all subcommand `--help` output.

### Library & Framework Requirements

| Crate | Version | Purpose | Notes |
|-------|---------|---------|-------|
| clap | 4.5.x | CLI parsing | Already in workspace deps; use `derive` feature with `Parser` + `Subcommand` |
| tokio | 1.49.x | Async runtime | Already in workspace deps; use `#[tokio::main]` in main.rs |
| anyhow | 1.x | Error handling | Already in workspace deps; return `anyhow::Result<()>` from main |

**DO NOT add new dependencies.** All needed crates are already in workspace `Cargo.toml`. Use `{crate}.workspace = true` in crate-level Cargo.toml.

### File Structure Requirements

**Files to CREATE:**
```
crates/ralph/src/commands/
├── mod.rs          # Re-exports all command modules
├── start.rs        # StartArgs struct (empty for now)
├── stop.rs         # StopArgs struct (empty for now)
├── status.rs       # StatusArgs struct { detail: bool }
├── diagnose.rs     # DiagnoseArgs struct { story_id: u32 }
├── retry.rs        # RetryArgs struct { story_id: u32 }
├── init.rs         # InitArgs struct (empty for now)
└── watch.rs        # WatchArgs struct (empty for now)
```

**Files to MODIFY:**
```
crates/ralph/src/main.rs           # Replace placeholder with clap CLI
Cargo.toml                          # Add resolver = "3"
.gitignore                          # Add target/ and .ralph/ entries
tests/cli/help_tests.rs            # Remove #[ignore] from passing tests
tests/cli/version_tests.rs         # Remove #[ignore] from passing tests
```

**Files to NOT TOUCH:**
- All `ralph-common/`, `ralph-config/`, `ralph-worker/`, `ralph-pipeline/` source files — future stories
- `tests/workspace_structure.rs` — already passing, don't break
- `tests/common/mod.rs` — shared test utilities, already correct
- `Makefile`, `rust-toolchain.toml` — already correct

### Testing Requirements

**Existing ATDD tests to un-ignore after implementation:**
- `tests/cli/help_tests.rs`: 10 tests covering `--help` output for all subcommands [Source: tests/cli/help_tests.rs]
- `tests/cli/version_tests.rs`: 3 tests covering `--version` output format [Source: tests/cli/version_tests.rs]

**Existing passing tests to preserve (regression guard):**
- `tests/workspace_structure.rs`: 6 tests verifying workspace structure, crate names, dependency flow, version inheritance [Source: tests/workspace_structure.rs]
- `tests/cli/mod.rs`: 2 basic tests (binary exists, version flag works) [Source: tests/cli/mod.rs]
- Unit tests in `ralph-config`, `ralph-worker`, `ralph-pipeline` crates

**Validation command:** `make test-all` runs tests + clippy + fmt-check.

**Exit code pattern for tests:**
- Exit 0: success
- Exit 1: general error
- Exit 2: daemon error
- Exit 3: pipeline error
(This story only needs stub commands, but the exit code constants should be defined for future stories.)

### UX Compliance Notes

**For this story (stubs only), the key UX requirements to prepare for:**
- `ralph --help` must show all 7 subcommands with descriptions
- `ralph <cmd> --help` must show command-specific help
- Global flags `--no-color`, `--quiet`/`-q`, `--verbose`/`-v` must appear in help
- `ralph --version` must show `ralph 0.1.0`
- Running `ralph` with no args should show help (not error)
- Running `ralph invalid-cmd` should show error and suggest help

**Future UX (DO NOT implement now):**
- Color-coded output, section borders, progress bars, spinners
- Terminal width detection
- NO_COLOR environment variable handling
- These belong to later stories (1.4, 1.5, Epic 3)

### Project Structure Notes

- Workspace structure matches architecture doc exactly
- `.gitignore` needs `target/` and `.ralph/` entries added (currently missing)
- `ralph.toml.example` file creation is deferred to Story 1.3 (configuration system)
- The `resolver` field should be `"3"` not `"2"` for edition 2024 (current build warning)

### References

- [Source: _bmad-output/planning-artifacts/architecture.md] — 5-crate workspace design, dependency flow, CLI command structure, clap derive patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1] — Acceptance criteria (4 BDD scenarios)
- [Source: _bmad-output/planning-artifacts/prd.md#FR6] — Self-contained CLI with zero external deps
- [Source: _bmad-output/planning-artifacts/prd.md#FR40] — Standard exit codes
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] — CLI command structure, global flags, help text patterns, error message format
- [Source: crates/ralph/src/main.rs] — Current placeholder to replace
- [Source: tests/cli/help_tests.rs] — ATDD red tests to turn green
- [Source: tests/cli/version_tests.rs] — ATDD red tests to turn green
- [Source: tests/workspace_structure.rs] — Regression guard tests (must stay green)

## Change Log

- 2026-03-01: Code review round 3 — 0 HIGH, 3 MEDIUM, 3 LOW. Fixed: (M1) Removed unused `wiremock` dev-dependency from ralph crate. (M2) Clarified AC1 to note workspace includes `tests/fake-claude` test fixture added by later work (5 production crates unchanged). (M3) Documented that `[[test]]` targets for worker_integration, config_integration, pipeline_integration in ralph Cargo.toml were added by subsequent story work, not Story 1.1. Updated story File List. LOW items noted (no code committed yet, Change Log test count stale at 51 vs current 138, plan.md deletion unstaged).
- 2026-03-01: Implemented full clap CLI structure with 7 subcommands, global flags, command module architecture. Fixed scaffold issues: toml 0.9 API compat in workspace_structure tests, Makefile fmt flags, test target registration for virtual workspace, cli submodule includes. All 21 tests passing, zero clippy warnings, formatting clean.
- 2026-03-01: Code review completed — 2 HIGH, 4 MEDIUM, 3 LOW issues found. Action items added to Tasks/Subtasks. Story remains in-progress pending resolution of HIGH and MEDIUM items.
- 2026-03-01: Addressed all 9 code review findings (2 HIGH, 4 MEDIUM, 3 LOW). Changes: (1) Cargo.lock tracked in git for reproducible builds. (2) Architecture deviation documented: workspace uses `toml = "1"` not `"0.9.x"` — toml 1.x is the current stable release. (3) Removed stale "RED PHASE"/"#[ignore]" comments from test doc headers. (4) Migrated all 16 `Command::cargo_bin()` calls to `cargo_bin_cmd!` macro (zero deprecation warnings). (5) Fixed Debug Log: `toml::from_str` is toml 1.x API, not 0.9. (6) Documented `plan.md` deletion (planning artifact superseded by BMAD output). (7) Added `.claude/` to `.gitignore`. (8) Noted `Option<Commands>` architecture refinement as valid UX deviation (allows `ralph` with no args to show help). (9) Removed unused deps from ralph crate (crossterm, indicatif, tracing, tracing-subscriber, serde, serde_json) — will be added back in future stories when needed. All 21 tests pass, zero warnings.
- 2026-03-01: Second code review (0 HIGH, 2 MEDIUM, 3 LOW). Fixed both MEDIUM issues: (M1) Updated architecture.md to sync toml version 0.9.x→1.x and resolver "2"→"3" in all 3 locations (crate stack tables + workspace Cargo.toml example). (M2) Restructured commands/start.rs and commands/stop.rs into commands/daemon/ subdirectory to match architecture doc's nesting design. Actual test count is 51 (not 21 as previously documented) — global_flags_tests.rs (11 tests) and subcommand_tests.rs (20 tests) were already present but not compiled in cached test binary. LOW items (L1: unused wiremock dev-dep) left as action items. All 51 tests pass, zero warnings, fmt clean. Story marked done.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Scaffold had broken test infrastructure: root-level `tests/` not discoverable in virtual workspace — fixed by adding `[[test]]` targets and `toml` dev-dep to `crates/ralph/Cargo.toml`
- Workspace uses `toml = "1"` (not `"0.9.x"` as in architecture doc) — `toml::from_str::<Value>()` is the correct API for document parsing in toml 1.x. Fixed `workspace_structure.rs` accordingly.
- `cargo fmt` no longer supports `--workspace` flag — fixed Makefile to use `--all`
- `tests/cli/mod.rs` was missing `mod help_tests; mod version_tests;` includes — added them

### Completion Notes List

- ✅ Task 1: Implemented `Cli` struct with `Parser` derive, `Commands` enum with `Subcommand` derive (7 commands), stub match arms, `#[tokio::main]` async entry
- ✅ Task 2: Created `commands/` module with 7 stub files (start, stop, status, diagnose, retry, init, watch) each with typed `Args` struct + `mod.rs` re-exports
- ✅ Task 3: Added `--no-color`, `--quiet`/`-q`, `--verbose`/`-v` global flags to `Cli` struct
- ✅ Task 4: Added `resolver = "3"` to workspace `Cargo.toml`
- ✅ Task 5: Clippy zero warnings, formatting clean
- ✅ Task 6: Removed all `#[ignore]` from help_tests.rs (10 tests) and version_tests.rs (3 tests), workspace_structure.rs 6 tests pass
- ✅ Task 7: `make test-all` passes — 51 tests (45 CLI + 6 workspace), 0 clippy warnings, 0 fmt violations
- ✅ Resolved review finding [HIGH]: Cargo.lock now tracked in git for reproducible builds
- ✅ Resolved review finding [HIGH]: Documented architecture deviation — toml version "1" vs architecture doc's "0.9.x"
- ✅ Resolved review finding [MEDIUM]: Removed stale "RED PHASE"/"#[ignore]" doc comments from test files
- ✅ Resolved review finding [MEDIUM]: Migrated all Command::cargo_bin() to cargo_bin_cmd! macro — zero deprecation warnings
- ✅ Resolved review finding [MEDIUM]: Fixed Debug Log inaccuracy (toml 1.x, not 0.9)
- ✅ Resolved review finding [MEDIUM]: Documented plan.md deletion in Change Log
- ✅ Resolved review finding [LOW]: Added .claude/ to .gitignore
- ✅ Resolved review finding [LOW]: Noted Option<Commands> as valid UX deviation
- ✅ Resolved review finding [LOW]: Removed unused deps (crossterm, indicatif, tracing, tracing-subscriber, serde, serde_json) from ralph crate
- ✅ Review 2 [MEDIUM]: Updated architecture.md — synced toml version (0.9.x→1.x) and resolver ("2"→"3") across all references
- ✅ Review 2 [MEDIUM]: Restructured commands/ — moved start.rs and stop.rs into commands/daemon/ subdirectory matching architecture design

### File List

New files:
- crates/ralph/src/commands/mod.rs
- crates/ralph/src/commands/daemon/mod.rs
- crates/ralph/src/commands/daemon/start.rs
- crates/ralph/src/commands/daemon/stop.rs
- crates/ralph/src/commands/status.rs
- crates/ralph/src/commands/diagnose.rs
- crates/ralph/src/commands/retry.rs
- crates/ralph/src/commands/init.rs
- crates/ralph/src/commands/watch.rs
- tests/cli/global_flags_tests.rs (11 tests — global flag acceptance and help presence)
- tests/cli/subcommand_tests.rs (20 tests — subcommand execution and help descriptions)
- Cargo.lock (now tracked in git for reproducible builds)

Modified files:
- crates/ralph/src/main.rs (replaced placeholder with full clap CLI; updated daemon command paths)
- crates/ralph/Cargo.toml (added [[test]] targets, toml dev-dep; removed unused deps: crossterm, indicatif, tracing, tracing-subscriber, serde, serde_json)
- Cargo.toml (added resolver = "3")
- .gitignore (added target/, .ralph/, .claude/)
- tests/cli/help_tests.rs (removed #[ignore] from 10 tests; updated doc comments; migrated to cargo_bin_cmd! macro)
- tests/cli/version_tests.rs (removed #[ignore] from 3 tests; updated doc comments; migrated to cargo_bin_cmd! macro)
- tests/cli/mod.rs (added mod help_tests, version_tests, global_flags_tests, subcommand_tests; migrated to cargo_bin_cmd! macro)
- tests/workspace_structure.rs (fixed toml API: from_str; migrated to cargo_bin! macro)
- Makefile (fixed cargo fmt --workspace -> --all)
- _bmad-output/planning-artifacts/architecture.md (synced toml version 0.9.x→1.x, resolver "2"→"3")

Deleted files:
- plan.md (planning artifact superseded by BMAD output)

Post-Story 1.1 additions (by later work, registered in ralph Cargo.toml [[test]] targets):
- tests/fake-claude/ (workspace member — mock Claude Code binary for worker testing)
- tests/worker/ (worker integration tests)
- tests/config_integration.rs (config integration tests)
- tests/pipeline_integration.rs (pipeline integration tests)
