# BMAD Workflow Execution Sequence

This document interleaves **BMM** (BMAD Method Manager) and **TEA** (Test Engineering Agent) slash commands in the correct execution order for the bmad-ralph project.

> **Important**: Each slash command should be run in a **fresh Claude Code context window** to avoid context pollution between steps.

---

## Phase 3: Solutioning (One-Time)

These steps are run once during project setup. Current status for bmad-ralph:

| # | Code | Slash Command | Required | Agent | Status |
|---|------|--------------|----------|-------|--------|
| 1 | CA | `/bmad-bmm-create-architecture` | REQUIRED | Winston (Architect) | [x] Done |
| 2 | TD | `/bmad-tea-testarch-test-design` | optional | Murat (TEA) | [x] Done |
| 3 | CE | `/bmad-bmm-create-epics-and-stories` | REQUIRED | John (SM) | [x] Done |
| 4 | TF | `/bmad-tea-testarch-framework` | optional | Murat (TEA) | [x] Done |
| 5 | IR | `/bmad-bmm-check-implementation-readiness` | REQUIRED | Winston (Architect) | [x] Done |
| 6 | CI | `/bmad-tea-testarch-ci` | optional | Murat (TEA) | [ ] Pending |

---

## Phase 4: Sprint Setup (Per-Sprint)

Run once at the start of each sprint:

| # | Code | Slash Command | Required | Agent | Status |
|---|------|--------------|----------|-------|--------|
| 1 | SP | `/bmad-bmm-sprint-planning` | REQUIRED | Bob (SM) | [x] Done |

---

## Story Cycle (Repeat Per Story)

This is the core loop. **All steps are REQUIRED.** Repeat for every story in the sprint.

### Step 1 — CS: Create Story

```
/bmad-bmm-create-story
```

Create the story spec file with full context for implementation.

### Step 2 — VS: Validate Story

```
/bmad-bmm-create-story
```

Run the **same command** but select **Validate Mode** when prompted. There is no separate validate command — the create-story workflow includes validation as a mode option.

### Step 3 — AT: ATDD Acceptance Tests

```
/bmad-tea-testarch-atdd
```

Generate failing acceptance tests following TDD red phase. This must run **before** dev-story so the developer has test targets to satisfy.

### Step 4 — DS: Dev Story

```
/bmad-bmm-dev-story
```

Implement the story code to make all tests pass (TDD green phase). Run `make test-all` to confirm.

### Step 5 — QA: QA Automation

```
/bmad-bmm-qa-generate-e2e-tests
```

Generate additional automated tests for edge cases and integration scenarios beyond ATDD coverage.

### Step 6 — CR: Code Review

```
/bmad-bmm-code-review
```

Adversarial code review. If issues are found:

> **Inner Loop**: CR finds issues → go back to **Step 4 (DS)** to fix → skip Step 5 (QA) → return to **Step 6 (CR)**. Repeat until CR passes clean.

### Step 7 — RV: Test Review

```
/bmad-tea-testarch-test-review
```

Quality audit of all tests. Produces a 0-100 quality score.

### Step 8 — NR: NFR Assessment

```
/bmad-tea-testarch-nfr
```

Evaluate non-functional requirements: performance, security, reliability.

### Step 9 — TR: Traceability & Gate

```
/bmad-tea-testarch-trace
```

Generate coverage traceability matrix and make the quality gate pass/fail decision. This is the final gate before a story is considered **Done**.

---

## Epic Boundary (Optional)

Run at the end of each epic:

| Code | Slash Command | Required | Agent |
|------|--------------|----------|-------|
| ER | `/bmad-bmm-retrospective` | optional | Team |

---

## Anytime Workflows

These can be run at any point during development:

| Code | Slash Command | Purpose |
|------|--------------|---------|
| SS | `/bmad-bmm-sprint-status` | Summarize sprint status and surface risks |
| CC | `/bmad-bmm-correct-course` | Manage significant changes during sprint execution |
| QS | `/bmad-bmm-quick-spec` | Create a quick tech spec for small changes |
| QD | `/bmad-bmm-quick-dev` | Implement a quick tech spec |

---

## Determining Next Step

When deciding the next workflow step, **always cross-reference two sources**:

1. **Sprint status** (`_bmad-output/implementation-artifacts/sprint-status.yaml`) — check which stories are `done`, `in-progress`, or `backlog`.
2. **Quality step artifacts** — verify that each completed story has the expected output files from Steps 5–9. A story marked `done` in sprint status is not truly done unless all quality gate artifacts exist.

**Expected artifacts per story** (in `_bmad-output/test-artifacts/` and `_bmad-output/implementation-artifacts/`):

| Step | Expected Artifact Pattern | Example |
|------|--------------------------|---------|
| 3. AT | `atdd-checklist-{story}.md` | `atdd-checklist-1-1.md` |
| 5. QA | QA e2e test report/files for the story | |
| 6. CR | Code review report for the story | |
| 7. RV | Test review quality score for the story | |
| 8. NR | NFR assessment report for the story | |
| 9. TR | Traceability matrix / gate decision for the story | |

**Rule**: If a story is marked `done` in sprint status but is missing any quality artifacts from Steps 5–9, resume the Story Cycle at the first missing step before starting a new story.

---

## Notes

1. **Fresh context**: Always start each slash command in a new Claude Code context window. Carrying over prior context can cause confusion and hallucination.
2. **Validate mode**: Step 2 (VS) uses the same `/bmad-bmm-create-story` command as Step 1 (CS). When the workflow prompts you, select "Validate" mode instead of "Create" mode.
3. **ATDD before dev**: Step 3 (AT) must complete before Step 4 (DS). The failing tests from ATDD define the acceptance criteria the developer must satisfy.
4. **CR inner loop**: When code review finds issues, only the dev-story step needs to re-run. Skip QA on rework iterations — QA tests are only generated once per story.
5. **Gate decision**: Step 9 (TR) is the final quality gate. A failing gate means the story needs rework before it can be marked Done.
6. **Story artifacts**: Each story produces files in `_bmad-output/implementation-artifacts/` and `_bmad-output/test-artifacts/`.
