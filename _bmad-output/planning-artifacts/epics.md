---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "prd.md"
  - "architecture.md"
  - "ux-design-specification.md"
---

# bmad-ralph - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for bmad-ralph, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: Developer can initiate BMAD planning workflows to create PRD, architecture, and design artifacts for a project
- FR2: Developer can use BMAD to break down requirements into epics and user stories with acceptance criteria
- FR3: Developer can generate sprint plans with story sequencing and dependency mapping from BMAD planning artifacts
- FR4: Team members (PM, designer) can contribute domain expertise and design specs through BMAD planning workflows
- FR5: System can read BMAD-produced sprint plans and stories as input for the delivery pipeline
- FR6: Developer can install bmad-ralph as a self-contained CLI tool with zero external dependencies
- FR7: Developer can initialize bmad-ralph on a new or existing project via setup command
- FR8: Developer can configure daemon behavior, worker settings, and project paths via TOML configuration file
- FR9: Developer can override TOML configuration values with CLI flags for one-off adjustments
- FR10: System can resolve configuration from multiple sources with precedence: CLI flags > project TOML > user-level TOML defaults
- FR11: Developer can start the Ralph daemon to begin processing a sprint plan
- FR12: Developer can stop the Ralph daemon with clean shutdown — terminating all active workers, saving pipeline state, and releasing resources
- FR13: Daemon can run continuously for 72+ hours without crashes, memory growth exceeding 10% of baseline, or increased status query response time
- FR14: Daemon can detect new sprint plans and stories automatically for pipeline ingestion
- FR15: Daemon can handle system signals (SIGTERM, SIGINT) gracefully for clean shutdown
- FR16: System can drive the SDLC workflow from sprint plan ingestion through story execution to completion
- FR17: System can determine story sequencing and parallelization opportunities based on dependency mapping
- FR18: System can track state transitions and execution progress persistently across daemon restarts
- FR19: System can assign stories to available workers based on concurrency analysis and dependency constraints
- FR20: System can spawn configurable concurrent Claude Code session workers (default up to 5) for parallel story execution
- FR21: System can monitor worker health and execution status in real-time
- FR22: System can kill and restart individual workers without affecting other running workers
- FR23: System can replace any worker without side effects due to stateless cattle architecture
- FR24: Each worker can execute an assigned story independently in isolation from other workers
- FR25: System can retry failed pipeline steps automatically (Layer 1 — step retry)
- FR26: System can kill and restart failed workers with fresh state (Layer 2 — worker restart)
- FR27: System can trigger a dedicated diagnose flow when retries cannot resolve an issue (Layer 3 — diagnose)
- FR28: System can track retry attempts and escalate through healing layers progressively
- FR29: Developer can query the running daemon for real-time pipeline state via CLI command
- FR30: Developer can view story progress (completed, in-progress, queued, failed) at a glance
- FR31: Developer can view worker health status and active worker count
- FR32: Developer can view current retry/healing state for stories in recovery
- FR33: Developer can view status output with color-coded categories (success/warning/error) and structured formatting for terminal display
- FR34: Developer can generate a diagnostic report for failed stories via CLI command
- FR35: Developer can view failure details, self-healing attempts made, and relevant logs in the diagnostic report
- FR36: Developer can export diagnostic report in a structured format suitable for automated analysis and fix proposal
- FR37: Developer can re-feed corrected stories back into the Ralph pipeline for re-execution
- FR38: Developer can use shell completion for commands, subcommands, and flags
- FR39: Developer can use shell completion in both zsh and bash shells
- FR40: System can return standard exit codes (0 success, non-zero failure) for all CLI commands

### NonFunctional Requirements

- NFR1: Daemon must sustain continuous operation for 72+ hours without crashes or degraded behavior as measured by process uptime and status query response consistency
- NFR2: Pipeline state must be persisted durably — if daemon crashes, it can recover to pre-crash state on restart without losing progress
- NFR3: Worker failures must be isolated — a single worker crash must not affect daemon stability or other running workers
- NFR4: State machine transitions must be atomic — no partial state updates that could leave the pipeline in an inconsistent state
- NFR5: Daemon must consume <100MB RSS memory and <1% CPU during idle periods, with no memory growth exceeding 10% of baseline over 72-hour runs
- NFR6: Resource consumption must remain within 10% of baseline measurements over 72-hour runs — no unbounded growth in memory, file handles, or disk usage
- NFR7: Status queries must return within 2 seconds while daemon is under load with up to 5 active workers
- NFR8: No specific latency targets — acceptable performance will be assessed empirically by the developer
- NFR9: System must spawn and manage Claude Code CLI sessions as worker processes reliably
- NFR10: System must read BMAD planning artifacts (markdown files with frontmatter) as pipeline input without format coupling
- NFR11: System must interact with git for branch management and PR creation through workers
- NFR12: Upstream BMAD changes must not break pipeline integration — system must control dependency versioning
- NFR13: System must support parallel worker execution with no hardcoded upper limit
- NFR14: Typical workload is up to 5 concurrent workers — system must operate reliably at this level
- NFR15: Workers must operate in full isolation — no shared mutable state, no file conflicts, no git branch collisions between workers

### Additional Requirements

**From Architecture:**

