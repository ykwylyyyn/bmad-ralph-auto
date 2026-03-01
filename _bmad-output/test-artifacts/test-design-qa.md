---
stepsCompleted: ['step-05-generate-output']
lastStep: 'step-05-generate-output'
lastSaved: '2026-02-28'
workflowType: 'testarch-test-design'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/epics.md'
---

# Test Design for QA: bmad-ralph

**Purpose:** Test execution recipe for bmad-ralph. Defines what to test, how to test it, and what is needed from development.

**Date:** 2026-02-28
**Author:** Deadlock
**Status:** Draft
**Project:** bmad-ralph

**Related:** See Architecture doc (test-design-architecture.md) for testability concerns and architectural blockers.

---

## Executive Summary

**Scope:** System-level test design for bmad-ralph — Rust CLI tool with daemon, pipeline state machine, parallel workers, and self-healing.

**Risk Summary:**

- Total Risks: 10 (4 high-priority >= 6, 4 medium, 2 low)
- Critical Categories: TECH (8/10 risks) — architecture and process management dominate

**Coverage Summary:**

- P0 tests: ~10 (daemon lifecycle, state machine, worker isolation, self-healing core)
- P1 tests: ~10 (pipeline sequencing, parallel execution, IPC, diagnostics)
- P2 tests: ~10 (performance, config edge cases, shell integration, log rotation)
- P3 tests: ~6 (soak test, concurrent queries, edge cases, TUI)
- **Total**: ~36 tests (~1-2 weeks with 1 developer)

---

## Not in Scope

| Item | Reasoning | Mitigation |
|------|-----------|------------|
| **BMAD planning workflows** | BMAD is a separate submodule with its own testing | BMAD tested independently; Ralph only consumes output artifacts |
| **Claude Code CLI internals** | External dependency, not under project control | Mock via `WorkerProcess` trait; real behavior validated manually |
| **Ratatui TUI rendering** | Post-MVP feature (`ralph watch`), visual validation | Manual testing when TUI is implemented |
| **Multi-LLM worker support** | PRD Phase 3 — deferred | N/A for MVP |
| **Plugin system** | PRD Phase 2 — deferred | N/A for MVP |

---

## Dependencies & Test Blockers

### Development Dependencies (Pre-Implementation)

**Source:** See Architecture doc "Quick Guide" for detailed mitigation plans

1. **`WorkerProcess` trait (R-004)** — Dev — Epic 1
   - Mock process abstraction for Claude Code sessions
   - Without this, integration tests cannot run in CI

2. **State machine implementation** — Dev — Epic 3
   - Pipeline state machine must exist before transition tests
   - Blocking for P0-001 through P0-003

### Test Infrastructure Setup

1. **Temp git repo fixtures** — Dev/QA
   - Integration tests need temporary git repos with initial commits for worktree testing
   - Use `tempdir` crate + `git init` in test setup

2. **SQLite test helpers**
   - In-memory SQLite databases for unit tests
   - File-based SQLite with cleanup for integration tests

3. **Mock process factory**
   - Configurable mock implementing `WorkerProcess` trait
   - Supports: success, failure, hang (timeout), crash, malformed output scenarios

**Test setup pattern (Rust):**

```rust
use assert_cmd::Command;
use predicates::prelude::*;
use tempfile::TempDir;

#[test]
fn ralph_status_shows_idle_when_no_daemon() {
    let tmp = TempDir::new().unwrap();
    Command::cargo_bin("ralph")
        .unwrap()
        .arg("status")
        .current_dir(tmp.path())
        .assert()
        .failure()
        .stderr(predicate::str::contains("daemon is not running"));
}
```

---

## Risk Assessment

**Full risk details in Architecture doc. Summary for test planning:**

### High-Priority Risks (Score >= 6)

