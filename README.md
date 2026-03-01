# Ralph

Autonomous SDLC pipeline runner — a Rust CLI daemon that orchestrates parallel Claude Code worker sessions to execute stories around the clock with self-healing capabilities.

Ralph pairs with [BMAD-METHOD](https://github.com/bmad-method) for planning, shifting delivery from human-in-the-loop to human-on-the-loop.

## How It Works

1. BMAD produces sprint plans with sequenced, dependency-mapped stories
2. Ralph daemon ingests the plan, analyzes parallelization opportunities
3. Concurrent Claude Code workers execute stories in isolated git worktrees
4. Three-layer self-healing (retry → restart → diagnose) handles failures automatically
5. Developer monitors progress via terminal dashboard and intervenes only when needed

## Architecture

5-crate Cargo workspace:

```
ralph (CLI binary)
├── ralph-pipeline   — State machine, story scheduling, self-healing
├── ralph-worker     — Process spawning, health monitoring, worktree isolation
├── ralph-config     — TOML config with three-tier precedence
└── ralph-common     — Shared error types, state models, SQLite schema
```

Key choices: SQLite + WAL for persistence, Unix Domain Socket IPC, tokio async runtime.

## CLI

```
ralph start      # Start daemon, begin processing sprint plan
ralph stop       # Graceful shutdown
ralph status     # Pipeline state, story progress, worker health
ralph watch      # Live terminal dashboard
ralph diagnose   # Diagnostic report for failed stories
ralph retry      # Re-feed corrected stories into pipeline
ralph init       # Initialize ralph on a project
```

## Development Status

**Early development** — project foundation in progress.

| Epic | Scope | Status |
|------|-------|--------|
| 1. Project Foundation & Developer Setup | Workspace scaffold, shared types, config system, init command | In Progress (1/5 stories done) |
| 2. Autonomous Story Execution | Daemon lifecycle, IPC, state persistence, pipeline engine, workers | Backlog |
| 3. Pipeline Monitoring & Status Display | Terminal rendering, status commands | Backlog |
| 4. Self-Healing & Error Recovery | Three-layer healing, diagnose/retry commands | Backlog |
| 5. Planning Integration | BMAD submodule integration, artifact handoff | Backlog |

### Completed

- Story 1-1: Cargo workspace scaffold & CLI entry point

## Build

```bash
cargo build --workspace
make test-all    # tests + clippy + fmt-check
```

Requires Rust 2024 edition (stable toolchain, pinned via `rust-toolchain.toml`).

## License

MIT