- Starter template: Custom `cargo init` + curated Rust crate stack — Rust language, Tokio async runtime, standalone binary distribution. This defines Epic 1 Story 1 (project scaffold)
- State persistence: SQLite + WAL mode via `rusqlite` 0.38.x — atomic transactions, crash recovery, concurrent read access
- Daemon-CLI IPC: Unix Domain Socket (project-local `.ralph/ralph.sock`) — JSON protocol with typed Request/Response enums via `serde_json`
- Worker isolation: Git Worktrees — create on spawn, destroy on kill; each worker operates in its own worktree with its own branch
- Process model: Direct child process via `tokio::process::Command` — daemon is parent process with immediate awareness of worker death
- Code organization: Cargo workspace with 5 crates — `ralph` (binary), `ralph-common` (shared types/schema/protocol), `ralph-config` (TOML resolution), `ralph-worker` (process/worktree), `ralph-pipeline` (state machine/healing/artifacts)
- Testing strategy: Unit tests per crate + Integration tests + E2E tests via `assert_cmd` 2.1.x + `predicates` 3.x
- BMAD artifact parsing: `serde_yaml_ng` 0.10.x for YAML frontmatter, raw file read for markdown body
- Log rotation: `tracing-appender` 0.2.x with daily rolling file appender
- Terminal output: Hybrid approach — static CLI output (crossterm + indicatif) for standard commands, ratatui TUI for `ralph watch` live dashboard
- Implementation sequence: ralph-common → ralph-config → ralph-worker → ralph-pipeline → ralph (daemon + CLI)
- Error handling pattern: `thiserror` typed Error enums per crate, `anyhow` at binary layer, no `unwrap()` without justification, no `panic!()` outside tests
- Async patterns: `tokio::sync::mpsc` for inter-component communication, `Arc<RwLock<T>>` for read-heavy shared state, `tokio::sync::watch` for shutdown broadcast, `tokio::task::spawn_blocking` for all SQLite access
- Logging: Structured tracing with levels (error/warn/info/debug/trace), span naming by module path, no story content or secrets in logs
- Command structure: `ralph start`, `ralph stop`, `ralph status`, `ralph diagnose <id>`, `ralph retry <id>`, `ralph init`, `ralph watch`

**From UX Design:**

- Component-based terminal output system: 13 reusable components (Section Border, Health Line, Progress Bar, Summary Line, Story Table, Worker Table, Event Timeline, Spinner, Error Message, Hint Line, Config Display, Action Guide, Spawn List, Completion Summary)
- Semantic color system: green (healthy/success), yellow (active/healing), red (failed/attention), dim (queued/secondary), magenta (accent/borders), bold (emphasis)
- NO_COLOR standard compliance + `--no-color` CLI flag for explicit plain-text output
- Terminal width adaptation: <80 cols (aggressive truncation), 80-99 (standard), 100-120 (comfortable), >120 (capped at 120)
- Progressive disclosure: compact default → `--detail` flag → single-entity deep dive
- State word vocabulary: completed, running, queued, blocked, retrying, restarting, diagnosing, failed, healthy, idle — consistent across all commands
- Section border pattern: `※ Name ═══════ context ※` (Zellij-inspired) with magenta markers, dim fill, semantic context coloring
- Progress bar specification: 30-char fixed width, magenta accent `█`, dim `░`, percentage label
- Hint line with progressive discoverability — appears for first N invocations (default 5), dismissable via `hints = false` in ralph.toml
- Error message pattern: `Error:` prefix (Red Bold) + description + actionable suggestion; never stack traces or internal errors
- Exit codes: 0 (success), 1 (general error), 2 (daemon error), 3 (pipeline error)
- Global CLI flags: `--no-color`, `--quiet` (`-q`), `--verbose` (`-v`), `--help` (`-h`)
- Command chaining pattern: every output suggests the logical next command (start→status, status→diagnose, diagnose→retry)
- Accessibility: color-independent state words, NO_COLOR support, screen reader compatibility, UTF-8 with ASCII fallback
- Responsive terminal layouts with graceful degradation by truncating least-critical columns first

### FR Coverage Map