| Risk ID | Category | Description | Score | QA Test Coverage |
|---------|----------|-------------|-------|-----------------|
| **R-001** | TECH | Daemon resource leaks over 72h | **6** | Soak test: 1000+ rapid story cycles, assert memory/handle bounds |
| **R-002** | TECH | Claude Code process unpredictability | **6** | Mock process tests: hang, crash, malformed output handling |
| **R-003** | TECH | State machine deadlock under concurrency | **6** | Exhaustive state transition tests, property-based tests |
| **R-004** | TECH | No CI-testable process abstraction | **6** | Validate `WorkerProcess` trait enables full mock testing |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
|---------|----------|-------------|-------|-----------------|
| R-005 | OPS | Self-healing retry loop non-convergence | **4** | Integration test: verify attempt limits and escalation |
| R-006 | PERF | Memory growth >10% over extended runs | **4** | Performance test: memory profiling over 1000 cycles |
| R-007 | DATA | SQLite WAL corruption on hard crash | **3** | Crash recovery test: kill -9 + restart + verify state |
| R-008-010 | Various | Git worktree cleanup, injection, socket | **1-2** | Monitor; covered by standard integration tests |

---

## Entry Criteria

- [ ] `WorkerProcess` trait implemented with mock (R-004 resolved)
- [ ] State machine crate compiles and has basic transition API
- [ ] SQLite schema defined and migrations run
- [ ] Cargo workspace builds without errors (`cargo build --workspace`)
- [ ] CI pipeline configured for `cargo test`

## Exit Criteria

- [ ] All P0 tests passing (100%)
- [ ] All P1 tests passing or failures triaged (>= 95%)
- [ ] No open high-priority bugs
- [ ] Soak test completes without resource leak (R-001 verified)
- [ ] Mock process tests cover hang/crash/malformed scenarios (R-002 verified)

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = **priority and risk level**, NOT execution timing. See "Execution Strategy" for when tests run.

### P0 (Critical)

**Criteria:** Blocks core functionality + High risk (>= 6) + No workaround

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---------|-------------|------------|-----------|-------|
| **P0-001** | State machine valid transitions (all states) | Unit | R-003 | Exhaustive enum match test |
| **P0-002** | State machine rejects invalid transitions | Unit | R-003 | Every invalid combo returns error |
| **P0-003** | SQLite crash recovery — state persists across restart | Integration | R-001, R-007 | Kill daemon, restart, verify state intact |
| **P0-004** | Worker spawns in isolated git worktree | Integration | R-004 | Verify separate working dirs, no file conflicts |
| **P0-005** | Self-healing Layer 1 — step retry triggers on failure | Integration | — | Mock worker returns failure, verify retry |
| **P0-006** | Graceful shutdown — SIGTERM stops daemon and workers | Integration | FR15 | Send SIGTERM, verify workers killed, state saved |
| **P0-007** | `ralph start` creates daemon process | E2E | FR11 | assert_cmd: process starts, PID file created |
| **P0-008** | `ralph stop` terminates daemon cleanly | E2E | FR12 | assert_cmd: daemon stops, socket removed |
| **P0-009** | `ralph status` returns pipeline state | E2E | FR29 | assert_cmd: output contains story/worker info |
| **P0-010** | Config precedence — CLI flags > project TOML > user TOML | Unit | FR10 | Three-tier resolution correctness |

**Total P0:** ~10 tests

---

### P1 (High)

**Criteria:** Important features + Medium risk (3-4) + Common workflows

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---------|-------------|------------|-----------|-------|
| **P1-001** | Pipeline respects story dependency ordering | Unit | FR17 | DAG-based sequencing |
| **P1-002** | 5 parallel workers execute without interference | Integration | FR20-24 | Mock workers, verify isolation |
| **P1-003** | Self-healing Layer 2 — worker restart after Layer 1 exhausted | Integration | FR26 | Verify escalation from retry to restart |
| **P1-004** | Self-healing Layer 3 — diagnose flow triggers | Integration | FR27 | Verify escalation from restart to diagnose |
| **P1-005** | BMAD artifact parsing — YAML frontmatter + markdown body | Unit | FR5 | serde_yaml_ng deserialization |
| **P1-006** | Story assignment to available workers | Unit | FR19 | Concurrency analysis, dependency constraints |
| **P1-007** | `ralph diagnose` outputs structured report | E2E | FR34-35 | assert_cmd: failure details, healing attempts |
| **P1-008** | Unix socket IPC — request/response roundtrip | Integration | Arch | JSON protocol correctness |
| **P1-009** | Worker health monitoring — detect unhealthy workers | Integration | FR21 | Mock worker that stops responding |
| **P1-010** | Terminal output formatting — color, tables, progress | Unit | FR33 | Render components produce expected strings |

