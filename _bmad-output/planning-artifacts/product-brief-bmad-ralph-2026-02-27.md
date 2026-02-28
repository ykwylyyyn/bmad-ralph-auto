---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "user-provided project overview (conversation input)"
  - "https://github.com/bmad-code-org/BMAD-METHOD"
  - "https://ghuntley.com/loop/"
date: 2026-02-27
author: Deadlock
---

# Product Brief: bmad-ralph

## Executive Summary

bmad-ralph is a generalized SDLC framework and CLI tool that combines two core paradigms: **BMAD-METHOD** for high-quality, human-AI collaborative planning, and **Ralph** for autonomous parallel delivery. It enables independent developers and small teams to shift from **human-in-the-loop** to **human-on-the-loop** — spend hours crafting comprehensive plans, then let agents work 24/7 delivering stories autonomously with self-healing, auto-retry, and parallel execution capabilities.

The framework is self-contained, project-agnostic, and designed to be picked up and applied to any project instantly.

---

## Core Vision

### Problem Statement

Current AI development tools operate in a **one-shot, task-based paradigm** — they assist with individual coding tasks but stop when done. They do not autonomously pick up the next story, manage sprints, or maintain continuous delivery momentum. Independent developers and small teams remain bottlenecked by their own availability, unable to compete with larger teams on throughput.

### Problem Impact

- Developers are still **human-in-the-loop**: every task requires manual initiation, review, and handoff to the next
- Small teams cannot achieve 24/7 development velocity — work stops when people stop
- Poor or insufficient planning leads to low-quality automated output, causing rework that negates productivity gains
- Existing tools are either **too manual** (Cursor/Copilot) requiring constant guidance, or lack the **planning depth** needed for reliable autonomous execution

### Why Existing Solutions Fall Short

Existing AI coding tools address only half the equation:
- **AI-assisted editors** (Cursor, Copilot) boost individual task speed but remain firmly human-in-the-loop — they don't drive continuous delivery
- **Autonomous agents** lack structured, high-quality planning input, resulting in unreliable output that requires heavy human intervention
- **No existing solution bridges the gap** between comprehensive planning and sustained autonomous execution across an entire sprint of stories

### Proposed Solution

bmad-ralph is a standalone CLI tool that provides a complete SDLC pipeline:

1. **Planning Phase (BMAD):** Human collaborates with specialized AI agents to produce comprehensive PRD, architecture, UX design, epics, and stories — ensuring the planning quality that autonomous execution demands
2. **Delivery Phase (Ralph):** Agents autonomously execute stories 24/7 in parallel, with cattle-model workers that support auto-retry and self-healing — no human initiation needed between tasks
3. **Generalized Framework:** Contains no business logic; applicable to any project as a drop-in CLI tool with personal workflow preferences built in
4. **Plugin Extensibility:** Self-contained by default with zero external dependencies; optional plugins for external tool integration

### Key Differentiators

- **Planning-to-Execution Pipeline:** The unique combination of BMAD's high-quality collaborative planning with Ralph's autonomous parallel delivery — planning quality directly elevates execution reliability
- **24/7 Autonomous Sprint Execution:** Not just task completion, but continuous story-level delivery with project management built in
- **Timing Advantage:** LLM capabilities have just reached the threshold for reliable story-level autonomous execution, making this approach viable now
- **Self-Contained & Portable:** Zero-dependency CLI tool that works on any project out of the box
- **Cattle Workers:** Stateless, replaceable execution workers enabling true parallelization and horizontal scaling

## Target Users

### Primary Users

**Persona 1: Solo Full-Stack Developer — "Alex"**

Alex is a full-stack developer with multiple side projects. During the day he has a full-time job, and at night he wants his ideas to keep moving forward. He spends 1-2 hours in the evening collaborating with BMAD to plan features, write PRDs, and break down stories. Then he kicks off Ralph and goes to sleep — waking up to find stories implemented, tests passing, and PRs ready for his morning review.

- **Motivation:** Ship side projects without sacrificing sleep or sanity
- **Current Pain:** AI tools help him code faster, but he still has to manually start each task, review, and move to the next — work stops when he stops
- **Success Vision:** Wake up to meaningful progress every morning; his projects move at 24/7 velocity while he only invests focused planning time

**Persona 2: Small Team Tech Lead — "Sam"**

Sam leads a 5-10 person team building a product. The team collaborates on planning — PM provides requirements, UI designer contributes design specs, and Sam synthesizes everything through BMAD to produce high-quality planning artifacts. Once the sprint is planned and stories are ready, Sam starts Ralph and the team shifts to reviewing delivered output rather than writing code line by line.

- **Motivation:** Multiply team output without multiplying headcount
- **Current Pain:** Team spends more time on implementation mechanics than on product thinking and quality review
- **Success Vision:** Team focuses on planning, design, and review — the autonomous delivery pipeline handles the execution grunt work

### Secondary Users

**Non-Technical Stakeholders (Product Managers, UI Designers)**

