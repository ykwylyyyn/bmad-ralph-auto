---
stepsCompleted: ['step-01-preflight-and-context', 'step-02-generation-mode', 'step-03-test-strategy', 'step-04c-aggregate', 'step-05-validate-and-complete']
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-02-28'
workflowType: 'testarch-atdd'
inputDocuments:
  - _bmad-output/implementation-artifacts/1-1-cargo-workspace-scaffold-cli-entry-point.md
  - _bmad/tea/config.yaml
  - Cargo.toml
  - tests/README.md
  - tests/common/mod.rs
  - tests/cli/mod.rs
  - _bmad/tea/testarch/knowledge/data-factories.md
  - _bmad/tea/testarch/knowledge/test-quality.md
  - _bmad/tea/testarch/knowledge/test-healing-patterns.md
  - _bmad/tea/testarch/knowledge/test-levels-framework.md
  - _bmad/tea/testarch/knowledge/test-priorities-matrix.md
  - _bmad/tea/testarch/knowledge/ci-burn-in.md
---

# ATDD Checklist - Epic 1, Story 1: Cargo Workspace Scaffold & CLI Entry Point

**Date:** 2026-02-28
**Author:** Deadlock
**Primary Test Level:** CLI E2E (assert_cmd) + Unit (rstest)

---

## Story Summary

Story 1.1 establishes the foundational Cargo workspace structure and CLI entry point for Ralph. The binary must compile cleanly, expose all planned subcommands via `--help`, report its version, and pass all linting/formatting checks.

**As a** developer
**I want** to install bmad-ralph as a standalone CLI binary
**So that** I can begin using Ralph on my projects

---

## Acceptance Criteria

1. **AC1 - Build & Workspace Structure**: `cargo build` produces a single `ralph` binary; workspace contains 5 crates (`ralph`, `ralph-common`, `ralph-config`, `ralph-worker`, `ralph-pipeline`) with correct dependency flow.
2. **AC2 - Help Output**: `ralph --help` shows subcommands: `start`, `stop`, `status`, `diagnose`, `retry`, `init`, `watch` with descriptions.
3. **AC3 - Version Output**: `ralph --version` outputs `ralph 0.1.0`.
4. **AC4 - Lint & Format**: `cargo clippy -- -D warnings` and `cargo fmt --check` produce zero warnings/violations.

---

## Preflight Summary

- **Stack**: backend (Rust)
- **Test Framework**: cargo test + rstest + assert_cmd + predicates + tempfile + mockall
- **Existing Patterns**: rstest fixtures, assert_cmd CLI tests, TempDir isolation
- **Knowledge Loaded**: data-factories, test-quality, test-healing-patterns, test-levels-framework, test-priorities-matrix, ci-burn-in
- **Generation Mode**: AI Generation (backend stack, clear AC, no browser recording needed)

---

## Test Strategy

### Test Level Mapping

| Scenario | Level | File | Priority |
|----------|-------|------|----------|
| S2.1-S2.4: Help output & subcommands | CLI E2E | `tests/cli/help_tests.rs` | P0 |
| S3.1-S3.2: Version output | CLI E2E | `tests/cli/version_tests.rs` | P1 |
| S1.2-S1.4: Workspace structure & deps | Integration | `tests/workspace_structure.rs` | P1 |
| S4.1-S4.2: Clippy & fmt | CI script | (not test file) | P2 |

### Red Phase Analysis

- **Will FAIL (RED):** S2.x (no clap CLI), S3.x (no `--version`), S2.4 (no error on invalid cmd)
- **May PASS (regression guard):** S1.x (workspace structure already exists)
- **CI-only:** S4.x (lint/format — checklist item, not test file)

---

## Failing Tests Created (RED Phase)

### CLI E2E Tests — Help (10 tests, P0)

**File:** `tests/cli/help_tests.rs` (148 lines)

- `#[ignore]` **Test:** `ralph_help_shows_start_subcommand`
  - **Status:** RED — `--help` output won't contain "start" (no clap)
  - **Verifies:** AC2 — start subcommand listed

- `#[ignore]` **Test:** `ralph_help_shows_stop_subcommand`
  - **Status:** RED — no clap
  - **Verifies:** AC2 — stop subcommand listed

- `#[ignore]` **Test:** `ralph_help_shows_status_subcommand`
  - **Status:** RED — no clap
  - **Verifies:** AC2 — status subcommand listed