- FR1: Epic 5 — Initiate BMAD planning workflows
- FR2: Epic 5 — Break down requirements into epics and stories
- FR3: Epic 5 — Generate sprint plans with sequencing and dependencies
- FR4: Epic 5 — Team members contribute through BMAD workflows
- FR5: Epic 2 — Read BMAD sprint plans as pipeline input
- FR6: Epic 1 — Install as self-contained CLI tool
- FR7: Epic 1 — Initialize on new or existing project
- FR8: Epic 1 — Configure via TOML configuration file
- FR9: Epic 1 — Override config with CLI flags
- FR10: Epic 1 — Multi-source config precedence resolution
- FR11: Epic 2 — Start the Ralph daemon
- FR12: Epic 2 — Stop daemon with clean shutdown
- FR13: Epic 2 — 72+ hour continuous daemon operation
- FR14: Epic 2 — Auto-detect sprint plans for ingestion
- FR15: Epic 2 — Graceful signal handling (SIGTERM, SIGINT)
- FR16: Epic 2 — Drive SDLC workflow from ingestion to completion
- FR17: Epic 2 — Story sequencing and parallelization by dependency
- FR18: Epic 2 — Persistent state tracking across restarts
- FR19: Epic 2 — Assign stories to workers by concurrency and dependency
- FR20: Epic 2 — Spawn configurable concurrent Claude Code workers
- FR21: Epic 2 — Monitor worker health in real-time
- FR22: Epic 2 — Kill and restart individual workers independently
- FR23: Epic 2 — Replace any worker without side effects (cattle model)
- FR24: Epic 2 — Isolated story execution per worker
- FR25: Epic 4 — Layer 1 step retry for failed pipeline steps
- FR26: Epic 4 — Layer 2 worker restart with fresh state
- FR27: Epic 4 — Layer 3 diagnose flow for unresolvable issues
- FR28: Epic 4 — Track retry attempts and escalate through layers
- FR29: Epic 3 — Query running daemon for real-time state
- FR30: Epic 3 — View story progress at a glance
- FR31: Epic 3 — View worker health and active count
- FR32: Epic 3 — View retry/healing state for recovering stories
- FR33: Epic 3 — Color-coded structured terminal output
- FR34: Epic 4 — Generate diagnostic report for failed stories
- FR35: Epic 4 — View failure details and healing attempts in report
- FR36: Epic 4 — Export structured diagnostic report for automation
- FR37: Epic 4 — Re-feed corrected stories into pipeline
- FR38: Epic 1 — Shell completion for commands and flags
- FR39: Epic 1 — Shell completion for zsh and bash
- FR40: Epic 1 — Standard exit codes for all CLI commands

**Coverage: 40/40 FRs mapped — no gaps.**

## Epic List

### Epic 1: Project Foundation & Developer Setup
Developer can install Ralph, initialize a project, and configure it for their needs — from zero to a working CLI binary with `ralph init`, TOML configuration, and shell completion.
**FRs covered:** FR6, FR7, FR8, FR9, FR10, FR38, FR39, FR40

### Epic 2: Autonomous Story Execution
Developer can start the Ralph daemon, which autonomously ingests a sprint plan, sequences stories by dependency, spawns parallel Claude Code workers in isolated git worktrees, and executes stories to completion — the core "start Ralph and walk away" experience.
**FRs covered:** FR5, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23, FR24

### Epic 3: Pipeline Monitoring & Status Display
Developer can query Ralph's real-time pipeline state via `ralph status` and see story progress, worker health, and healing state through rich color-coded terminal output with the full UX component system.
**FRs covered:** FR29, FR30, FR31, FR32, FR33

### Epic 4: Self-Healing & Error Recovery
Ralph automatically recovers from failures through three progressive healing layers (step retry → worker restart → diagnose flow), and developer can diagnose exhausted failures and re-feed corrected stories via `ralph diagnose` and `ralph retry`.
**FRs covered:** FR25, FR26, FR27, FR28, FR34, FR35, FR36, FR37

### Epic 5: Planning Integration
Developer can use BMAD planning workflows to create planning artifacts (PRD, architecture, stories, sprint plans), team members can contribute domain expertise, and all artifacts flow seamlessly into Ralph's execution pipeline — completing the full plan-to-execute SDLC loop.
**FRs covered:** FR1, FR2, FR3, FR4

---

## Epic 1: Project Foundation & Developer Setup

Developer can install Ralph, initialize a project, and configure it for their needs — from zero to a working CLI binary with `ralph init`, TOML configuration, and shell completion.

### Story 1.1: Cargo Workspace Scaffold & CLI Entry Point

As a developer,
I want to install bmad-ralph as a standalone CLI binary,
So that I can begin using Ralph on my projects.

**Acceptance Criteria:**

**Given** a fresh checkout of the repository
**When** I run `cargo build`
**Then** a single `ralph` binary is produced in the target directory
**And** the workspace contains 5 crates: ralph, ralph-common, ralph-config, ralph-worker, ralph-pipeline with correct dependency flow (ralph-common has no internal deps, ralph depends on all)

**Given** the compiled ralph binary
**When** I run `ralph --help`
**Then** I see available subcommands (start, stop, status, diagnose, retry, init, watch) with descriptions

**Given** the compiled ralph binary
**When** I run `ralph --version`
**Then** I see the current version number

**Given** each crate in the workspace
**When** I run `cargo clippy -- -D warnings` and `cargo fmt --check`
**Then** zero warnings and zero formatting violations are reported

### Story 1.2: Shared Types, Error Models & Database Schema

As a developer building Ralph,
I want a shared foundation of types, error models, and database schema,
So that all crates use consistent data structures and can communicate reliably.

**Acceptance Criteria:**

**Given** the ralph-common crate
**When** I use story model types
**Then** StoryState enum represents all states: queued, blocked, assigned, running, retrying, restarting, diagnosing, completed, failed
**And** Story struct includes id, title, acceptance_criteria, dependencies, state, worker_id, duration, retry_count

**Given** the ralph-common crate
**When** I use worker model types
**Then** WorkerState enum represents: healthy, idle, restarting, failed
**And** WorkerHealth struct includes worker_id, state, assigned_story, uptime

**Given** the ralph-common crate
**When** I use pipeline model types
**Then** PipelineState enum represents: idle, running, healing, complete, error
**And** SprintPlan struct includes stories with dependency relationships

**Given** the ralph-common crate
**When** I use healing model types
**Then** HealingLayer enum represents: StepRetry, WorkerRestart, Diagnose
**And** HealingAttempt struct includes layer, attempt_number, timestamp, failure_reason

