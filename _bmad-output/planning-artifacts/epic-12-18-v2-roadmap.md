---
title: Epic 12–18 — Agent OS v2 Engineering Roadmap
status: in-progress
created: 2026-06-30
based_on: user-v2-refactor-checklist
---

# Epic 12–18：工程级改造路线图（v2）

## 现状 vs 目标

| 维度 | 当前（Epic 8–11 后） | v2 目标 |
|------|---------------------|---------|
| 编排 | BMAD 手动 + Ralph 执行（串联） | 统一 Orchestrator（Plan→Execute→Review→Re-plan） |
| 任务图 | Story DAG + 并行 worker（已有） | 增强：回滚分支、epic 级分组 |
| 状态 | SQLite + sprint-status.yaml（已有） | + sprint 级跨 story memory |
| 验证 | Verifier 门禁（opt-in） | + architecture enforcement |
| 模型 | Router 按阶段选后端（opt-in） | + fallback chain + cost-aware |
| 失败处理 | Layer 1–3 自愈（已有） | + failure taxonomy 分类路由 |
| 集成 | CLI + Unix socket IPC | + REST API + plugin hooks |
| 交付 | worktree 分支隔离 | + commit/PR 策略 |

## 改造清单映射（20 项）

| # | 改造点 | 现状 | Epic |
|---|--------|------|------|
| 1 | 统一 Orchestrator | PARTIAL | 12 |
| 2 | Task Graph / DAG | EXISTS | 12（增强） |
| 3 | SQLite 状态 | EXISTS | — |
| 4 | BMAD feedback loop | PARTIAL | 13 |
| 5 | Story sizing engine | MISSING | 17 |
| 6 | Architecture enforcement | MISSING | 15 |
| 7 | 跨 story execution memory | PARTIAL | 16 |
| 8 | Failure classification | PARTIAL | 17 |
| 9 | Test-driven gate | EXISTS (opt-in) | — |
| 10 | Commit strategy | MISSING | 14 |
| 11 | Model router | EXISTS (opt-in) | 17 |
| 12 | Cost-aware scheduling | PARTIAL | 17 |
| 13 | Fallback chain | PARTIAL | 17 |
| 14 | 并行 worker | EXISTS | — |
| 15 | Checkpoint/resume | PARTIAL | 16 |
| 16 | Prompt isolation | EXISTS | — |
| 17 | Observability | PARTIAL | 18 |
| 18 | UI / dashboard | PARTIAL (terminal) | 18 |
| 19 | REST API | MISSING | 18 |
| 20 | Plugin system | MISSING | 18 |

## 实施顺序（Top 5 优先）

1. **Epic 12** — Unified Orchestrator（`orchestrator/controller.py`）
2. **Epic 16** — Sprint-level Execution Memory（`memory/sprint_store.py`）
3. **Epic 17** — Failure Taxonomy + Router Fallback（`failure/taxonomy.py`, `router/fallback.py`）
4. **Epic 18** — REST API（`api/server.py`）
5. **Epic 13–15** — Feedback loop、Git delivery、Architecture gate

---

## Epic 12：Unified Orchestrator

**目标**：BMAD 与 Ralph 统一调度，闭环 `Plan → Execute → Review → Re-plan`。

| Story | 范围 | 状态 |
|-------|------|------|
| 12.1 | `UnifiedOrchestrator` 封装 `PipelineEngine` + flow phase | **done (M5)** |
| 12.2 | BMAD 质量门禁 artifact 检查（QA/CR/RV/NR/TR） | backlog |
| 12.3 | 自动 `IN_REVIEW → DONE` 当全部 gate 通过 | backlog |
| 12.4 | 扩展 `story_cycle` 映射 BMAD WORKFLOW 全步骤 | backlog |

## Epic 13：BMAD Feedback Loop

| Story | 范围 | 状态 |
|-------|------|------|
| 13.1 | 监视 `_bmad-output/` CR/review artifact 变更 | **stub (M5)** |
| 13.2 | 解析 review → 更新 story spec / spawn follow-up | backlog |
| 13.3 | 检测到修正 spec 后自动 retry | backlog |

## Epic 14：Git Commit & Delivery

| Story | 范围 | 状态 |
|-------|------|------|
| 14.1 | `[git]` 配置：auto-commit、message template | backlog |
| 14.2 | verify 通过后 worktree 内 commit | backlog |
| 14.3 | PR 创建策略 | backlog |

## Epic 15：Architecture Enforcement

| Story | 范围 | 状态 |
|-------|------|------|
| 15.1 | 解析 `architecture.md` → 可执行规则 | backlog |
| 15.2 | pre-DONE gate：crate 边界、命名、禁止模式 | backlog |

## Epic 16：Cross-Story Execution Memory

| Story | 范围 | 状态 |
|-------|------|------|
| 16.1 | `SprintMemoryStore`（`sprint_memory` 表） | **done (M5)** |
| 16.2 | 注入已完成 story 的 API/module 摘要到 dev prompt | backlog |
| 16.3 | 从 `healing_attempts` 构建 failure pattern index | backlog |

## Epic 17：Smart Scheduling & Resilience

| Story | 范围 | 状态 |
|-------|------|------|
| 17.1 | Cost-aware scheduler | backlog |
| 17.2 | Backend fallback chain on runtime failure | **done (M5)** |
| 17.3 | Formal failure taxonomy + routing policies | **done (M5)** |
| 17.4 | Story sizing heuristics | backlog |

## Epic 18：External Integration

| Story | 范围 | 状态 |
|-------|------|------|
| 18.1 | HTTP REST API（/status, /stories, /retry） | **done (M5)** |
| 18.2 | Web dashboard | backlog |
| 18.3 | Structured observability (OpenTelemetry) | backlog |
| 18.4 | Plugin registry (pre-spawn, post-verify hooks) | backlog |

---

## M5 已落地模块（本次）

```text
src/ralph/
├── orchestrator/
│   ├── config.py          # [orchestrator] 配置
│   ├── controller.py      # UnifiedOrchestrator
│   └── feedback.py        # BMAD artifact 反馈监视 stub
├── failure/
│   └── taxonomy.py        # FailureCategory + classify_failure()
├── memory/
│   └── sprint_store.py    # SprintMemoryStore（跨 story）
├── router/
│   └── fallback.py        # FallbackChain + select_with_fallback()
└── api/
    ├── handlers.py        # REST 路由处理
    └── server.py          # stdlib HTTP server
```

配置示例：

```toml
[orchestrator]
enabled = true
feedback_loop = true
auto_done = false

[api]
enabled = true
host = "127.0.0.1"
port = 8765

[router]
default = "claude"
fallback.dev = ["gpt", "deepseek"]  # Claude fail → GPT → DeepSeek
```
