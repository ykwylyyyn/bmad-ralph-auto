---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - "product-brief-bmad-ralph-2026-02-27.md"
  - "prd.md"
  - "prd-validation-report.md"
  - "ux-design-specification.md"
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-02-28'
project_name: 'bmad-ralph'
user_name: 'Deadlock'
date: '2026-02-27'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
40 FRs organized across 8 subsystems:
- **Planning Integration (FR1-5):** BMAD workflow initiation, story/sprint plan creation, artifact ingestion — establishes the input contract for the pipeline
- **Project Setup & Configuration (FR6-10):** Self-contained CLI install, TOML config, CLI flag overrides, multi-source config precedence — defines the configuration architecture
- **Daemon Management (FR11-15):** Long-running daemon lifecycle, 72+ hour continuous operation, polling-based task detection, graceful signal handling — the foundational process model
- **Pipeline Orchestration (FR16-19):** State machine driving SDLC workflow, dependency-aware sequencing, parallelization analysis, persistent state across restarts — the orchestration brain
- **Worker Management (FR20-24):** Spawn up to 5 concurrent Claude Code sessions, cattle-model (stateless, replaceable), isolated execution, real-time health monitoring — the execution layer
- **Self-Healing Pipeline (FR25-28):** Three-layer progressive escalation (step retry → worker restart → diagnose flow), attempt tracking, layer progression — the reliability mechanism
- **Status & Monitoring (FR29-33):** Real-time daemon queries, story progress, worker health, retry/healing state, color-coded terminal output — the trust-building interface
- **Diagnostics & Error Recovery (FR34-37):** Structured diagnostic reports, failure details with healing attempts, machine-parseable format, story re-ingestion — the recovery workflow
- **Shell Integration (FR38-40):** zsh/bash completion, standard exit codes — CLI conventions

**Non-Functional Requirements:**
15 NFRs across 4 categories:
- **Reliability:** 72+ hour continuous operation, durable persistent state, isolated worker failures, atomic state transitions
- **Performance:** <100MB RSS, <1% CPU idle, 10% baseline growth limit over 72h, 2s status query response under load
- **Integration:** Claude Code CLI session management, BMAD markdown/frontmatter artifact reading, git branch/PR operations, pinned dependency versioning
- **Concurrency:** No hardcoded worker limit, reliable operation at 5 concurrent workers, full worker isolation (no shared mutable state, no file/git conflicts)

**UX Architectural Implications:**
- Component-based terminal output system: Section Border, Health Line, Progress Bar, Story Table, Worker Table, Event Timeline, Spinner, Error Message, Hint Line, Config Display, Action Guide, Spawn List, Completion Summary
- Semantic color system: green (healthy/success), yellow (active/healing), red (failed/attention), dim (queued/secondary), magenta (accent/borders)
- Progressive disclosure: compact default → --detail flag → single-entity deep dive
- Terminal width adaptation: 80-120 cols with graceful degradation
- NO_COLOR standard compliance and --no-color flag support
- Shared rendering layer for consistent formatting across all commands

### Scale & Complexity

- **Primary domain:** CLI tool with daemon process and process orchestration
- **Complexity level:** Medium — daemon lifecycle, state machine, parallel process management, and multi-layer self-healing within standard engineering constraints
- **Estimated architectural components:** 6-8 major components (daemon, pipeline/state machine, worker manager, self-healing engine, CLI interface, output renderer, config manager, artifact reader)

### Technical Constraints & Dependencies

- **Claude Code CLI sessions** as worker processes — product-level constraint defining the execution mechanism
- **Self-contained, zero external dependencies** — no cloud services, no network requirements for core operation
- **TOML** for Ralph's own configuration files (`ralph.toml`, pipeline state, worker state)
- **Input format contract (read-only):** BMAD outputs markdown documents, workflows are YAML, instructions are XML — Ralph consumes but does not control these formats
- **256-color ANSI support** with graceful plain-text fallback; respects NO_COLOR standard
- **Git** — branch management and PR creation through workers, not through daemon directly

### Cross-Cutting Concerns Identified

1. **State Persistence & Crash Recovery** — Pipeline state must survive daemon crashes and enable resumption. Affects: daemon, pipeline, worker manager, self-healing
2. **Process Isolation** — Workers must operate with zero shared mutable state, no filesystem conflicts, no git branch collisions. Affects: worker manager, pipeline orchestration
3. **Error Handling & Escalation Model** — Unified error model from step-level failures through three self-healing layers to user-facing diagnostics. Affects: all components
4. **Configuration Resolution** — Three-tier precedence (CLI flags > project TOML > user TOML defaults) applied consistently. Affects: daemon, workers, CLI
5. **Terminal Output Consistency** — Shared rendering layer enforcing color semantics, component structure, width adaptation, and NO_COLOR compliance across all commands. Affects: CLI, status, diagnostics
6. **Resource Management** — Memory, file handles, child processes must remain bounded over 72+ hour runs with no growth exceeding 10% baseline. Affects: daemon, worker manager

