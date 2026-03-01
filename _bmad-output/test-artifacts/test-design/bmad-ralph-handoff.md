---
title: 'TEA Test Design → BMAD Handoff Document'
version: '1.0'
workflowType: 'testarch-test-design-handoff'
inputDocuments:
  - '_bmad-output/test-artifacts/test-design-architecture.md'
  - '_bmad-output/test-artifacts/test-design-qa.md'
sourceWorkflow: 'testarch-test-design'
generatedBy: 'TEA Master Test Architect'
generatedAt: '2026-02-28'
projectName: 'bmad-ralph'
---

# TEA → BMAD Integration Handoff

## Purpose

This document bridges TEA's test design outputs with BMAD's epic/story decomposition workflow (`create-epics-and-stories`). It provides structured integration guidance so that quality requirements, risk assessments, and test strategies flow into implementation planning.

## TEA Artifacts Inventory

| Artifact | Path | BMAD Integration Point |
|----------|------|----------------------|
| Architecture Test Design | `_bmad-output/test-artifacts/test-design-architecture.md` | Epic quality requirements, pre-implementation blockers |
| QA Test Design | `_bmad-output/test-artifacts/test-design-qa.md` | Story acceptance criteria, test coverage plan |
| Risk Assessment | (embedded in both docs) | Epic risk classification, story priority |
| Coverage Strategy | (embedded in QA doc) | Story test requirements |

## Epic-Level Integration Guidance

### Risk References

The following high-priority risks (score >= 6) should appear as epic-level quality gates:

| Risk ID | Category | Score | Affected Epic(s) | Quality Gate |
|---------|----------|-------|-------------------|-------------|
| R-001 | TECH | 6 | All (daemon stability) | Soak test passes with <10% memory growth |
| R-002 | TECH | 6 | Epic 4 (Worker Management) | Mock process tests cover hang/crash/malformed |
| R-003 | TECH | 6 | Epic 3 (Pipeline Orchestration) | All state transitions tested, no deadlock in property tests |
| R-004 | TECH | 6 | Epic 1 (Foundation) | `WorkerProcess` trait defined with mock impl |

### Quality Gates

| Epic | Recommended Quality Gate |
|------|------------------------|
| Epic 1 (Foundation) | `WorkerProcess` trait exists, mock impl passes basic spawn/kill/status tests |
| Epic 2 (Config) | Three-tier config precedence unit tests pass (P0-010) |
| Epic 3 (Pipeline) | State machine transition tests pass (P0-001, P0-002), no deadlock under concurrent events |
| Epic 4 (Workers) | Worker isolation in git worktrees verified (P0-004), self-healing Layer 1 triggers (P0-005) |
| Epic 5 (Daemon/CLI) | `ralph start/stop/status` E2E tests pass (P0-007, P0-008, P0-009), graceful shutdown works (P0-006) |

## Story-Level Integration Guidance

### P0/P1 Test Scenarios → Story Acceptance Criteria

The following critical test scenarios MUST be reflected as acceptance criteria in relevant stories:

| Test ID | Scenario | Recommended Story AC |
|---------|----------|---------------------|
| P0-001 | State machine valid transitions | "All valid state transitions pass unit tests" |
| P0-003 | SQLite crash recovery | "Pipeline state persists across daemon restart after kill -9" |
| P0-004 | Worker worktree isolation | "Each worker operates in its own git worktree with no file conflicts" |
| P0-005 | Self-healing Layer 1 | "Failed step triggers automatic retry with attempt tracking" |
| P0-006 | Graceful shutdown | "SIGTERM cleanly stops all workers and saves pipeline state" |
| P0-010 | Config precedence | "CLI flags override project TOML which overrides user TOML defaults" |
| P1-001 | Dependency sequencing | "Stories execute in dependency order; blocked stories wait for dependencies" |
| P1-002 | Parallel worker isolation | "5 concurrent workers run without file or git conflicts" |
| P1-003 | Self-healing escalation L2 | "After Layer 1 retry limit, worker is killed and restarted with fresh state" |
| P1-004 | Self-healing escalation L3 | "After Layer 2 restart limit, diagnose flow triggers and generates report" |

### Testability Requirements for Stories

Stories involving the following components MUST include testability considerations:

- **Worker spawning stories**: Must use `WorkerProcess` trait, not direct `tokio::process::Command`
- **State machine stories**: Must define all transitions as exhaustive enum match
- **SQLite stories**: Must wrap all rusqlite calls in `spawn_blocking`
- **Async stories**: Must capture all `JoinHandle`s — no fire-and-forget

## Risk-to-Story Mapping

| Risk ID | Category | P×I | Recommended Story/Epic | Test Level |
|---------|----------|-----|----------------------|------------|
| R-001 | TECH | 2×3=6 | Epic 5 (Daemon lifecycle) | Integration + Performance |
| R-002 | TECH | 2×3=6 | Epic 4 (Worker management) | Integration (mock process) |
| R-003 | TECH | 2×3=6 | Epic 3 (Pipeline state machine) | Unit + Property-based |
| R-004 | TECH | 3×2=6 | Epic 1 (Foundation — ralph-worker) | Unit + Integration |
| R-005 | OPS | 2×2=4 | Epic 3 (Self-healing) | Integration |
| R-006 | PERF | 2×2=4 | Epic 5 (Daemon stability) | Performance |
| R-007 | DATA | 1×3=3 | Epic 1 (Foundation — ralph-common) | Integration |

## Recommended BMAD → TEA Workflow Sequence

1. **TEA Test Design** (`TD`) → produces this handoff document ✅ (completed)
2. **BMAD Create Epics & Stories** → consumes this handoff, embeds quality requirements
3. **TEA ATDD** (`AT`) → generates acceptance tests per story
4. **BMAD Implementation** → developers implement with test-first guidance
5. **TEA Automate** (`TA`) → generates full test suite
6. **TEA Trace** (`TR`) → validates coverage completeness

## Phase Transition Quality Gates

| From Phase | To Phase | Gate Criteria |
|-----------|----------|--------------|
| Test Design | Epic/Story Creation | All P0 risks have mitigation strategy (R-001 through R-004 addressed) |
| Epic/Story Creation | ATDD | Stories have acceptance criteria derived from P0/P1 test scenarios |
| ATDD | Implementation | Failing acceptance tests exist for all P0 scenarios |
| Implementation | Test Automation | All acceptance tests pass, `cargo test` green |
| Test Automation | Release | Soak test passes, <10% memory growth, all P0/P1 tests pass |
