---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
inputDocuments:
  - "product-brief-bmad-ralph-2026-02-27.md"
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 0
classification:
  projectType: cli_tool
  domain: developer_tooling_general
  complexity: medium
  projectContext: greenfield
workflowType: 'prd'
---

# Product Requirements Document - bmad-ralph

**Author:** Deadlock
**Date:** 2026-02-27

## Executive Summary

bmad-ralph is a self-contained CLI tool that enables independent developers and small teams to shift from human-in-the-loop to human-on-the-loop software delivery. It combines BMAD-METHOD's structured collaborative planning with Ralph's autonomous parallel execution pipeline — users invest focused hours in high-quality planning, then agents execute stories 24/7 without human initiation. The result: developers wake up to implemented stories, passing tests, and PRs ready for review.

The tool targets solo full-stack developers who want their projects to progress while they sleep, and small team tech leads who want to multiply output without multiplying headcount. It is a greenfield open-source project built to solve the creator's own need.

### What Makes This Special

The differentiation is not incremental — it is categorical. Existing AI coding tools make developers faster at individual tasks but remain firmly human-in-the-loop: work stops when people stop. bmad-ralph delivers the "wake up moment" — the experience of returning to find meaningful, autonomous progress completed overnight. This is possible because planning quality directly determines execution reliability: BMAD's rigorous planning artifacts give Ralph's cattle-model workers the context needed for sustained autonomous delivery with multi-layer self-healing.

The core insight is proven, not theoretical. Ralph has already demonstrated viable story-level autonomous execution. bmad-ralph packages this capability into a generalized, project-agnostic CLI tool that any developer can pick up and apply immediately.

## Project Classification

- **Project Type:** CLI Tool — standalone command-line interface with daemon process, pipeline orchestration, and worker management
- **Domain:** Developer Tooling — SDLC automation framework, no industry-specific compliance requirements
- **Complexity:** Medium — involves daemon lifecycle, state machine orchestration, parallel worker management, and multi-layer self-healing, but operates within standard software engineering constraints
- **Project Context:** Greenfield — new product built from scratch

## Success Criteria

### User Success

- **AFK Confidence:** Users trust the system enough to start Ralph and walk away for the night. The trust threshold is sustained stable operation over multiple days — not a single successful run, but proven reliability over time.
- **Wake Up Moment:** Users return to find stories implemented, tests passing, and PRs ready for review. This is the core user success experience.
- **Final Story Success Rate:** >99% of stories reach successful completion through Ralph's self-healing pipeline. First-attempt success rate is intentionally uncontrolled — Ralph's architecture treats retries and self-healing as core mechanisms, not fallbacks.

### Business Success

- **Framework Reliability:** Ralph daemon runs continuously for days without crashes or degraded performance.
- **Generalizability:** Successfully applied across multiple unrelated projects without project-specific customization.
- **Self-Contained Operation:** Zero external dependency failures — the framework operates independently out of the box.
- **Time-to-Productive:** Minutes from CLI install to first Ralph execution on a new project.

### Technical Success

- **Pipeline Stability:** Daemon sustains continuous operation for days without intervention.
- **State Machine Integrity:** Pipeline state machine correctly orchestrates multi-story sprint execution with proper sequencing and parallelization.
- **Self-Healing Effectiveness:** All three healing layers (step retry, worker restart, diagnose flow) function correctly and contribute to the >99% final success rate.
- **Cattle Worker Model:** Workers are truly stateless and replaceable — any worker can be killed and restarted without side effects.

### Measurable Outcomes

| Metric | Target | Notes |
|--------|--------|-------|
| Story final success rate | >99% | Including all self-healing cycles |
| Continuous autonomous runtime | Days | Unattended execution duration |
| Pipeline stability | Days without crash | Longest uninterrupted session |
| First-attempt success rate | Tracked only | Intentionally no target — retries are by design |
| Time-to-productive | Minutes | Install to first execution |

## Product Scope

### MVP Strategy

**MVP Approach:** Problem-solving MVP — prove that autonomous story-level sprint execution is reliable on real projects. The creator is the primary validator; success is measured by sustained personal use, not market adoption.

**Scope Boundary:** MVP includes both the BMAD planning phase (as submodule integration) and the Ralph delivery pipeline. The full SDLC loop — plan, execute, review, feedback — must work end-to-end.

**Resource:** Solo developer building for personal use, leveraging BMAD for planning the tool itself.

### MVP Feature Set (Phase 1)

**All Five Core User Journeys Supported:**
1. Solo developer success path (plan → start → wake up to results)
2. Error recovery path (diagnose → report → fix → re-feed)
3. Live monitoring (connect to daemon, query state)
4. Team sprint execution (multi-user planning input → autonomous delivery)
5. First-time onboarding (install → setup → first run)