**Given** the ralph-common crate
**When** I use the error module
**Then** a base Error enum is available via thiserror with proper Display implementations

**Given** the ralph-common protocol module
**When** I use Request and Response enums
**Then** they are serializable/deserializable via serde_json for Unix socket communication
**And** Request variants include: Status, Stop, Diagnose, Retry
**And** Response variants include: Status (with pipeline and worker data), Ok, Error

**Given** the ralph-common db module
**When** I initialize the database
**Then** SQLite tables are created with WAL mode enabled
**And** table names are snake_case plural (stories, workers, healing_attempts)
**And** timestamps use ISO 8601 format
**And** a migrations system is in place for future schema changes

### Story 1.3: Configuration System with Three-Tier Precedence

As a developer,
I want to configure Ralph's behavior through TOML files and CLI flags,
So that I can customize daemon settings, worker counts, and project paths for my needs.

**Acceptance Criteria:**

**Given** a ralph.toml file in the project root
**When** Ralph reads configuration
**Then** all settings are loaded correctly: workers (integer), retry_limit (integer), log_level (string), sprint_plan path, log directory

**Given** no configuration files exist
**When** Ralph loads config
**Then** sensible defaults are used: workers=3, retry_limit=3, log_level="info"

**Given** both project-level ralph.toml and user-level ~/.config/ralph/config.toml
**When** there are conflicting values
**Then** project TOML takes precedence over user-level defaults

**Given** CLI flags and TOML config both specifying the same setting
**When** configuration is resolved
**Then** CLI flags take highest precedence (CLI flags > project TOML > user TOML defaults)

**Given** a ralph.toml with unknown keys
**When** Ralph loads config
**Then** unknown keys are ignored without error (forward compatibility)

**Given** the ralph-config crate
**When** unit tests run
**Then** all three-tier precedence scenarios are verified with tests

### Story 1.4: Project Initialization Command

As a developer,
I want to initialize bmad-ralph on my project with a single command,
So that I can start using Ralph with minimal setup effort.

**Acceptance Criteria:**

**Given** an existing project directory with git initialized
**When** I run `ralph init`
**Then** a ralph.toml is created with sensible defaults
**And** a `.ralph/` runtime directory is created (and added to .gitignore if not already present)

**Given** `ralph init` runs
**When** the project type is detected
**Then** a config summary is displayed showing the created settings (key-value pairs, one per line)

**Given** `ralph init` completes
**When** the output is rendered
**Then** numbered next steps are displayed: (1) Plan sprint with BMAD, (2) ralph start, (3) ralph status

**Given** a project where ralph.toml already exists
**When** I run `ralph init`
**Then** a clear message is displayed: "Project already initialized" with hint to edit config

**Given** `ralph init` completes successfully
**When** the process exits
**Then** exit code 0 is returned

**Given** `ralph init` fails (e.g., no write permission)
**When** the process exits
**Then** exit code 1 is returned with an error message showing the problem and a suggested fix

### Story 1.5: Shell Completion & CLI Polish

As a developer,
I want shell completions and consistent CLI behavior,
So that I can use Ralph efficiently with tab-completion and trust its exit codes.

**Acceptance Criteria:**

**Given** zsh shell
**When** I source the generated completion script (via `ralph completions zsh`)
**Then** tab-completion works for all commands, subcommands, and common flags

**Given** bash shell
**When** I source the generated completion script (via `ralph completions bash`)
**Then** tab-completion works for all commands, subcommands, and common flags

**Given** any CLI command that succeeds
**When** it completes
**Then** exit code 0 is returned

**Given** any CLI command that fails
**When** it completes
**Then** a non-zero exit code is returned: 1 (general error), 2 (daemon error), 3 (pipeline error)

**Given** `--no-color` flag on any command
**When** output is rendered
**Then** no ANSI escape codes are present in the output

**Given** `NO_COLOR` environment variable is set (any value)
**When** any command produces output
**Then** no ANSI color codes are present in the output

**Given** `--quiet` flag on any command
**When** the command runs
**Then** only essential output is shown (errors and primary result)

**Given** `--verbose` flag on any command
**When** the command runs
**Then** additional detail is shown (debug-level information)

---

## Epic 2: Autonomous Story Execution

Developer can start the Ralph daemon, which autonomously ingests a sprint plan, sequences stories by dependency, spawns parallel Claude Code workers in isolated git worktrees, and executes stories to completion — the core "start Ralph and walk away" experience.

### Story 2.1: Daemon Process Lifecycle & Signal Handling

As a developer,
I want to start and stop the Ralph daemon,
So that I can control when autonomous story execution is active.

**Acceptance Criteria:**

**Given** no daemon is running
**When** I run `ralph start`
**Then** a daemon process starts, a PID file is written to `.ralph/ralph.pid`, and a startup confirmation is displayed ("Starting daemon... done")

**Given** a running daemon
**When** I run `ralph stop`
**Then** the daemon shuts down gracefully — terminating all active workers, saving pipeline state to SQLite, releasing resources, and removing PID and socket files
**And** a confirmation is displayed: "Ralph stopped — was running for Xh Ym"

**Given** a running daemon
**When** SIGTERM is received
**Then** the daemon performs the same graceful shutdown as `ralph stop`