## Starter Template Evaluation

### Primary Technology Domain

Rust CLI tool with long-running daemon — standalone binary distribution. Process orchestration with parallel worker management, state machine, and multi-layer self-healing.

### Technology Preferences

- **Language:** Rust
- **Distribution:** Standalone binary
- **Configuration:** TOML (Ralph's own files), read-only consumption of BMAD markdown/YAML/XML
- **Terminal Output:** 256-color ANSI with NO_COLOR fallback
- **Async Runtime:** Tokio (process management, signals, timers, IPC)

### Starter Approach

**Custom `cargo init` + curated crate stack** — standard Rust practice for specialized CLI tools. No existing starter template covers the daemon + worker orchestration + state machine + TUI hybrid requirements. The project scaffolds from `cargo new` with a curated dependency set.

### Terminal Output Strategy: Hybrid

**Static CLI Output** for standard commands (`start`, `stop`, `status`, `diagnose`, `init`, `retry`):
- Run command → render output → return to shell
- Matches UX spec's "run command, get output, exit" interaction model
- Built with crossterm + indicatif + custom component rendering layer

**Ratatui TUI** for live monitoring (`ralph watch` or similar):
- Interactive real-time dashboard showing worker activity, story progress, self-healing events
- Live-updating render loop with keyboard navigation
- Optional enhancement beyond the core UX spec

### Initialization Command

```bash
cargo new bmad-ralph
cd bmad-ralph
```

### Core Crate Stack

**CLI & Runtime:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `clap` | 4.5.x | CLI parsing with derive macros, subcommands, shell completion (zsh/bash) |
| `tokio` | 1.49.x | Async runtime — process spawning (`tokio::process`), signal handling (`tokio::signal`), timers, IPC |

**Serialization & Configuration:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `serde` | 1.x | Serialization/deserialization framework with derive |
| `serde_json` | 1.x | JSON serialization for Unix socket protocol |
| `toml` | 0.9.x | TOML config parsing for ralph.toml and state files |

**Terminal Output — Static Commands:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `crossterm` | 0.29.x | Terminal control — colors (256-color), cursor, width detection, NO_COLOR support |
| `indicatif` | 0.18.x | Progress bars (sprint progress) and spinners (daemon startup) |

**Terminal Output — Live Monitoring TUI:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `ratatui` | 0.30.x | TUI framework for `ralph watch` live dashboard — tables, gauges, charts |

**Error Handling & Logging:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `anyhow` | latest | Application-level error handling with context |
| `thiserror` | latest | Typed library errors with derive macros |
| `tracing` | latest | Structured, async-aware logging for daemon |
| `tracing-subscriber` | latest | Log output formatting and filtering |

### Architectural Decisions Provided by Stack

**Language & Runtime:**
- Rust with Tokio async runtime — memory safety, zero-cost abstractions, single-binary distribution
- Async-first design for concurrent worker management and daemon event loop

**CLI Framework:**
- Clap derive macros for type-safe argument parsing
- Built-in shell completion generation (zsh, bash)
- Subcommand architecture: `ralph <command> [flags]`

**Configuration:**
- Serde + TOML for type-safe config deserialization
- Config structs derive `Deserialize`/`Serialize` for zero-boilerplate TOML handling

**Terminal Output:**
- Hybrid rendering: crossterm/indicatif for static commands, ratatui for live TUI
- Shared crossterm backend between static and TUI modes
- Custom component rendering layer implementing UX spec's design system (Section Border, Story Table, etc.)

**Error Handling:**
- `thiserror` for library-layer typed errors (pipeline errors, worker errors, config errors)
- `anyhow` for application-layer error propagation with context
- `tracing` for structured daemon logging with async span support

**Distribution:**
- `cargo build --release` produces single standalone binary
- No runtime dependencies — self-contained as per PRD requirement

**Note:** Project initialization using `cargo new` should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. State Persistence: SQLite + WAL
2. Daemon-CLI IPC: Unix Domain Socket
3. Worker Isolation: Git Worktrees
4. Process Model: Direct child process
5. Code Organization: Cargo workspace (5 crates)

**Important Decisions (Shape Architecture):**
6. Testing: assert_cmd + predicates for E2E
7. BMAD Artifact Parsing: serde for YAML/TOML, file read for markdown
8. Log Rotation: tracing-appender built-in rolling

**Deferred Decisions (Post-MVP):**
- Markdown parsing library — deferred until parsing needs are concrete
- Plugin system architecture — PRD Phase 2
- Multi-LLM worker support — PRD Phase 3

### State Persistence

- **Decision:** SQLite + WAL mode for pipeline state, file-based for logs and workflow artifacts
- **Crate:** `rusqlite` 0.38.x with `bundled` feature
- **Rationale:** SQLite + WAL provides atomic transactions, crash recovery, and concurrent read access. State (story progress, worker assignments, healing attempts) is queryable and survives daemon crashes. Logs stay as files for easy tailing/grep. Workflow artifacts stay as files matching BMAD's file-based model.
- **Affects:** ralph-common (schema), ralph (state writes, status reads), ralph-pipeline (state machine transitions)

### Daemon-CLI Communication

- **Decision:** Unix Domain Socket
- **Rationale:** Standard daemon IPC pattern, low latency, bidirectional. Supports both queries (status) and commands (stop). macOS/Linux coverage sufficient for target users.
- **Socket path:** Project-local (e.g., `.ralph/ralph.sock`) to support multiple projects
- **Affects:** ralph (socket server/client)

### Worker Isolation

- **Decision:** Git Worktrees
- **Rationale:** Natural fit for cattle workers — create on spawn, destroy on kill. Git-native isolation (separate working directory, shared object store). Lightweight disk footprint. Each worker operates in its own worktree with its own branch, eliminating file and git conflicts.
- **Affects:** ralph-worker (worktree lifecycle), ralph-pipeline (branch naming strategy)

### Process Model

- **Decision:** Direct child process via `tokio::process::Command`
- **Rationale:** Daemon is parent process — immediate awareness of worker death (exit status), direct stdout/stderr capture, simple kill semantics. Matches cattle model: spawn → monitor → kill → respawn.
- **Affects:** ralph-worker (process spawning), ralph (child process monitoring)

### Code Organization

- **Decision:** Cargo workspace with 5 crates

| Crate | Responsibility |
|-------|---------------|
| `ralph` | Binary entry point, CLI subcommands, daemon lifecycle, event loop, output rendering, Unix socket server/client |
| `ralph-pipeline` | State machine, story sequencing, dependency analysis, three-layer self-healing |
| `ralph-worker` | Worker spawning, health monitoring, git worktree management |
| `ralph-config` | TOML config resolution, three-tier precedence |
| `ralph-common` | Shared types, error types, state models, SQLite schema |

- **Dependency flow:** ralph → ralph-pipeline → ralph-worker, all depend on ralph-common, ralph-config consumed by ralph and ralph-pipeline
- **Rationale:** Workspace provides compile caching per crate, enforces API boundaries between components, and enables parallel compilation. 5 crates balances granularity with manageable complexity for solo developer.

### Testing Strategy

- **Decision:** Unit tests (per-crate `#[cfg(test)]`) + Integration tests (`tests/`) + E2E tests (`assert_cmd` 2.1.x + `predicates` 3.x)
- **Rationale:** assert_cmd is the standard Rust pattern for testing CLI binary output. Runs in CI, type-safe assertions, tests the real compiled binary.
- **Affects:** All crates (unit), workspace root (integration + E2E)

### BMAD Artifact Parsing

- **Decision:** Serde for YAML/TOML deserialization, raw file read for markdown content. Markdown parsing library deferred until concrete parsing needs arise.
- **Crate:** `serde_yaml_ng` 0.10.x for YAML frontmatter (maintained fork — original `serde_yaml` is deprecated since 0.9.34), `toml` + `serde` for TOML (already in stack)
- **Rationale:** BMAD artifacts are markdown with YAML frontmatter — split on `---`, deserialize header with serde_yaml_ng, keep body as raw string. No need for a markdown AST parser until proven otherwise.
- **Affects:** ralph-common (artifact types), ralph-pipeline (artifact ingestion)

### Log Rotation

- **Decision:** `tracing-appender` 0.2.x built-in rolling file appender with daily rotation
- **Rationale:** Already in tracing ecosystem (zero additional dependency). Daily rotation sufficient for 72+ hour daemon runs — produces manageable file sizes for developer inspection.
- **Affects:** ralph (log initialization)

### Updated Complete Crate Stack

**CLI & Runtime:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `clap` | 4.5.x | CLI parsing with derive macros, subcommands, shell completion (zsh/bash) |
| `tokio` | 1.49.x | Async runtime — process spawning, signal handling, timers, IPC |

**Serialization & Configuration:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `serde` | 1.x | Serialization/deserialization framework with derive |
| `serde_json` | 1.x | JSON serialization for Unix socket protocol |
| `toml` | 0.9.x | TOML config parsing for ralph.toml |
| `serde_yaml_ng` | 0.10.x | YAML frontmatter parsing for BMAD artifacts (replaces deprecated serde_yaml) |

**State Persistence:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `rusqlite` | 0.38.x | SQLite with WAL mode for pipeline state persistence |

**Terminal Output — Static Commands:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `crossterm` | 0.29.x | Terminal control — colors (256-color), cursor, width detection, NO_COLOR support |
| `indicatif` | 0.18.x | Progress bars (sprint progress) and spinners (daemon startup) |

**Terminal Output — Live Monitoring TUI:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `ratatui` | 0.30.x | TUI framework for `ralph watch` live dashboard — tables, gauges, charts |

**Error Handling & Logging:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `anyhow` | latest | Application-level error handling with context |
| `thiserror` | latest | Typed library errors with derive macros |
| `tracing` | latest | Structured, async-aware logging for daemon |
| `tracing-subscriber` | latest | Log output formatting and filtering |
| `tracing-appender` | 0.2.x | Rolling file appender with daily log rotation |

**Testing:**

| Crate | Version | Purpose |
|-------|---------|---------|
| `assert_cmd` | 2.1.x | CLI binary E2E testing |
| `predicates` | 3.x | Output assertion predicates |

### Decision Impact Analysis

**Implementation Sequence:**
1. ralph-common — shared types, error types, SQLite schema (foundation)
2. ralph-config — TOML config resolution (needed by everything)
3. ralph-worker — process spawning, worktree management (can test independently)
4. ralph-pipeline — state machine, healing logic (depends on worker + common)
5. ralph — daemon lifecycle, socket server, event loop, CLI subcommands, rendering (depends on all)

**Cross-Component Dependencies:**
- SQLite schema in ralph-common is shared contract between daemon (writes) and CLI (reads)
- Unix socket protocol defined in ralph-common, implemented in daemon (server) and CLI (client)
- Worker types in ralph-common used by pipeline (assignment) and worker (execution)
- Config types in ralph-config consumed by daemon and CLI

## Implementation Patterns & Consistency Rules

### Pattern Scope

These patterns address areas where AI agents could make different implementation choices that would cause conflicts. Standard Rust conventions enforced by clippy and rustfmt are NOT repeated here — agents are expected to follow idiomatic Rust by default.

### Rust Error Type Pattern

Each crate defines its own `Error` enum using `thiserror`, named simply `Error`. Module path disambiguates at usage site.

```rust
// ralph-pipeline/src/error.rs
#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("story {0} not found")]
    StoryNotFound(u32),
    #[error("worker error: {0}")]
    Worker(#[from] ralph_worker::Error),
}

// Usage in ralph:
use ralph_pipeline::Error as PipelineError;
```

### SQLite Schema Conventions

| Area | Convention | Example |
|------|-----------|---------|
| Table names | snake_case, plural | `stories`, `workers`, `healing_attempts` |
| Column names | snake_case | `story_id`, `created_at`, `retry_count` |
| Primary key | `id INTEGER PRIMARY KEY` | Every table |
| Foreign key | `{referenced_table_singular}_id` | `story_id`, `worker_id` |
| Timestamps | ISO 8601 strings | `2026-02-27T10:30:00Z` |
| Booleans | INTEGER 0/1 | SQLite has no native boolean |

### Unix Socket Protocol

- **Format:** JSON over Unix Domain Socket via `serde_json`
- **Rationale:** Human-debuggable, serde_json is Rust ecosystem standard, trivial to serialize/deserialize with serde derive
- **Message structure:** Request/Response pattern with typed message enums

```rust
#[derive(Serialize, Deserialize)]
#[serde(tag = "type")]
enum Request {
    Status,
    Stop { graceful: bool },
    Diagnose { story_id: u32 },
    Retry { story_id: u32 },
}

#[derive(Serialize, Deserialize)]
#[serde(tag = "type")]
enum Response {
    Status { pipeline: PipelineState, workers: Vec<WorkerState> },
    Ok,
    Error { message: String },
}
```

### Error Propagation Rules

| Layer | Convention |
|-------|-----------|
| Crate internal | `thiserror` typed `Error` enum, `?` propagation |
| Crate boundary | Upper crate converts lower errors via `#[from]` |
| Binary (ralph) | `anyhow` catch-all, format for user-facing display |
| `unwrap()`/`expect()` | **Only** for provably infallible cases (e.g., `Mutex::lock` on non-poisoned mutex), must include descriptive message |
| `panic!()` | **Forbidden** outside of tests |

### Async Patterns

| Area | Convention |
|------|-----------|
| Inter-component communication | `tokio::sync::mpsc` channels between daemon components |
| Shared state | `Arc<RwLock<T>>` for read-heavy, `Arc<Mutex<T>>` for write-heavy |
| Spawned tasks | All `tokio::spawn` must capture and handle `JoinHandle` — no fire-and-forget |
| Graceful shutdown | `tokio::sync::watch` channel to broadcast shutdown signal to all components |
| External I/O | All external I/O operations must use `tokio::time::timeout` |
| SQLite access | All `rusqlite` calls must be wrapped in `tokio::task::spawn_blocking` — rusqlite is synchronous and will block the async runtime if called directly |

### Logging Conventions

| Level | Usage |
|-------|-------|
| `error!` | User-actionable failures — exhausted healing, daemon errors |
| `warn!` | Self-healing activated, degraded state — not user-actionable yet |
| `info!` | State transitions — story assigned, worker spawned, step completed |
| `debug!` | Internal logic — config resolution, dependency analysis |
| `trace!` | Verbose — message parsing, socket I/O, SQL queries |

**Structured logging format:**
```rust
tracing::info!(story_id = %id, worker = %w, "story assigned");
tracing::warn!(story_id = %id, attempt = attempt, layer = "step_retry", "healing activated");
```

**Span naming:** Module path style
```rust
let _span = tracing::info_span!("pipeline::execute").entered();
let _span = tracing::info_span!("worker::spawn", worker_id = %id).entered();
```

**Security:** Never log story content, config secrets, or full file paths from user projects.

### Enforcement Guidelines

**All AI Agents MUST:**
1. Run `cargo clippy -- -D warnings` with zero warnings before completing any story
2. Run `cargo fmt --check` with zero formatting violations
3. Follow the error propagation rules — no `unwrap()` without justification, no `panic!()` outside tests
4. Use structured tracing fields for all log statements — no `format!()` string interpolation in log messages
5. Use typed Request/Response enums for all socket communication — no ad-hoc JSON construction

**Pattern Verification:**
- `cargo clippy` enforces Rust idioms and catches common anti-patterns
- `cargo test` runs all unit, integration, and E2E tests
- Code review checks socket protocol conformance and error handling patterns

### Anti-Patterns

**Avoid:**
- `String` error types — always use `thiserror` enums
- `.unwrap()` chains — propagate with `?` or provide context with `.context()` (anyhow)
- Unstructured logging — `info!("thing happened: {}", x)` → use `info!(field = %x, "thing happened")`
- Raw JSON construction for socket protocol — always serialize from typed structs
- `tokio::spawn` without storing/awaiting the `JoinHandle`
- Shared mutable state without explicit synchronization primitive

## Project Structure & Boundaries

### Complete Project Directory Structure

```
bmad-ralph/
├── Cargo.toml                          # Workspace manifest
├── Cargo.lock
├── ralph.toml.example                  # Example config for users
├── .gitignore
├── LICENSE
│
├── crates/
│   ├── ralph-common/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs                  # Re-exports
│   │       ├── error.rs                # Base error types
│   │       ├── models/
│   │       │   ├── mod.rs
│   │       │   ├── story.rs            # Story, StoryState, StoryResult
│   │       │   ├── worker.rs           # WorkerState, WorkerHealth
│   │       │   ├── pipeline.rs         # PipelineState, SprintPlan
│   │       │   └── healing.rs          # HealingAttempt, HealingLayer
│   │       ├── db/
│   │       │   ├── mod.rs
│   │       │   ├── schema.rs           # SQLite schema definitions
│   │       │   └── migrations.rs       # Schema migrations
│   │       └── protocol/
│   │           ├── mod.rs
│   │           ├── request.rs          # Socket Request enum (JSON)
│   │           └── response.rs         # Socket Response enum (JSON)
│   │
│   ├── ralph-config/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── config.rs              # RalphConfig struct, TOML deserialization
│   │       ├── resolve.rs             # Three-tier precedence resolution
│   │       └── defaults.rs            # Default config values
│   │
│   ├── ralph-worker/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── error.rs
│   │       ├── process.rs             # tokio::process child spawning/monitoring
│   │       ├── worktree.rs            # Git worktree create/destroy lifecycle
│   │       ├── health.rs              # Worker health checking
│   │       └── output.rs             # Worker stdout/stderr capture
│   │
│   ├── ralph-pipeline/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── error.rs
│   │       ├── state_machine.rs       # Pipeline state machine transitions
│   │       ├── scheduler.rs           # Story sequencing, dependency analysis
│   │       ├── executor.rs            # Story-to-worker assignment
│   │       ├── healing/
│   │       │   ├── mod.rs
│   │       │   ├── retry.rs           # Layer 1: step retry
│   │       │   ├── restart.rs         # Layer 2: worker restart
│   │       │   └── diagnose.rs        # Layer 3: diagnose flow
│   │       ├── artifact/
│   │       │   ├── mod.rs
│   │       │   ├── reader.rs          # BMAD artifact file reading
│   │       │   └── parser.rs          # YAML frontmatter parsing (serde_yaml_ng)
│   │       └── persistence.rs         # SQLite state read/write
│   │
│   └── ralph/
│       ├── Cargo.toml                 # [[bin]] name = "ralph"
│       └── src/
│           ├── main.rs                # Entry point, clap App definition
│           ├── commands/
│           │   ├── mod.rs
│           │   ├── daemon/
│           │   │   ├── start.rs       # ralph start
│           │   │   └── stop.rs        # ralph stop
│           │   ├── status.rs          # ralph status
│           │   ├── diagnose.rs        # ralph diagnose <id>
│           │   ├── retry.rs           # ralph retry <id>
│           │   ├── init.rs            # ralph init
│           │   └── watch.rs           # ralph watch (ratatui TUI)
│           ├── daemon/
│           │   ├── mod.rs
│           │   ├── server.rs          # Daemon event loop
│           │   ├── socket.rs          # Unix socket server
│           │   ├── signal.rs          # SIGTERM/SIGINT handling
│           │   ├── supervisor.rs      # Worker lifecycle supervision
│           │   └── logging.rs         # tracing-appender setup, daily rotation
│           ├── render/
│           │   ├── mod.rs
│           │   ├── border.rs          # ※ Section Border component
│           │   ├── health.rs          # Health Line component
│           │   ├── progress.rs        # Progress Bar component
│           │   ├── summary.rs         # Summary Line component
│           │   ├── table.rs           # Story Table + Worker Table
│           │   ├── timeline.rs        # Event Timeline component
│           │   ├── spinner.rs         # Spinner component
│           │   ├── hint.rs            # Hint Line component
│           │   ├── error.rs           # Error Message component
│           │   └── theme.rs           # Color semantics, NO_COLOR, width detection
│           ├── client.rs              # Unix socket client (status/stop/diagnose)
│           └── tui/
│               ├── mod.rs
│               ├── app.rs             # Ratatui app state
│               ├── ui.rs              # Ratatui widget layout
│               └── event.rs           # Keyboard event handling
│
├── tests/
│   ├── integration/
│   │   ├── daemon_lifecycle.rs        # Start/stop daemon integration
│   │   ├── pipeline_execution.rs      # Full pipeline flow
│   │   └── worker_isolation.rs        # Git worktree isolation verification
│   └── e2e/
│       ├── cli_start.rs               # assert_cmd: ralph start
│       ├── cli_status.rs              # assert_cmd: ralph status output
│       ├── cli_diagnose.rs            # assert_cmd: ralph diagnose output
│       └── cli_init.rs                # assert_cmd: ralph init behavior
│
├── target/                            # Build output (gitignored)
│   ├── debug/
│   │   └── ralph                      # Debug binary
│   └── release/
│       └── ralph                      # Release binary
│
└── .ralph/                            # Runtime directory (gitignored)
    ├── ralph.sock                     # Unix domain socket
    ├── ralph.pid                      # Daemon PID file
    ├── ralph.db                       # SQLite database (WAL mode)
    ├── ralph.db-wal                   # WAL file
    ├── ralph.db-shm                   # Shared memory file
    ├── logs/
    │   ├── ralph.2026-02-27.log       # Daily rotated logs
    │   └── ralph.2026-02-28.log
    └── worktrees/
        ├── worker-1/                  # Git worktree for W1
        ├── worker-2/                  # Git worktree for W2
        └── worker-3/                  # Git worktree for W3
```

### Cargo Workspace Configuration

```toml
# bmad-ralph/Cargo.toml
[workspace]
members = [
    "crates/ralph",
    "crates/ralph-common",
    "crates/ralph-config",
    "crates/ralph-worker",
    "crates/ralph-pipeline",
]
resolver = "2"

[workspace.dependencies]
tokio = { version = "1.49", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml_ng = "0.10"
toml = "0.9"
clap = { version = "4.5", features = ["derive"] }
thiserror = "2"
anyhow = "1"
tracing = "0.1"
tracing-subscriber = "0.3"
tracing-appender = "0.2"
rusqlite = { version = "0.38", features = ["bundled"] }
crossterm = "0.29"
indicatif = "0.18"
ratatui = "0.30"
serde_yaml_ng = "0.10"
```

### Architectural Boundaries

**Crate Boundary Rules:**

| Boundary | Rule |
|----------|------|
| ralph-common | **No** dependencies on other ralph crates. Pure types, models, protocol, schema. |
| ralph-config | Depends on ralph-common only. Owns config resolution logic. |
| ralph-worker | Depends on ralph-common. Owns process spawning and worktree lifecycle. Does NOT know about pipeline or healing. |
| ralph-pipeline | Depends on ralph-common + ralph-worker. Owns state machine, scheduling, healing. |
| ralph | Depends on all crates. Binary entry point — CLI, daemon, rendering, TUI. |

### Data Flow

```
BMAD Artifacts (files) → ralph-pipeline::artifact → Pipeline State Machine
                                                         ↓
                                                    ralph-worker (spawn Claude Code in worktree)
                                                         ↓
                                                    Worker stdout/stderr → Pipeline healing decisions
                                                         ↓
                                                    SQLite (state persistence)
                                                         ↓
                                          daemon (socket server) ←→ CLI commands (socket client)
                                                                         ↓
                                                                    Terminal output (render/)
```

### Command Structure

```
ralph start                 # Start daemon process
ralph stop                  # Stop daemon gracefully
ralph status                # Query pipeline state (top-level, most frequent)
ralph status --detail       # Expanded status with story table
ralph diagnose <id>         # Diagnostic report for failed story
ralph retry <id>            # Re-feed story into pipeline
ralph init                  # Initialize project setup
ralph watch                 # Live TUI monitoring dashboard
```

### FR Category → Structure Mapping

| FR Category | Primary Crate | Key Files |
|-------------|--------------|-----------|
| FR1-5 Planning Integration | ralph-pipeline | `artifact/reader.rs`, `artifact/parser.rs` |
| FR6-10 Setup & Config | ralph-config + ralph | `config.rs`, `resolve.rs`, `commands/init.rs` |
| FR11-15 Daemon Management | ralph | `daemon/server.rs`, `daemon/signal.rs`, `daemon/logging.rs` |
| FR16-19 Pipeline Orchestration | ralph-pipeline | `state_machine.rs`, `scheduler.rs`, `executor.rs` |
| FR20-24 Worker Management | ralph-worker | `process.rs`, `worktree.rs`, `health.rs` |
| FR25-28 Self-Healing | ralph-pipeline | `healing/retry.rs`, `healing/restart.rs`, `healing/diagnose.rs` |
| FR29-33 Status & Monitoring | ralph | `commands/status.rs`, `render/`, `client.rs` |
| FR34-37 Diagnostics | ralph + ralph-pipeline | `commands/diagnose.rs`, `render/timeline.rs` |
| FR38-40 Shell Integration | ralph | `main.rs` (clap shell completions) |

### Cross-Cutting Concerns → Location Mapping

| Concern | Location |
|---------|----------|
| State Persistence | ralph-common/src/db/ (schema), ralph-pipeline/src/persistence.rs (read/write) |
| Error Handling | Each crate's error.rs (thiserror), ralph main.rs (anyhow catch-all) |
| Logging | ralph/src/daemon/logging.rs (setup), all crates use tracing macros |
| Config Resolution | ralph-config (resolution logic), ralph/src/commands/ (CLI flag overrides) |
| Socket Protocol | ralph-common/src/protocol/ (types), ralph/src/daemon/socket.rs (server), ralph/src/client.rs (client) |
| Terminal Rendering | ralph/src/render/ (all output components), ralph/src/render/theme.rs (color/NO_COLOR) |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- All 14 crates in the stack are compatible — serde 1.x unifies serialization across JSON/YAML/TOML
- Tokio 1.49 + rusqlite 0.38 compatible via `spawn_blocking` pattern (documented in Async Patterns)
- Crossterm 0.29 is default backend for ratatui 0.30 — zero configuration needed
- Clap 4.5 derive + tokio async main coexist without conflict

**Pattern Consistency:**
- Error handling follows consistent thiserror→anyhow layering aligned with workspace crate boundaries
- Naming conventions follow idiomatic Rust (clippy/rustfmt enforced) with project-specific rules only where needed
- Async patterns (channels, shutdown, spawn_blocking) are consistent with tokio best practices
- Logging conventions align with tracing ecosystem patterns

**Structure Alignment:**
- 5-crate workspace mirrors architectural component boundaries exactly
- Dependency flow is unidirectional — no circular dependencies possible
- Socket protocol types in ralph-common shared between daemon (server) and CLI (client)
- Each FR category maps cleanly to one primary crate

### Requirements Coverage Validation ✅

**Functional Requirements:** 40/40 covered
- All 8 FR categories have explicit crate and file mapping
- No orphan FRs — every requirement traces to specific source files
- Cross-cutting FRs (config, error handling, logging) addressed via ralph-common and patterns

**Non-Functional Requirements:** 15/15 covered
- Reliability: SQLite WAL + atomic transactions + crash recovery
- Performance: Rust zero-cost abstractions + async runtime + <100MB RSS achievable
- Integration: Claude Code via tokio::process, BMAD via serde_yaml_ng, git via worktrees
- Concurrency: Worker isolation via git worktrees + direct child processes + no shared mutable state

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All crate versions verified via web search (February 2026)
- serde_yaml deprecated → replaced with serde_yaml_ng 0.10.x
- rusqlite sync nature → spawn_blocking pattern documented
- serde_json added for socket protocol

**Structure Completeness:**
- Complete directory tree with all files and their responsibilities
- Runtime directory (.ralph/) defined with socket, PID, DB, logs, worktrees
- Cargo workspace Cargo.toml with shared dependencies specified
- Build output (target/) and binary name (ralph) defined

**Pattern Completeness:**
- SQLite schema conventions prevent agent conflicts
- Socket protocol uses typed enums — no ad-hoc JSON possible
- Error propagation rules cover every layer (crate internal → boundary → binary)
- Async patterns cover all concurrency scenarios including SQLite access

### Gap Analysis Results

**Critical Gaps:** 0
**Important Gaps:** 0 (2 found and resolved during validation)
**Nice-to-Have Gaps:**
- CI/CD pipeline configuration — deferrable to implementation
- Cross-compilation targets for standalone binary — deferrable to implementation
- `ralph completions` subcommand for shell completion generation — minor, can be added during implementation

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (40 FRs, 15 NFRs, UX spec)
- [x] Scale and complexity assessed (Medium)
- [x] Technical constraints identified (Claude Code, TOML, standalone binary)
- [x] Cross-cutting concerns mapped (6 concerns)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions (8 decisions)
- [x] Technology stack fully specified (14 crates, all versions verified)
- [x] Integration patterns defined (Unix socket JSON, BMAD artifact reading, git worktrees)
- [x] Performance considerations addressed (async runtime, spawn_blocking, resource bounds)

**✅ Implementation Patterns**
- [x] Error type pattern established (thiserror Error per crate)
- [x] SQLite schema conventions defined
- [x] Socket protocol specified (typed JSON request/response)
- [x] Async patterns documented (channels, shutdown, spawn_blocking, timeouts)
- [x] Logging conventions established (levels, structured fields, spans)
- [x] Enforcement guidelines defined (clippy, fmt, code review)

**✅ Project Structure**
- [x] Complete directory structure with all files
- [x] Cargo workspace configuration specified
- [x] Crate boundary rules defined
- [x] Data flow documented
- [x] Command structure finalized
- [x] FR → structure mapping complete
- [x] Runtime directory structure defined

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Clean separation of concerns via 5-crate workspace with unidirectional dependencies
- Crash-safe state persistence (SQLite WAL) meets 72+ hour reliability requirement
- Worker isolation via git worktrees is a natural fit for cattle-model architecture
- Hybrid terminal output (static CLI + ratatui TUI) provides both core UX and live monitoring
- All crate versions verified current as of February 2026

**Areas for Future Enhancement:**
- Plugin system architecture (PRD Phase 2)
- Multi-LLM worker support beyond Claude Code (PRD Phase 3)
- JSON/structured output mode for scripting (PRD Phase 2)
- Git hook integration replacing polling (PRD Phase 2)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect crate boundary rules — no circular dependencies
- All SQLite access via `spawn_blocking`, all external I/O with timeouts
- Refer to this document for all architectural questions

**First Implementation Priority:**
1. `cargo new` workspace scaffold with 5 crates
2. ralph-common — shared types, error types, SQLite schema
3. ralph-config — TOML config resolution
4. Build outward from foundation crates