**Total P1:** ~10 tests

---

### P2 (Medium)

**Criteria:** Secondary features + Low risk + Edge cases

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---------|-------------|------------|-----------|-------|
| **P2-001** | Memory stability over 1000 rapid cycles | Performance | R-006 | Assert RSS stays within 10% of baseline |
| **P2-002** | Status query latency <2s with 5 active workers | Performance | NFR | Timed assertion under load |
| **P2-003** | Healing attempt tracking — counts and escalation logs | Unit | FR28 | State model correctness |
| **P2-004** | Config edge cases — missing file, invalid TOML, empty values | Unit | FR8 | Error handling paths |
| **P2-005** | `ralph init` creates project structure | E2E | FR7 | assert_cmd: config file created |
| **P2-006** | Shell completions generate for zsh and bash | E2E | FR38-39 | Clap generates valid completion scripts |
| **P2-007** | Exit codes — 0 on success, non-zero on failure | E2E | FR40 | All commands return correct codes |
| **P2-008** | Worker stdout/stderr capture and logging | Integration | Arch | Output appears in daemon logs |
| **P2-009** | Daily log rotation — new file created after midnight | Integration | Arch | tracing-appender behavior |
| **P2-010** | Story re-ingestion — corrected story re-enters pipeline | Integration | FR37 | State transitions back to queued |

**Total P2:** ~10 tests

---

### P3 (Low)

**Criteria:** Nice-to-have + Exploratory + Benchmarks

| Test ID | Requirement | Test Level | Notes |
|---------|-------------|------------|-------|
| **P3-001** | 72-hour soak test — continuous operation | Performance | Manual pre-release; automated accelerated version |
| **P3-002** | Concurrent status queries — multiple CLI clients | Integration | Verify socket handles multiple connections |
| **P3-003** | Edge: `ralph start` when daemon already running | E2E | Should return error, not crash |
| **P3-004** | Edge: `ralph status`/`stop` when no daemon running | E2E | Should return clear error message |
| **P3-005** | Ratatui TUI dashboard rendering | Manual | Post-MVP visual validation |
| **P3-006** | Large sprint plan — 50+ stories processing | Performance | Pipeline handles scale without degradation |

**Total P3:** ~6 tests

---

## Execution Strategy

**Philosophy:** Run everything in PRs via `cargo test` unless it requires extended runtime or special infrastructure. Rust compilation + test parallelism keeps total PR test time under 5 minutes.

### Every PR: `cargo test` (~3-5 min)

**All functional tests** (P0, P1, P2, P3 functional):

- Unit tests across all 5 crates (`#[cfg(test)]`)
- Integration tests (`tests/` directory)
- E2E tests (`assert_cmd` binary tests)
- Cargo runs tests in parallel by default

**Why run in PRs:** Rust test suite is fast; no external infrastructure needed with mock process abstraction.

### Nightly: Performance & Stability (~30-60 min)

**Performance and extended tests:**

- P2-001: Memory stability over 1000 cycles
- P2-002: Status query latency under load
- P3-006: Large sprint plan processing
- Extended soak (accelerated — 1000 rapid cycles in ~30 min)

**Why defer to nightly:** Longer runtime, resource-intensive profiling.

### Weekly/Pre-Release: Soak & Chaos (~hours)

**Long-running validation:**

- P3-001: 72-hour soak test (manual or CI long-running job)
- Crash recovery chaos: random kill -9 during operations

**Why defer to weekly:** Multi-hour runtime, requires dedicated resources.

---

## QA Effort Estimate