**Given** a running daemon
**When** SIGINT is received
**Then** the daemon performs graceful shutdown

**Given** a daemon is already running (PID file exists and process is alive)
**When** I run `ralph start`
**Then** an error is displayed: "Error: Ralph is already running (PID xxxxx)" with hint "Check status: ralph status"

**Given** no daemon is running
**When** I run `ralph stop`
**Then** the message "Ralph is not running. Nothing to stop." is displayed

**Given** the daemon starts
**When** initialization completes
**Then** structured logging is set up via tracing-appender with daily rotation to `.ralph/logs/`

### Story 2.2: Unix Domain Socket IPC

As a developer,
I want CLI commands to communicate with the running daemon,
So that I can query state and send commands to the running daemon process.

**Acceptance Criteria:**

**Given** a running daemon
**When** it starts
**Then** a Unix domain socket is created at `.ralph/ralph.sock` and the daemon listens for incoming connections

**Given** a CLI command (status, stop, diagnose, retry)
**When** it needs to communicate with the daemon
**Then** it connects to `.ralph/ralph.sock` and sends a JSON-serialized Request message

**Given** the socket server receives a Request
**When** it processes the request
**Then** it returns a JSON-serialized Response using the typed Response enum

**Given** `ralph stop` is run
**When** the CLI sends a Stop request via socket
**Then** the daemon acknowledges with an Ok response and initiates graceful shutdown

**Given** any CLI command that requires daemon communication
**When** no daemon is running (no socket file or connection refused)
**Then** an error is displayed: "Error: No running daemon found" with suggestion "Start Ralph first: ralph start"

**Given** the daemon shuts down
**When** cleanup runs
**Then** the socket file `.ralph/ralph.sock` is removed

**Given** concurrent CLI commands
**When** multiple status queries arrive simultaneously
**Then** all are handled without blocking or corruption (socket server handles concurrent connections)

### Story 2.3: SQLite State Persistence Layer

As a developer,
I want pipeline state to persist across daemon restarts,
So that no progress is lost if the daemon crashes or is restarted.

**Acceptance Criteria:**

**Given** a daemon starts for the first time
**When** no database exists
**Then** `.ralph/ralph.db` is created with WAL mode enabled and all schema tables initialized (stories, workers, healing_attempts)

**Given** active pipeline execution
**When** a story state changes (e.g., queued → running)
**Then** the transition is written to SQLite atomically — no partial state updates possible

**Given** a daemon crash (process killed unexpectedly)
**When** the daemon restarts
**Then** it reads pipeline state from SQLite and resumes from the last persisted state without losing completed work

**Given** any SQLite read or write operation
**When** it executes in the daemon
**Then** it runs via `tokio::task::spawn_blocking` to avoid blocking the async runtime

**Given** concurrent status queries during active pipeline execution
**When** the CLI reads state while the daemon writes
**Then** SQLite WAL mode allows concurrent reads without blocking writes

**Given** the database over a 72+ hour daemon run
**When** data accumulates
**Then** database file size remains bounded and query performance does not degrade

### Story 2.4: BMAD Artifact Parsing & Sprint Plan Ingestion

As a developer,
I want Ralph to read my BMAD planning artifacts and ingest the sprint plan,
So that the pipeline knows which stories to execute and their dependencies.

**Acceptance Criteria:**

**Given** BMAD markdown files with YAML frontmatter (delimited by `---`)
**When** Ralph parses them
**Then** the YAML header is deserialized via serde_yaml_ng and the markdown body is captured as raw string

**Given** a sprint plan artifact in the expected location
**When** Ralph ingests it
**Then** all stories are identified with their IDs, titles, acceptance criteria, and dependency relationships

**Given** story dependencies in the sprint plan
**When** Ralph processes them
**Then** a dependency graph is constructed enabling correct sequencing and parallelization analysis

**Given** `ralph start`
**When** a sprint plan exists in the standard planning artifacts location
**Then** it is auto-detected and ingested into the pipeline automatically

**Given** no sprint plan exists in the project
**When** `ralph start` is run
**Then** an error is displayed: "Error: No sprint plan found in project" with guidance "Run BMAD sprint planning first, then try ralph start again."

**Given** a malformed sprint plan (invalid YAML, missing required fields)
**When** Ralph attempts to parse it
**Then** a clear error is displayed identifying the parsing problem and file location

### Story 2.5: Pipeline State Machine & Story Scheduler

As a developer,
I want the pipeline to orchestrate story execution with proper sequencing,
So that stories are executed in the right order respecting dependencies and maximizing parallelism.

**Acceptance Criteria:**

**Given** a set of ingested stories with dependencies
**When** the pipeline starts
**Then** stories with no unresolved dependencies are immediately marked as schedulable (queued)

**Given** a story's dependencies all have status "completed"
**When** the scheduler evaluates
**Then** the dependent story becomes schedulable

**Given** multiple schedulable stories and available workers
**When** the scheduler assigns work
**Then** stories are assigned to workers in parallel up to the configured concurrency limit

**Given** the state machine
**When** a story transitions
**Then** only valid transitions occur: queued → assigned → running → completed OR queued → assigned → running → (healing states) → completed/failed
**And** each transition is persisted atomically to SQLite

