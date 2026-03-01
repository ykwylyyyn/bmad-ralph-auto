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

# Test Design for Architecture: bmad-ralph

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by the development team. Serves as a contract between QA and Engineering on what must be addressed before test development begins.

**Date:** 2026-02-28
**Author:** Deadlock
**Status:** Architecture Review Pending
**Project:** bmad-ralph
**PRD Reference:** `_bmad-output/planning-artifacts/prd.md`
**Architecture Reference:** `_bmad-output/planning-artifacts/architecture.md`

---

## Executive Summary

**Scope:** System-level test design for bmad-ralph — a Rust CLI tool with daemon process, pipeline state machine, parallel worker management, and multi-layer self-healing.

**Architecture:**

- **Stack:** Rust + Tokio 1.49, Cargo workspace (5 crates)
- **State:** SQLite + WAL mode for pipeline persistence
- **IPC:** Unix Domain Socket (JSON protocol)
- **Workers:** Claude Code CLI sessions in git worktrees (cattle model)
- **Healing:** Three-layer progressive escalation (step retry → worker restart → diagnose)

**Risk Summary:**

- **Total risks**: 10 (4 high-priority score >= 6, 4 medium, 2 low)
- **Test effort**: ~36 tests (~1-2 weeks for 1 developer)

---

## Quick Guide

### BLOCKERS - Must Address Pre-Implementation

1. **R-004: Worker process mock strategy** — Define `WorkerProcess` trait abstraction so Claude Code sessions can be stubbed in CI tests (recommended owner: Dev, Epic 1)
2. **TC-1: No testable process interface** — Without trait-based abstraction, integration tests cannot run without real Claude Code CLI (recommended owner: Dev, Epic 1)

**What we need:** Complete these 2 items in Epic 1 (foundation crate) or integration/E2E test development is blocked.

---

### HIGH PRIORITY - Validate During Implementation

1. **R-001: Daemon resource leak prevention** — Enforce JoinHandle tracking and resource cleanup patterns across all async tasks (implementation phase)
2. **R-003: State machine deadlock prevention** — Implement explicit state transition guards with timeout watchdog (Epic 3)
3. **R-002: Claude Code process resilience** — Define timeout and output parsing strategies for external process interaction (Epic 4)

**What we need:** Review recommendations and approve approach during implementation.

---

### INFO ONLY - No Decisions Needed

1. **Test framework**: `#[cfg(test)]` unit + `tests/` integration + `assert_cmd` E2E (standard Rust)
2. **Execution**: `cargo test` in PR (<5 min), performance/soak tests nightly/weekly
3. **Coverage**: ~36 test scenarios prioritized P0-P3 with risk-based classification
4. **State persistence**: SQLite WAL provides queryable, crash-safe state for test assertions

---

## Risk Assessment

**Total risks identified**: 10 (4 high-priority >= 6, 4 medium, 2 low)

### High-Priority Risks (Score >= 6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Prob | Impact | Score | Mitigation | Owner | Timeline |
|---------|----------|-------------|------|--------|-------|------------|-------|----------|
| **R-001** | **TECH** | Daemon resource leaks (async task leaks, file handles, SQLite connections) degrade 72h stability | 2 | 3 | **6** | JoinHandle enforcement, resource cleanup audit, soak test | Dev | Pre-release |
| **R-002** | **TECH** | Claude Code process hangs/crashes/unexpected output breaks worker management | 2 | 3 | **6** | Per-operation timeout, resilient output parsing, kill escalation | Dev | Epic 4 |
| **R-003** | **TECH** | State machine deadlock/livelock under concurrent worker completion events | 2 | 3 | **6** | Explicit state guards, timeout watchdog, exhaustive transition tests | Dev | Epic 3 |
| **R-004** | **TECH** | No mock strategy for Claude Code process — CI tests cannot verify worker lifecycle | 3 | 2 | **6** | Trait-based `WorkerProcess` abstraction with mock impl | Dev | Epic 1 |

### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Prob | Impact | Score | Mitigation | Owner |
|---------|----------|-------------|------|--------|-------|------------|-------|
| R-005 | OPS | Self-healing retry loop non-convergence | 2 | 2 | **4** | Per-layer attempt limits, progressive backoff | Dev |
| R-006 | PERF | Memory growth >10% baseline over 72h from async/channel leaks | 2 | 2 | **4** | Channel capacity bounds, periodic profiling | Dev |
| R-007 | DATA | SQLite WAL corruption on hard crash during write | 1 | 3 | **3** | WAL mode + atomic transactions (already chosen) | Dev |
| R-008 | TECH | Git worktree cleanup failure leaving disk residue | 1 | 2 | **2** | Shutdown cleanup, periodic garbage collection | Dev |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Prob | Impact | Score | Action |
|---------|----------|-------------|------|--------|-------|--------|
| R-009 | SEC | Story markdown content passed unsanitized to shell | 1 | 2 | **2** | Monitor — architecture uses file-based passing |
| R-010 | TECH | Unix socket congestion under concurrent status queries | 1 | 1 | **1** | Monitor — unlikely at 5-worker scale |

---

## Testability Concerns and Architectural Gaps

### ACTIONABLE CONCERNS - Must Address