These users participate exclusively in the BMAD planning phase — contributing domain expertise, product requirements, and design specifications. They do not interact with Ralph directly. Their review feedback on delivered output gets transformed into new stories that feed back into the delivery pipeline.

- **Interaction Model:** Collaborate during planning → review delivered output → feedback becomes new stories
- **Value Received:** Their input directly shapes what gets autonomously delivered, without needing to understand the technical execution

### User Journey

1. **Discovery:** Developer finds bmad-ralph through GitHub or community recommendation while looking for ways to automate their development workflow
2. **Onboarding:** Install CLI tool, run setup on an existing or new project — ready to use in minutes
3. **Planning Session:** Spend 1-2 hours collaborating with BMAD agents to produce PRD, architecture, epics, and stories
4. **Launch & AFK:** Start Ralph, walk away — agents work 24/7 executing stories in parallel
5. **Morning Review:** Come back to find implemented stories, review PRs, provide feedback
6. **Feedback Loop:** Review comments and change requests become new stories → fed back into Ralph → continuous delivery cycle

## Success Metrics

**User Success Metrics:**

- **Story Completion Rate:** Final success rate >99% (including auto-retry and self-healing cycles) — the core indicator that autonomous delivery is reliable
- **Autonomous Runtime:** Ralph sustains continuous unattended execution for multiple days without requiring human intervention
- **AFK Confidence:** Users can start Ralph and walk away with confidence that work is progressing — measured by the ratio of stories completed autonomously vs. stories requiring manual intervention

**Team Success Metrics:**

- **Throughput Multiplier:** Small teams (5-10 people) achieve significant output increase by shifting from manual implementation to planning + autonomous delivery
- **Human Focus Shift:** Team time spent on implementation mechanics decreases; time spent on planning, design, and review increases proportionally

### Business Objectives

As a personal open-source project, business objectives focus on utility and reliability rather than commercial metrics:

- **Framework Reliability:** Ralph pipeline runs stably for days without crashes or degraded performance
- **Generalizability:** Successfully applied across multiple unrelated projects without project-specific customization
- **Self-Contained Operation:** Zero external dependency failures — the framework operates independently out of the box

### Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Story final success rate | >99% | Stories completed (with retries) / total stories attempted |
| Continuous autonomous runtime | Days | Duration of unattended Ralph execution without human intervention |
| Pipeline stability | Days without crash | Longest uninterrupted Ralph session |
| First-attempt story success rate | Tracked (no target) | Stories completed on first attempt / total — indicator of planning quality |
| Time-to-productive | Minutes | Time from CLI install to first Ralph execution on a new project |

## MVP Scope

### Core Features

**1. Ralph Daemon**
- Long-running daemon process, polling-based task detection (MVP does not use git hooks)
- Detects new sprint plans / stories that need execution
- Manages worker lifecycle — spawn, monitor, kill, restart (cattle principle)

**2. Pipeline State Machine**
- Entire pipeline is a single state machine driving the SDLC workflow
- Reads BMAD-produced sprint plans and stories as input
- Determines step sequencing, parallelization opportunities, and dependencies
- Tracks state transitions and execution progress persistently

**3. Parallel Worker Execution**
- Spawns multiple Claude Code session workers based on concurrency analysis
- Workers are cattle — stateless, replaceable, horizontally scalable
- Each worker executes an assigned story or task independently

**4. Multi-Layer Self-Healing**
- **Layer 1 — Step Retry:** Individual pipeline steps can be retried on failure
- **Layer 2 — Worker Restart:** Failed workers are killed and restarted with fresh state (cattle principle)
- **Layer 3 — Diagnose Flow:** When retries cannot resolve an issue, a dedicated diagnose process is triggered to analyze the failure, attempt self-repair, and resume execution — key to sustained autonomous stability

**5. CLI Interface**
- Commands to start/stop daemon, check status, and manage pipeline execution
- Self-contained operation with zero external dependencies

### Out of Scope for MVP

- **Git hook integration** — daemon uses polling instead; git hook triggering is future enhancement
- **Plugin system** — external tool integration architecture deferred to post-MVP
- **Large team features** — advanced access control, multi-repo orchestration, enterprise-grade features
- **Non-Claude worker support** — MVP workers are Claude Code sessions only

### MVP Success Criteria

- Ralph daemon runs continuously for days without crashes
- Pipeline state machine correctly orchestrates multi-story sprint execution
- Workers execute stories in parallel with >99% final success rate (including self-healing)
- All three self-healing layers function correctly — retry, restart, and diagnose
- Framework successfully applied to at least one real project end-to-end

### Future Vision

- **Git hook triggering** — daemon reacts to git events for instant pipeline activation
- **Plugin ecosystem** — optional integrations with external tools (Jira, Slack, GitHub Actions, etc.)
- **Advanced diagnostics** — richer failure analysis, learning from past failures to improve future execution
- **Multi-LLM worker support** — workers beyond Claude Code (other agents, specialized models)
- **Large team features** — role-based access, multi-repo orchestration, audit trails
- **Community marketplace** — shared workflow templates, pipeline configurations, and plugins