**Given** all stories reach a terminal state (completed or failed)
**When** the pipeline evaluates
**Then** the pipeline state transitions to "complete" and a sprint completion event is recorded

**Given** a story is assigned to a worker
**When** the worker begins execution
**Then** the story state moves to "running" and the worker assignment is recorded

### Story 2.6: Worker Spawning & Git Worktree Isolation

As a developer,
I want Ralph to spawn Claude Code workers in isolated git worktrees,
So that multiple stories can be executed in parallel without file or git conflicts.

**Acceptance Criteria:**

**Given** a story is assigned to a worker
**When** the worker spawns
**Then** a new git worktree is created in `.ralph/worktrees/worker-N/` with a dedicated branch named `ralph/story-{id}-{slug}`

**Given** a worker is spawned
**When** it starts execution
**Then** a Claude Code CLI session is launched as a child process via `tokio::process::Command` in the worktree directory
**And** the story specification and acceptance criteria are provided as context

**Given** a worker completes (story finished) or is killed
**When** cleanup runs
**Then** the git worktree is destroyed and the associated branch is cleaned up

**Given** multiple workers running concurrently
**When** they execute stories
**Then** each operates in complete isolation — no shared files, no git branch collisions, no working directory conflicts

**Given** the configured worker count (default 3)
**When** `ralph start` runs with a sprint plan
**Then** up to the configured number of workers are spawned for the initial wave of schedulable stories

**Given** a worker spawns
**When** the worktree creation or process spawn fails
**Then** the error is captured, the story is returned to schedulable state, and the failure is logged

### Story 2.7: Worker Health Monitoring & Lifecycle Management

As a developer,
I want Ralph to monitor worker health and manage their lifecycle reliably,
So that the system runs stably for 72+ hours with automatic worker replacement.

**Acceptance Criteria:**

**Given** running workers
**When** the daemon checks health
**Then** each worker's status (healthy, failed, idle) is tracked in real-time and updated in the database

**Given** a worker process exits unexpectedly (non-zero exit code or signal)
**When** the daemon detects the exit
**Then** the worker is marked as failed, the assigned story's state is updated, and an event is logged

**Given** a request to kill a specific worker
**When** the kill is executed
**Then** only the target worker is affected — all other workers continue uninterrupted

**Given** a killed or failed worker
**When** a replacement is needed
**Then** a new worker is spawned with completely fresh state (new worktree, new process) — stateless cattle model with no carryover

**Given** the daemon is running
**When** 72+ hours pass under typical load
**Then** memory consumption remains within 10% of baseline, no file handle leaks, and child process count remains bounded

**Given** worker stdout/stderr output
**When** produced during execution
**Then** it is captured asynchronously and available for diagnostic purposes without blocking the daemon event loop

---

## Epic 3: Pipeline Monitoring & Status Display

Developer can query Ralph's real-time pipeline state via `ralph status` and see story progress, worker health, and healing state through rich color-coded terminal output with the full UX component system.

### Story 3.1: Terminal Rendering Engine & Theme System

As a developer,
I want consistent, beautiful terminal output across all Ralph commands,
So that I can quickly scan information with clear visual hierarchy.

**Acceptance Criteria:**

**Given** the rendering engine
**When** terminal width is detected
**Then** layout adapts: <80 cols (story name truncated to 15 chars), 80-99 (standard, name 20 chars), 100-120 (comfortable, name 30 chars), >120 (capped at 120)

**Given** the theme system
**When** colors are rendered
**Then** semantic colors are consistent across all output: green (32) = healthy/success, yellow (33) = active/healing, red (31) = failed/attention, dim (2) = queued/secondary, magenta (35) = accent/borders, bold (1) = emphasis

**Given** `--no-color` flag or `NO_COLOR` environment variable
**When** output is rendered
**Then** all ANSI codes are suppressed and output remains fully functional with text structure, alignment, and state words alone

**Given** the Section Border component
**When** rendered
**Then** it follows the pattern `※ Name ═══════ context ※` with magenta `※` markers, dim `═` fill, bold name, and semantically colored context
**And** border width auto-fills to detected terminal width (min 80, max 120)

**Given** the Spinner component
**When** an operation is in progress
**Then** a Braille spinner (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) animates at ~100ms intervals
**And** it is replaced by `✓` (green) on success or `✗` (red) on failure

**Given** the Error Message component
**When** an error occurs
**Then** output follows: `Error:` (red bold) + description (default) + actionable suggestion (dim)
**And** never includes stack traces, internal error codes, or source file paths

### Story 3.2: Status Command — Health Overview & Sprint Progress

As a developer,
I want to check Ralph's overall health and sprint progress with a single command,
So that I can answer "is everything okay?" in under 2 seconds of reading.

**Acceptance Criteria:**

**Given** a running daemon
**When** I run `ralph status`
**Then** the output starts with a Section Border: `※ Ralph ═══════ {state} ※` where state is healthy/healing/complete/error with appropriate color

**Given** a running daemon
**When** I run `ralph status`
**Then** a Health Line displays narrative state (e.g., "Running for 6h 42m with 3 workers") immediately below the border

**Given** an active sprint with stories
**When** I run `ralph status`
**Then** a Progress Bar is displayed: 30-char fixed width, magenta `█` for filled, dim `░` for empty, with "N% completed" label
**And** a Summary Line shows color-coded state counts in fixed order: completed (green) → running (yellow) → healing states (yellow) → queued (dim) → blocked (dim) → failed (red)