#### 1. Blockers to Fast Feedback

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
|---------|--------|-------------------------------|-------|----------|
| **No process abstraction layer** | Cannot test worker lifecycle without real Claude Code CLI | `WorkerProcess` trait in ralph-worker with mock implementation | Dev | Epic 1 |

#### 2. Architectural Improvements Needed

1. **Process abstraction for testability**
   - **Current problem**: `ralph-worker` directly spawns `tokio::process::Command` for Claude Code — no seam for test injection
   - **Required change**: Extract `WorkerProcess` trait; production impl uses real process, test impl returns controlled responses
   - **Impact if not fixed**: Integration and E2E tests require real Claude Code CLI, making CI testing impractical
   - **Owner**: Dev
   - **Timeline**: Epic 1 (foundation)

2. **Stability test strategy**
   - **Current problem**: 72h continuous operation requirement has no defined validation method
   - **Required change**: Define accelerated aging test — high-frequency story cycles with memory profiling under `cargo test --release`
   - **Impact if not fixed**: 72h NFR unverifiable until actual multi-day manual test
   - **Owner**: Dev
   - **Timeline**: Pre-release

---

### Testability Assessment Summary

#### What Works Well

- SQLite state is directly queryable for assertion verification
- Structured logging via tracing enables log-based assertions in tests
- Clear crate boundaries (5 crates) naturally isolate testable units
- BMAD artifacts as plain files make test fixture creation trivial
- `assert_cmd` is the established Rust pattern for CLI E2E testing
- Serde-derived types enable serialization round-trip testing
- TOML config is easy to fixture and override in tests

#### Accepted Trade-offs

- **No real 72h CI test** — accelerated aging replaces real-duration soak test for CI; real 72h validation done manually pre-release
- **No browser/UI tests** — CLI tool with no web interface; terminal output tested via assert_cmd string matching

---

## Risk Mitigation Plans (High-Priority Risks >= 6)

### R-001: Daemon Resource Leaks (Score: 6)

**Mitigation Strategy:**

1. Enforce `JoinHandle` collection for all `tokio::spawn` calls — zero fire-and-forget tasks
2. Audit all `Arc<Mutex<T>>` and `Arc<RwLock<T>>` usage for potential deadlocks
3. Implement resource accounting in daemon supervisor — track active file handles, child processes, SQLite connections
4. Create soak test that runs 1000+ rapid story cycles and asserts memory/handle counts stay bounded

**Owner:** Dev
**Timeline:** Pre-release
**Status:** Planned
**Verification:** Soak test passes with <10% memory growth over 1000 story cycles

### R-002: Claude Code Process Resilience (Score: 6)

**Mitigation Strategy:**

1. Apply `tokio::time::timeout` to all process I/O operations (stdout read, process wait)
2. Define output parsing that handles truncated, malformed, and empty responses gracefully
3. Implement kill escalation: SIGTERM → wait 10s → SIGKILL for hung processes

**Owner:** Dev
**Timeline:** Epic 4
**Status:** Planned
**Verification:** Integration tests with mock process that simulates hang, crash, and malformed output

### R-003: State Machine Deadlock Prevention (Score: 6)

**Mitigation Strategy:**

1. Define all valid state transitions as an exhaustive enum match — invalid transitions are compile-time errors
2. Add timeout watchdog — if state machine stalls >5 min without progress, force error state
3. Write property-based tests covering all transition permutations

**Owner:** Dev
**Timeline:** Epic 3
**Status:** Planned
**Verification:** Property-based test with 10K random transition sequences produces no deadlocks

### R-004: Worker Process Mock Strategy (Score: 6)

**Mitigation Strategy:**

1. Define `WorkerProcess` trait in ralph-worker crate with `spawn`, `kill`, `status`, `output` methods
2. Production impl wraps `tokio::process::Command` for real Claude Code sessions
3. Test impl returns configurable responses (success, failure, hang, crash)
4. Integration tests use mock impl exclusively

**Owner:** Dev
**Timeline:** Epic 1 (foundation)
**Status:** Planned
**Verification:** Integration tests run in CI without Claude Code installed

---

## Assumptions and Dependencies

### Assumptions

1. Rust toolchain (stable) and cargo are available in CI environment
2. Git is available in CI for worktree-based isolation tests
3. SQLite (bundled via rusqlite) requires no external database setup
4. Claude Code CLI is NOT required in CI — mock process abstraction replaces it

### Dependencies

1. `WorkerProcess` trait defined in Epic 1 — required before worker integration tests
2. State machine implementation in Epic 3 — required before pipeline integration tests
3. Self-healing implementation in Epic 3-4 — required before healing integration tests

### Risks to Plan

- **Risk**: Architecture changes during implementation invalidate test design assumptions
  - **Impact**: Test coverage gaps or wasted test development effort
  - **Contingency**: Re-assess coverage after each epic completion

---

**End of Architecture Document**

**Next Steps for Dev Team:**

1. Review Quick Guide and prioritize R-004 (process mock) as Epic 1 prerequisite
2. Validate mitigation strategies for R-001, R-002, R-003
3. Confirm assumptions about CI environment capabilities

**Next Steps for QA:**

1. Refer to companion QA doc (test-design-qa.md) for test scenarios and coverage plan
2. Begin test infrastructure once `WorkerProcess` trait is available