**Must-Have Capabilities:**
- BMAD planning phase integration (submodule) for PRD, architecture, epics, stories
- Ralph daemon (long-running, polling-based task detection)
- Pipeline state machine driving story execution with dependency awareness
- Parallel worker execution (cattle-model Claude Code sessions)
- Multi-layer self-healing (step retry → worker restart → diagnose flow)
- CLI commands: `start`, `stop`, `status`, `diagnose`, `init`/`setup`
- TOML configuration with CLI flag overrides
- Shell completion (zsh, bash)
- Human-readable terminal output

**MVP Validation Criteria:** Continuous stable operation for multiple days on a real project, executing a full sprint of stories autonomously.

### Phase 2: Growth (Post-MVP)

- Git hook integration replacing polling
- Plugin system for external tool integration (Jira, Slack, GitHub Actions)
- Advanced diagnostics — failure pattern learning
- JSON/structured output for scripting
- Multi-LLM worker support

### Phase 3: Expansion (Future)

- Large team features — RBAC, multi-repo orchestration, audit trails
- Community marketplace for workflow templates and pipeline configs
- Self-improving execution based on historical failure data

### Risk Mitigation

**Technical Risks:**
- **Daemon stability** is the highest-risk item — long-running process must not crash or degrade over days. Mitigation: robust signal handling, resource cleanup, watchdog patterns.
- **Worker coordination** — parallel cattle workers must not interfere with each other. Mitigation: strict isolation per worker, no shared mutable state.

**Resource Risks:**
- Solo developer project — if time is limited, priority order is: daemon stability > state machine > self-healing > CLI polish.
- BMAD submodule is an external dependency — changes upstream could affect integration. Mitigation: pin submodule versions.

## User Journeys

### Journey 1: Alex's Nightly Sprint — Solo Developer Success Path

Alex is a full-stack developer with a side project he's passionate about. During the day he's at his full-time job; his side project only moves when he does. Tonight, he sits down after dinner and opens his terminal.

**Opening Scene:** Alex has a backlog of features he wants to build. He spends 90 minutes collaborating with BMAD — refining the PRD, breaking down epics into stories, ensuring each story has clear acceptance criteria. The planning feels like pair-programming with a senior PM. He's thorough because he knows: planning quality determines execution quality.

**Rising Action:** Alex runs `ralph start` and watches the daemon pick up the sprint plan. He sees workers spawning, stories being assigned. He checks status once — `ralph status` — sees 3 workers running in parallel. He closes his laptop and goes to sleep.

**Climax:** Morning. Coffee in hand, Alex runs `ralph status`. 8 of 10 stories completed. Tests passing. PRs ready for review. Two stories hit issues — one was retried and succeeded on the second attempt, another went through the full diagnose flow and self-healed. The overnight output is real, reviewable, working code.

**Resolution:** Alex spends his morning commute reviewing PRs on his phone. By lunch, he's merged everything. His side project just got 3 days of solo development done overnight. He plans the next sprint that evening.

### Journey 2: Alex's Morning Surprise — Error Recovery Path

Alex wakes up and runs `ralph status`. 9 stories completed, but story #7 is marked as failed — even after all three self-healing layers exhausted their attempts.

**Opening Scene:** Alex sees the failure status. He doesn't panic — this is expected occasionally. Ralph's design philosophy is >99% final success rate, not 100%.

**Rising Action:** Alex runs Ralph's diagnose command. Ralph generates a detailed diagnostic report: what failed, what self-healing attempts were made, where it got stuck, relevant logs and context. The report is structured and machine-readable.

**Climax:** Alex hands the diagnostic report to Claude Code. Claude Code analyzes the failure, proposes a fix — maybe the story's acceptance criteria were ambiguous, or there was an edge case the planning didn't anticipate. Alex reviews the proposed fix, applies it, and updates the story.

**Resolution:** Alex feeds the corrected story back into Ralph. The story completes on the next run. Alex makes a mental note to be more specific about that type of requirement in future planning sessions. The feedback loop improves planning quality over time.

### Journey 3: Alex Checking In — Live Monitoring Path

It's 11 PM. Alex started Ralph an hour ago and can't resist checking progress before bed.

**Opening Scene:** Alex opens his terminal and runs `ralph status` — the CLI connects to the running daemon and pulls current state.

**Rising Action:** He sees a real-time snapshot: 2 workers active, 3 stories completed, 1 story in retry cycle (layer 1 — step retry), 4 stories queued. Worker health is green. Daemon uptime: 1h 12m.

**Climax:** Everything looks healthy. The retry is on a test that was flaky — Ralph is handling it. No human intervention needed.