**Given** a completed sprint (all stories resolved)
**When** I run `ralph status`
**Then** the border shows "complete" (green), Health Line shows "Sprint finished in Xh Ym with N workers"
**And** a Completion Summary section displays: success percentage, self-healed count, failed count, total runtime, and guidance for failed stories ("run ralph diagnose N for details")

**Given** no daemon is running
**When** I run `ralph status`
**Then** an Error Message is displayed: "Error: No running daemon found" with hint "Start Ralph first: ralph start"

**Given** any status query
**When** the daemon is under load with up to 5 active workers
**Then** the response returns within 2 seconds

### Story 3.3: Status Command — Story & Worker Detail Tables

As a developer,
I want to see per-story and per-worker details in status output,
So that I can understand exactly what each worker is doing and how each story is progressing.

**Acceptance Criteria:**

**Given** `ralph status` with an active sprint
**When** stories exist
**Then** a Story Table is displayed under `※ Stories ═══` border with columns: ID (4 chars, right-aligned), Name (20 chars, left, truncated with `…`), State (11 chars, color-coded state word), Worker (6 chars), Duration (9 chars, right), Retries (7 chars, right)

**Given** story state words in the table
**When** displayed
**Then** they use consistent colors: completed=green, running=yellow, retrying=yellow, restarting=yellow, diagnosing=yellow, queued=dim, blocked=dim, failed=red

**Given** `ralph status` with active workers
**When** workers are displayed
**Then** a Worker Table is displayed under `※ Workers ═══ N/N healthy ※` border showing: Worker ID (bold), health state (colored), current assignment, uptime

**Given** `ralph status --detail`
**When** run
**Then** expanded information is shown: full story events timeline per story, detailed worker logs, additional context per entry

**Given** `ralph status` during the first 5 invocations
**When** output is rendered
**Then** a Hint Line appears at the footer in dim text: "Tip: ralph status --detail for expanded view"

**Given** stories are sorted in the table
**When** displayed
**Then** they appear in story ID ascending order (execution order)

---

## Epic 4: Self-Healing & Error Recovery

Ralph automatically recovers from failures through three progressive healing layers (step retry → worker restart → diagnose flow), and developer can diagnose exhausted failures and re-feed corrected stories via `ralph diagnose` and `ralph retry`.

### Story 4.1: Self-Healing Layer 1 — Automatic Step Retry

As a developer,
I want failed pipeline steps to retry automatically,
So that transient failures are resolved without my intervention.

**Acceptance Criteria:**

**Given** a story step fails during worker execution
**When** the failure is detected by the pipeline
**Then** Layer 1 automatically retries the failed step on the same worker

**Given** a Layer 1 retry
**When** the retry limit is not reached (default 3 attempts)
**Then** the step is re-executed and the story state changes to "retrying"

**Given** a Layer 1 retry
**When** the retry succeeds
**Then** the story continues to the next step normally and the self-healed event is recorded

**Given** a Layer 1 retry
**When** all retry attempts are exhausted (default 3)
**Then** the failure escalates to Layer 2 (worker restart)

**Given** any retry attempt
**When** it occurs
**Then** a HealingAttempt record is created in the database with: layer (StepRetry), attempt number, timestamp, failure reason
**And** a tracing event is logged at warn level: `story_id`, `attempt`, `layer="step_retry"`, "healing activated"

### Story 4.2: Self-Healing Layer 2 — Worker Restart

As a developer,
I want failed workers to be replaced with fresh ones,
So that environment-related issues are resolved by starting clean.

**Acceptance Criteria:**

**Given** Layer 1 retries are exhausted for a story
**When** escalation to Layer 2 occurs
**Then** the current worker is killed, its worktree is destroyed, and a fresh replacement worker is spawned

**Given** a fresh Layer 2 worker
**When** it starts
**Then** it has a new git worktree and completely clean state — the story is re-executed from scratch (not from the failed step)

**Given** a Layer 2 restart
**When** the story completes successfully on the fresh worker
**Then** the story is marked as completed with a "self-healed" flag and the healing history is preserved

**Given** a Layer 2 restart
**When** the story fails again on the fresh worker
**Then** the failure escalates to Layer 3 (diagnose flow)

**Given** Layer 2 activity
**When** it occurs
**Then** a HealingAttempt record is created with: layer (WorkerRestart), old worker ID, new worker ID, timestamp
**And** the story state changes to "restarting" during the transition

### Story 4.3: Self-Healing Layer 3 — Diagnose Flow

As a developer,
I want the system to run a diagnostic analysis when retries and restarts fail,
So that complex failures get automated root cause analysis before requiring my attention.

**Acceptance Criteria:**

**Given** Layer 2 restart has failed
**When** escalation to Layer 3 occurs
**Then** a dedicated diagnose flow is triggered and the story state changes to "diagnosing"

**Given** the diagnose flow
**When** it analyzes the failure
**Then** it examines: failure patterns across attempts, worker output/logs, story specification, and acceptance criteria for inconsistencies

**Given** the diagnose flow completes
**When** a root cause or recommendation is identified
**Then** a structured diagnostic report is stored with the story's data including: root cause analysis, recommendation, and suggested fix