| Priority | Count | Effort Range | Notes |
|----------|-------|-------------|-------|
| P0 | ~10 | ~15-25 hours | Complex setup (state machine, crash recovery, process mocking) |
| P1 | ~10 | ~12-20 hours | Standard integration and E2E (parallel workers, IPC, diagnostics) |
| P2 | ~10 | ~8-15 hours | Edge cases, performance baselines, config validation |
| P3 | ~6 | ~3-8 hours | Soak test setup, edge cases, manual TUI |
| **Total** | **~36** | **~38-68 hours** | **~1-2 weeks, 1 developer full-time** |

**Assumptions:**

- Includes test design, implementation, debugging, CI integration
- Excludes ongoing maintenance (~10% effort)
- Assumes `WorkerProcess` trait mock is available (R-004 resolved)
- Solo developer writes both production code and tests

---

## Implementation Planning Handoff

| Work Item | Owner | Dependencies/Notes |
|-----------|-------|-------------------|
| Define `WorkerProcess` trait + mock impl | Dev | Epic 1 prerequisite; blocks all integration tests |
| Temp git repo test fixtures | Dev | Needed for worktree isolation tests |
| SQLite test helpers (in-memory + cleanup) | Dev | Needed for state persistence tests |
| Mock process factory (success/fail/hang/crash) | Dev | Needed once trait is defined |
| Soak test harness | Dev | Pre-release; accelerated cycle approach |

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope |
|-------------------|--------|-----------------|
| **BMAD submodule** | Input artifacts format | Verify YAML frontmatter parsing still works after BMAD upgrades |
| **Claude Code CLI** | Worker execution | Manual validation that real Claude Code sessions work end-to-end |
| **Git** | Worktree lifecycle | Verify worktree create/destroy works with current git version |
| **SQLite (rusqlite)** | State persistence | Verify WAL mode, schema migrations work after crate upgrades |

**Regression strategy:**

- Run full `cargo test` suite before any dependency upgrade merge
- Pin BMAD submodule version to prevent unexpected format changes

---

## Appendix A: Code Examples & Tagging

**Rust test tagging via module organization and `#[ignore]`:**

```rust
// tests/e2e/cli_start.rs
use assert_cmd::Command;
use predicates::prelude::*;
use tempfile::TempDir;

/// P0: ralph start creates daemon process
#[test]
fn ralph_start_creates_daemon() {
    let tmp = TempDir::new().unwrap();
    // Initialize project
    Command::cargo_bin("ralph").unwrap()
        .arg("init")
        .current_dir(tmp.path())
        .assert()
        .success();

    // Start daemon (background)
    let mut child = std::process::Command::new(
        assert_cmd::cargo::cargo_bin("ralph")
    )
        .arg("start")
        .current_dir(tmp.path())
        .spawn()
        .unwrap();

    // Verify PID file created
    std::thread::sleep(std::time::Duration::from_secs(2));
    assert!(tmp.path().join(".ralph/ralph.pid").exists());

    // Cleanup
    child.kill().unwrap();
}

/// P2: Performance test — marked #[ignore] for nightly runs
#[test]
#[ignore]
fn memory_stability_over_1000_cycles() {
    // Run 1000 rapid story cycles
    // Assert RSS stays within 10% of baseline
}
```

**Run specific priority levels:**

```bash
# Run all tests (PR)
cargo test --workspace

# Run only non-ignored tests (fast, PR)
cargo test --workspace

# Run ignored performance tests (nightly)
cargo test --workspace -- --ignored

# Run specific test module
cargo test --package ralph-pipeline state_machine

# Run E2E tests only
cargo test --package ralph --test '*'
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` — Risk scoring methodology (P x I, 1-9 scale)
- **Test Levels Framework**: `test-levels-framework.md` — Unit vs Integration vs E2E selection
- **Test Quality**: `test-quality.md` — Definition of Done (deterministic, isolated, <300 lines)
- **ADR Quality Readiness Checklist**: `adr-quality-readiness-checklist.md` — 8-category NFR framework

---

**Generated by:** BMad TEA Agent — Test Architect Module
**Workflow:** `_bmad/tea/testarch/test-design`
**Version:** 5.0 (BMad v6)