**Resolution:** Alex closes the terminal and goes to sleep with confidence. He knows he can check anytime with a single command, but he doesn't need to. That's AFK confidence.

### Journey 4: Sam's Team Sprint — Team Lead Success Path

Sam leads a team of 7. The PM has written requirements, the UI designer has contributed design specs, and Sam has synthesized everything through BMAD's planning workflow.

**Opening Scene:** Sam's team spent the week in planning mode — PM contributed domain expertise through BMAD, designer provided UX specs, Sam drove architecture decisions. The result: a well-structured sprint plan with 15 stories, properly sequenced with dependencies mapped.

**Rising Action:** Sam runs `ralph start` on the team's development environment. Workers spawn and begin executing stories in parallel, respecting dependency ordering. The team shifts from "writing code" to "reviewing output."

**Climax:** Over the next two days, Ralph delivers stories continuously. The team reviews PRs as they arrive — they're now functioning as a review and quality team rather than an implementation team. Their feedback on delivered output gets captured as new stories.

**Resolution:** The sprint that would have taken the team 2 weeks of implementation is delivered in days. The team's time shifted from implementation mechanics to product thinking, design quality, and review rigor. Sam plans the next sprint with confidence.

### Journey 5: First-Time Onboarding — New Developer Setup

A developer discovers bmad-ralph through GitHub. They have an existing project they want to accelerate.

**Opening Scene:** The developer installs the CLI tool. Setup takes minutes — self-contained, zero external dependencies.

**Rising Action:** They run the setup command on their existing project. BMAD guides them through creating their first planning artifacts — product brief, architecture notes, a small sprint plan with 3 stories to start small.

**Climax:** They run `ralph start` for the first time. They watch the daemon start, a worker spawn, and the first story begin execution. It feels like watching something magical — their project is building itself.

**Resolution:** The first 3 stories complete successfully. The developer is hooked. They start planning a larger sprint, trusting the system with more ambitious work. Time-to-productive: minutes from install to first execution.

### Journey Requirements Summary

| Journey | Key Capabilities Revealed |
|---------|--------------------------|
| Alex Success Path | Sprint plan ingestion, parallel worker execution, status reporting, PR-ready output |
| Alex Error Recovery | Diagnose command, structured diagnostic reports, story re-ingestion |
| Alex Monitoring | CLI daemon connection, real-time status snapshot, worker health reporting |
| Sam Team Sprint | Dependency-aware scheduling, sustained multi-day execution, continuous PR delivery |
| First-Time Onboarding | CLI install, project setup, BMAD planning guidance, first-run experience |

## CLI Tool Specific Requirements

### Command Structure

Interactive-first CLI with long-running daemon component. Developer-at-terminal is the primary interaction model.

- **`ralph start`** — Start the daemon, begin processing sprint plan
- **`ralph stop`** — Gracefully stop the daemon and all workers
- **`ralph status`** — Connect to running daemon, display real-time pipeline state (workers, stories, health)
- **`ralph diagnose`** — Generate diagnostic report for failed stories
- **`ralph init`** / **`ralph setup`** — Initialize bmad-ralph on a new project

Commands follow standard CLI conventions: `ralph <command> [flags]`

### Output & Display

- Human-readable terminal output optimized for developer consumption
- Status output scannable at a glance — story progress, worker health, retry state
- Color and formatting where terminal supports it
- No JSON/machine-readable output for MVP (deferred to Phase 2)

### Configuration

- **Primary:** TOML configuration file (`ralph.toml` or similar) for project-level and user-level settings
- **Override:** CLI flags override TOML values for one-off adjustments
- **Scope:** Daemon behavior (concurrency, retry limits), worker settings, project paths, pipeline preferences
- **Precedence:** CLI flags > project TOML > user-level TOML defaults

### Shell Integration

- Shell completion required for MVP (zsh and bash)
- Completions for commands, subcommands, and common flags
- Standard exit codes (0 success, non-zero failure)
- Scripting support deferred to post-MVP

### Implementation Considerations

- Daemon communication: CLI commands connect to running daemon process to query state
- Process management: Daemon handles signals gracefully (SIGTERM, SIGINT)
- Terminal UX: Status display works in standard terminal sizes, no TUI framework for MVP
- TOML parsing: Use established library, no custom parser

## Functional Requirements

### Planning Integration

- FR1: Developer can initiate BMAD planning workflows to create PRD, architecture, and design artifacts for a project
- FR2: Developer can use BMAD to break down requirements into epics and user stories with acceptance criteria
- FR3: Developer can generate sprint plans with story sequencing and dependency mapping from BMAD planning artifacts
- FR4: Team members (PM, designer) can contribute domain expertise and design specs through BMAD planning workflows
- FR5: System can read BMAD-produced sprint plans and stories as input for the delivery pipeline