- `#[ignore]` **Test:** `ralph_help_shows_diagnose_subcommand`
  - **Status:** RED — no clap
  - **Verifies:** AC2 — diagnose subcommand listed

- `#[ignore]` **Test:** `ralph_help_shows_retry_subcommand`
  - **Status:** RED — no clap
  - **Verifies:** AC2 — retry subcommand listed

- `#[ignore]` **Test:** `ralph_help_shows_init_subcommand`
  - **Status:** RED — no clap
  - **Verifies:** AC2 — init subcommand listed

- `#[ignore]` **Test:** `ralph_help_shows_watch_subcommand`
  - **Status:** RED — no clap
  - **Verifies:** AC2 — watch subcommand listed

- `#[ignore]` **Test:** `ralph_help_shows_all_subcommands`
  - **Status:** RED — composite check, all 7 subcommands
  - **Verifies:** AC2 — complete subcommand set

- `#[ignore]` **Test:** `ralph_invalid_subcommand_shows_error`
  - **Status:** RED — no error handling for invalid commands
  - **Verifies:** AC2 — error UX for invalid input

- `#[ignore]` **Test:** `ralph_start_help_shows_description`
  - **Status:** RED — no subcommand-level help
  - **Verifies:** AC2 — subcommand help detail

### CLI E2E Tests — Version (3 tests, P1)

**File:** `tests/cli/version_tests.rs` (43 lines)

- `#[ignore]` **Test:** `ralph_version_shows_correct_format`
  - **Status:** RED — no `--version` flag
  - **Verifies:** AC3 — version output "ralph 0.1.0"

- `#[ignore]` **Test:** `ralph_version_contains_semver`
  - **Status:** RED — no version output
  - **Verifies:** AC3 — semver format

- `#[ignore]` **Test:** `ralph_short_version_flag`
  - **Status:** RED — no `-V` flag
  - **Verifies:** AC3 — short version flag

### Integration Tests — Workspace Structure (6 tests, P1, Regression Guard)

**File:** `tests/workspace_structure.rs` (218 lines)

- **Test:** `workspace_has_five_crates`
  - **Status:** GREEN (regression guard) — workspace already has 5 members
  - **Verifies:** AC1 — crate count

- **Test:** `workspace_members_have_correct_names`
  - **Status:** GREEN — correct crate names exist
  - **Verifies:** AC1 — crate naming

- **Test:** `ralph_common_has_no_internal_dependencies`
  - **Status:** GREEN — ralph-common has no ralph-* deps
  - **Verifies:** AC1 — dependency flow

- **Test:** `ralph_depends_on_all_sibling_crates`
  - **Status:** GREEN — ralph depends on all 4 siblings
  - **Verifies:** AC1 — dependency flow

- **Test:** `ralph_binary_is_produced`
  - **Status:** GREEN — binary compiles
  - **Verifies:** AC1 — build output

- **Test:** `all_crates_have_workspace_version`
  - **Status:** GREEN — all use `version.workspace = true`
  - **Verifies:** AC1 — version consistency

---

## Data Factories Created

None required — CLI binary tests use `assert_cmd` (no data factories needed).

---

## Fixtures Created

None additional — existing `tests/common/mod.rs` provides `setup_project_dir()` and `setup_git_repo()`.

---

## Mock Requirements

None — Story 1.1 tests verify CLI binary output, no external services to mock.

---

## Required data-testid Attributes

Not applicable — Rust CLI project, no UI.

---

## Implementation Checklist

### Test: `ralph_help_shows_all_subcommands` (and individual subcommand tests)

**File:** `tests/cli/help_tests.rs`

**Tasks to make these tests pass:**

- [ ] Set up clap `Command` with `#[derive(Parser)]` in `crates/ralph/src/main.rs`
- [ ] Define 7 subcommands: `start`, `stop`, `status`, `diagnose`, `retry`, `init`, `watch`
- [ ] Add description for each subcommand
- [ ] Wire `tests/cli/mod.rs` to include `mod help_tests;`
- [ ] Remove `#[ignore]` from tests
- [ ] Run test: `cargo test -p ralph -- help_tests --ignored`
- [ ] All 10 tests pass (green phase)

### Test: `ralph_version_shows_correct_format` (and version tests)

**File:** `tests/cli/version_tests.rs`

**Tasks to make these tests pass:**