**Given** all three healing layers are exhausted without resolution
**When** the final assessment is made
**Then** the story is marked as "failed" (exhausted) requiring user attention
**And** the story state uses the red color semantic in all output

**Given** Layer 3 activity
**When** it completes
**Then** the full healing history across all three layers is preserved and queryable in the database

### Story 4.4: Diagnose Command & Diagnostic Reports

As a developer,
I want to view detailed diagnostic reports for failed stories,
So that I can understand what went wrong and how to fix it.

**Acceptance Criteria:**

**Given** a failed story
**When** I run `ralph diagnose <id>`
**Then** a structured diagnostic report is displayed opening with Section Border: `※ Diagnose ═══ Story #N: {name} ※`
**And** state summary shows: "failed (exhausted — all 3 healing layers attempted)", duration, retry count across workers

**Given** the diagnostic report
**When** the Timeline section is displayed
**Then** an Event Timeline component shows chronological events with: timestamps (dim), event descriptions (default), layer labels (bold "Layer 1:", "Layer 2:", "Layer 3:")
**And** events are dense (no blank lines between entries), indented 2 spaces

**Given** the diagnostic report
**When** a recommendation exists
**Then** a Recommendation section displays: root cause explanation and suggested fix including the `ralph retry <id>` command

**Given** the diagnostic report
**When** exported or displayed
**Then** the format is structured enough for Claude Code to parse and propose automated fixes (clear sections, consistent formatting, machine-readable story context)

**Given** no failed stories exist
**When** I run `ralph diagnose`
**Then** the message "No failed stories to diagnose. All stories completed successfully." is displayed

**Given** an invalid story ID
**When** I run `ralph diagnose <id>`
**Then** an error is displayed: "Error: Story #N not found in current sprint" with hint "Run ralph status to see available stories"

### Story 4.5: Retry Command & Story Re-ingestion

As a developer,
I want to re-feed corrected stories back into the pipeline,
So that I can resolve exhausted failures and complete the sprint.

**Acceptance Criteria:**

**Given** a failed story
**When** I run `ralph retry <id>`
**Then** the story is re-queued into the pipeline with reset healing state (all layers available again)
**And** confirmation output is displayed: Section Border with "retrying", story name, worker assignment, and hint to check status

**Given** a re-queued story
**When** the pipeline processes it
**Then** it goes through the full execution and healing cycle as if it were a new story (fresh healing attempts)

**Given** an invalid story ID
**When** I run `ralph retry <id>`
**Then** an error is displayed: "Error: Story #N not found in current sprint" with hint "Run ralph status to see available stories"

**Given** a story that is not in failed state (e.g., running or completed)
**When** I run `ralph retry <id>`
**Then** an appropriate message is displayed: "Story #N is currently {state} — retry is only available for failed stories"

**Given** a completed sprint with failures
**When** I run `ralph status`
**Then** the Completion Summary shows success rate, self-healed count, and for each failed story: "Story #N — run ralph diagnose N for details"

**Given** no daemon is running
**When** I run `ralph retry <id>`
**Then** an error is displayed: "Error: No running daemon found" with hint to start Ralph

---

## Epic 5: Planning Integration

Developer can use BMAD planning workflows to create planning artifacts (PRD, architecture, stories, sprint plans), team members can contribute domain expertise, and all artifacts flow seamlessly into Ralph's execution pipeline — completing the full plan-to-execute SDLC loop.

### Story 5.1: BMAD Submodule Integration & Planning Workflow Access

As a developer,
I want Ralph to integrate BMAD planning capabilities into my project,
So that I can create planning artifacts without leaving the Ralph workflow.

**Acceptance Criteria:**

**Given** `ralph init` on a fresh project
**When** initialization runs
**Then** BMAD is configured as a git submodule (or validated if already present) with a pinned version to prevent upstream breaking changes

**Given** BMAD is integrated in the project
**When** a developer starts a planning session
**Then** they can access BMAD workflows to create PRD, architecture, UX design, and sprint planning artifacts

**Given** BMAD planning workflows
**When** team members (PM, designer) participate
**Then** they can contribute domain expertise and design specs through the standard BMAD workflow interfaces

**Given** an upstream BMAD update
**When** the developer chooses to update
**Then** the submodule version is updated explicitly via `git submodule update --remote _bmad`
**And** the previous version remains available for rollback

### Story 5.2: Sprint Plan Generation & Pipeline Artifact Handoff

As a developer,
I want BMAD to produce sprint plans that Ralph can directly consume,
So that the transition from planning to execution is seamless with zero manual translation.

**Acceptance Criteria:**

**Given** BMAD planning workflows
**When** a developer completes requirements decomposition
**Then** epics and user stories with acceptance criteria are produced in markdown with YAML frontmatter format

**Given** BMAD sprint planning workflow
**When** a sprint plan is generated
**Then** it includes story sequencing and dependency mapping in a format Ralph's artifact parser can ingest

**Given** generated planning artifacts
**When** stored in the project
**Then** they are placed in the standard `_bmad-output/` location structure that Ralph's auto-detection can find

**Given** the complete planning-to-execution handoff
**When** a developer finishes BMAD planning and runs `ralph start`
**Then** the sprint plan is automatically detected and ingested without any manual file copying, format conversion, or configuration