### Project Setup & Configuration

- FR6: Developer can install bmad-ralph as a self-contained CLI tool with zero external dependencies
- FR7: Developer can initialize bmad-ralph on a new or existing project via setup command
- FR8: Developer can configure daemon behavior, worker settings, and project paths via TOML configuration file
- FR9: Developer can override TOML configuration values with CLI flags for one-off adjustments
- FR10: System can resolve configuration from multiple sources with precedence: CLI flags > project TOML > user-level TOML defaults

### Daemon Management

- FR11: Developer can start the Ralph daemon to begin processing a sprint plan
- FR12: Developer can stop the Ralph daemon with clean shutdown — terminating all active workers, saving pipeline state, and releasing resources
- FR13: Daemon can run continuously for 72+ hours without crashes, memory growth exceeding 10% of baseline, or increased status query response time
- FR14: Daemon can detect new sprint plans and stories automatically for pipeline ingestion
- FR15: Daemon can handle system signals (SIGTERM, SIGINT) gracefully for clean shutdown

### Pipeline Orchestration

- FR16: System can drive the SDLC workflow from sprint plan ingestion through story execution to completion
- FR17: System can determine story sequencing and parallelization opportunities based on dependency mapping
- FR18: System can track state transitions and execution progress persistently across daemon restarts
- FR19: System can assign stories to available workers based on concurrency analysis and dependency constraints

### Worker Management

- FR20: System can spawn configurable concurrent Claude Code session workers (default up to 5) for parallel story execution
- FR21: System can monitor worker health and execution status in real-time
- FR22: System can kill and restart individual workers without affecting other running workers
- FR23: System can replace any worker without side effects due to stateless cattle architecture
- FR24: Each worker can execute an assigned story independently in isolation from other workers

### Self-Healing Pipeline

- FR25: System can retry failed pipeline steps automatically (Layer 1 — step retry)
- FR26: System can kill and restart failed workers with fresh state (Layer 2 — worker restart)
- FR27: System can trigger a dedicated diagnose flow when retries cannot resolve an issue (Layer 3 — diagnose)
- FR28: System can track retry attempts and escalate through healing layers progressively

### Status & Monitoring

- FR29: Developer can query the running daemon for real-time pipeline state via CLI command
- FR30: Developer can view story progress (completed, in-progress, queued, failed) at a glance
- FR31: Developer can view worker health status and active worker count
- FR32: Developer can view current retry/healing state for stories in recovery
- FR33: Developer can view status output with color-coded categories (success/warning/error) and structured formatting for terminal display

### Diagnostics & Error Recovery

- FR34: Developer can generate a diagnostic report for failed stories via CLI command
- FR35: Developer can view failure details, self-healing attempts made, and relevant logs in the diagnostic report
- FR36: Developer can export diagnostic report in a structured format suitable for automated analysis and fix proposal
- FR37: Developer can re-feed corrected stories back into the Ralph pipeline for re-execution

### Shell Integration

- FR38: Developer can use shell completion for commands, subcommands, and flags
- FR39: Developer can use shell completion in both zsh and bash shells
- FR40: System can return standard exit codes (0 success, non-zero failure) for all CLI commands

## Non-Functional Requirements

### Reliability

- Daemon must sustain continuous operation for 72+ hours without crashes or degraded behavior as measured by process uptime and status query response consistency
- Pipeline state must be persisted durably — if daemon crashes, it can recover to pre-crash state on restart without losing progress
- Worker failures must be isolated — a single worker crash must not affect daemon stability or other running workers
- State machine transitions must be atomic — no partial state updates that could leave the pipeline in an inconsistent state

### Performance

- Daemon must consume <100MB RSS memory and <1% CPU during idle periods, with no memory growth exceeding 10% of baseline over 72-hour runs
- Resource consumption must remain within 10% of baseline measurements over 72-hour runs — no unbounded growth in memory, file handles, or disk usage
- Status queries must return within 2 seconds while daemon is under load with up to 5 active workers
- No specific latency targets — acceptable performance will be assessed empirically by the developer

### Integration

- System must spawn and manage Claude Code CLI sessions as worker processes reliably
- System must read BMAD planning artifacts (markdown files with frontmatter) as pipeline input without format coupling
- System must interact with git for branch management and PR creation through workers
- Upstream BMAD changes must not break pipeline integration — system must control dependency versioning

### Concurrency

- System must support parallel worker execution with no hardcoded upper limit
- Typical workload is up to 5 concurrent workers — system must operate reliably at this level
- Workers must operate in full isolation — no shared mutable state, no file conflicts, no git branch collisions between workers