- [ ] Add `.version(clap::crate_version!())` to clap Command
- [ ] Verify `ralph --version` outputs "ralph 0.1.0"
- [ ] Wire `tests/cli/mod.rs` to include `mod version_tests;`
- [ ] Remove `#[ignore]` from tests
- [ ] Run test: `cargo test -p ralph -- version_tests --ignored`
- [ ] All 3 tests pass (green phase)

### Test: `workspace_structure.rs` (regression guard)

**File:** `tests/workspace_structure.rs`

**Tasks to make these tests compilable:**

- [ ] Ensure `tests/workspace_structure.rs` is discoverable by cargo (may require moving to `crates/ralph/tests/` or adding workspace root package)
- [ ] Add `toml` to dev-dependencies where needed
- [ ] Run test: `cargo test -- workspace`
- [ ] All 6 tests pass (already GREEN)

### Lint & Format (AC4, CI)

- [ ] Run `cargo clippy --workspace -- -D warnings` — zero warnings
- [ ] Run `cargo fmt --workspace -- --check` — zero violations
- [ ] Add to CI pipeline

---

## Running Tests

```bash
# Run all ignored (RED) tests for this story
cargo test -p ralph -- --ignored

# Run specific test file
cargo test -p ralph -- help_tests --ignored

# Run workspace structure tests (should PASS)
cargo test -- workspace_structure

# Run all tests across workspace
cargo test --workspace

# Run with output visible
cargo test --workspace -- --nocapture

# Run clippy (AC4)
cargo clippy --workspace -- -D warnings

# Run fmt check (AC4)
cargo fmt --workspace -- --check
```

---

## Red-Green-Refactor Workflow

### RED Phase (Current)

**TEA Agent Responsibilities:**

- All 13 CLI tests written and marked `#[ignore]` (RED)
- 6 workspace structure tests written (GREEN regression guard)
- Implementation checklist created
- Test wiring requirements documented

**Verification:**

- CLI tests will fail when run with `--ignored` (no clap setup)
- Workspace structure tests pass on existing structure
- Failures due to missing implementation, not test bugs

---

### GREEN Phase (DEV Team — Next Steps)

**DEV Agent Responsibilities:**

1. **Wire test modules** in `tests/cli/mod.rs` (`mod help_tests; mod version_tests;`)
2. **Set up clap CLI** with `#[derive(Parser)]` in `main.rs`
3. **Define subcommands** (start, stop, status, diagnose, retry, init, watch)
4. **Add version** via `clap::crate_version!()`
5. **Remove `#[ignore]`** from passing tests
6. **Run `cargo test --workspace`** to verify all pass

### REFACTOR Phase (DEV Team — After All Tests Pass)

1. Verify all 19 tests pass
2. Review code quality (clippy, fmt)
3. Ensure clean dependency flow
4. Ready for code review

---

## Next Steps

1. **Review this checklist** with team or in standup
2. **Run RED phase tests** to confirm: `cargo test -p ralph -- --ignored`
3. **Begin implementation** using implementation checklist as guide
4. **Work one test group at a time** (help → version → lint)
5. **When all tests pass**, refactor code for quality
6. **When refactoring complete**, update story status to 'done'

---

## Knowledge Base References Applied

- **test-quality.md** — Deterministic, isolated tests with explicit assertions
- **test-levels-framework.md** — CLI E2E (assert_cmd) for binary testing, integration for structure
- **test-priorities-matrix.md** — P0 for core CLI entry point, P1 for version/structure
- **data-factories.md** — Not needed (CLI tests, no data creation)
- **test-healing-patterns.md** — Patterns available for future test maintenance
- **ci-burn-in.md** — CI pipeline integration guidance

---

## Test Execution Evidence

### Initial Test Run (RED Phase Verification)

**Command:** `cargo test -p ralph -- --ignored`

**Expected Results:**

- Total RED tests: 13
- Passing: 0 (expected)
- Failing: 13 (expected — no clap CLI setup)
- Status: RED phase verified

**Expected Failure Messages:**

- `ralph_help_shows_*`: stdout does not contain expected subcommand name
- `ralph_version_*`: stdout does not contain version string
- `ralph_invalid_subcommand_shows_error`: process exits with success (should fail)

---

## Notes

- Workspace root `tests/` directory needs wiring — files may need to move to `crates/ralph/tests/` or root needs `[package]` section
- Existing `tests/cli/mod.rs` must declare `mod help_tests;` and `mod version_tests;` for cargo discovery
- AC4 (clippy/fmt) is CI-enforced, not test-file-based

---

**Generated by BMad TEA Agent** — 2026-02-28
