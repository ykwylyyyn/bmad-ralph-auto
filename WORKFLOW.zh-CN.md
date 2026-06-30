# BMAD 工作流执行顺序

[English](WORKFLOW.md) | 中文

本文档按正确顺序编排 **BMM**（BMAD Method Manager）与 **TEA**（Test Engineering Agent）的 slash 命令，适用于配合 Ralph 进行自主 SDLC 交付。

> **重要**：每个 slash 命令应在**全新的 Claude Code 上下文窗口**中执行，避免步骤之间上下文污染。

---

## 阶段总览

```text
一次性规划（Phase 3 Solutioning）
    → 每 Sprint 一次（Phase 4 Sprint Setup）
        → 每个 Story 循环 9 步（Story Cycle）
            → 可选：Epic 结束回顾
```

| 阶段 | 频率 | 核心产出 |
|------|------|----------|
| Phase 3 方案设计 | 项目初始化一次 | PRD、架构、Epic/Story 清单、就绪检查、CI |
| Phase 4 Sprint 设置 | 每个 Sprint 一次 | `sprint-status.yaml` |
| Story Cycle | 每个 Story 重复 | Story 规格、测试、实现、评审、质量门禁 |
| Epic 回顾 | 每个 Epic 结束（可选） | 回顾报告 |

---

## Phase 3：方案设计（一次性）

项目启动时执行一次。

| # | 代码 | Slash 命令 | 必需 | 代理 | 说明 |
|---|------|-----------|------|------|------|
| 1 | CA | `/bmad-bmm-create-architecture` | **必需** | Winston（架构师） | 系统架构、技术选型、ADR |
| 2 | TD | `/bmad-tea-testarch-test-design` | 可选 | Murat（TEA） | 测试策略与风险矩阵 |
| 3 | CE | `/bmad-bmm-create-epics-and-stories` | **必需** | John（SM） | 拆分 Epic 与 Story |
| 4 | TF | `/bmad-tea-testarch-framework` | 可选 | Murat（TEA） | 测试框架脚手架 |
| 5 | IR | `/bmad-bmm-check-implementation-readiness` | **必需** | Winston（架构师） | 实现就绪检查（PASS/CONCERNS/FAIL） |
| 6 | CI | `/bmad-tea-testarch-ci` | 可选 | Murat（TEA） | CI/CD 质量流水线 |

**产物目录**：`_bmad-output/planning-artifacts/`

---

## Phase 4：Sprint 设置（每个 Sprint）

每个 Sprint 开始时执行一次。

| # | 代码 | Slash 命令 | 必需 | 代理 | 说明 |
|---|------|-----------|------|------|------|
| 1 | SP | `/bmad-bmm-sprint-planning` | **必需** | Bob（SM） | 生成 `sprint-status.yaml`，排定本 Sprint Story |

**关键产物**：

```text
_bmad-output/implementation-artifacts/
└── sprint-status.yaml    # Ralph start 时自动摄入
```

---

## Story Cycle（每个 Story 重复）

核心开发循环。**以下 9 步均为必需**（除非标注为可选）。每个 Story 完整走一遍。

### 步骤 1 — CS：创建 Story

```
/bmad-bmm-create-story
```

为 Story 生成完整实现规格（验收标准、技术上下文、依赖关系）。

**产物示例**：`_bmad-output/implementation-artifacts/1-1-user-model-and-schema.md`

### 步骤 2 — VS：校验 Story

```
/bmad-bmm-create-story
```

运行**同一命令**，在提示时选择 **Validate（校验）模式**（无独立 validate 命令）。

### 步骤 3 — AT：ATDD 验收测试

```
/bmad-tea-testarch-atdd
```

生成**失败状态**的验收测试（TDD 红灯阶段）。**必须在 dev-story 之前完成**。

**产物示例**：`_bmad-output/test-artifacts/atdd-checklist-1-1.md`

### 步骤 4 — DS：开发 Story

```
/bmad-bmm-dev-story
```

实现代码使测试通过（TDD 绿灯）。完成后运行：

```bash
make test-all    # 或项目对应的测试命令
```

### 步骤 5 — QA：QA 自动化

```
/bmad-bmm-qa-generate-e2e-tests
```

补充 ATDD 之外的边界与集成测试。

### 步骤 6 — CR：代码评审

```
/bmad-bmm-code-review
```

对抗式代码评审。若发现问题：

> **内循环**：CR 发现问题 → 回到 **步骤 4（DS）** 修复 → **跳过步骤 5（QA）** → 返回 **步骤 6（CR）**，直到通过。

### 步骤 7 — RV：测试评审

```
/bmad-tea-testarch-test-review
```

测试质量审计，产出 0–100 质量分。

### 步骤 8 — NR：NFR 评估

```
/bmad-tea-testarch-nfr
```

非功能需求评估：性能、安全、可靠性等。

### 步骤 9 — TR：可追溯性与门禁

```
/bmad-tea-testarch-trace
```

生成覆盖率追溯矩阵，做出质量门禁 **Pass/Fail** 决策。通过后 Story 才可标记为 **Done**。

---

## Epic 边界（可选）

每个 Epic 结束时：

| 代码 | Slash 命令 | 必需 | 代理 |
|------|-----------|------|------|
| ER | `/bmad-bmm-retrospective` | 可选 | Team |

---

## 随时可用工作流

开发过程中任意时刻可调用：

| 代码 | Slash 命令 | 用途 |
|------|-----------|------|
| SS | `/bmad-bmm-sprint-status` | 汇总 Sprint 状态与风险 |
| CC | `/bmad-bmm-correct-course` | Sprint 中途重大变更纠偏 |
| QS | `/bmad-bmm-quick-spec` | 小改动快速技术规格 |
| QD | `/bmad-bmm-quick-dev` | 快速实现 quick-spec |
| Help | `bmad-help` | 询问「下一步该做什么」 |

---

## 如何判断下一步

决策时**必须交叉参考两个来源**：

1. **Sprint 状态**（`sprint-status.yaml`）— 各 Story 是 `done`、`in-progress` 还是 `backlog`
2. **质量步骤产物** — 每个 Story 是否具备步骤 5–9 的产出文件

### 每个 Story 的预期产物

| 步骤 | 产物模式 | 示例 |
|------|----------|------|
| 3. AT | `atdd-checklist-{story}.md` | `atdd-checklist-1-1.md` |
| 5. QA | Story 的 E2E 测试报告/文件 | |
| 6. CR | Story 的代码评审报告 | |
| 7. RV | Story 的测试质量评分 | |
| 8. NR | Story 的 NFR 评估报告 | |
| 9. TR | Story 的追溯矩阵 / 门禁决策 | |

**规则**：若 `sprint-status.yaml` 中 Story 已标 `done`，但缺少步骤 5–9 任一产物，应从**第一个缺失步骤**继续，再开始新 Story。

### sprint-status.yaml 片段示例

```yaml
development_status:
  epic-1: in-progress
  1-1-user-model-and-schema: done
  1-2-user-registration-api: in-progress
  1-3-user-login-and-jwt: backlog
  epic-1-retrospective: optional
```

---

## 与 Ralph 的衔接

| 人工（Claude Code + BMAD） | 自主（Ralph daemon） |
|---------------------------|---------------------|
| 执行 slash 命令生成规划与 Story 规格 | `ralph start` 摄入 sprint plan |
| 编写/审查代码、跑质量门禁 | 并行调度 worker 在 worktree 中执行 Story |
| 更新 `sprint-status.yaml` 状态 | `ralph status` / `ralph watch` 监控进度 |
| Story 失败后人工修复 | `ralph diagnose` + `ralph retry` |

**Claude Code 配置要点**：

- **人工 BMAD 步骤**：在项目目录运行 `claude`，推荐 `--permission-mode auto` 或 `acceptEdits`
- **Ralph worker**：必须设置 `RALPH_CLAUDE_ARGS="--dangerously-skip-permissions"`（见 [README.zh-CN.md](README.zh-CN.md#claude-code-配置)）

```text
BMAD 规划与 Story 规格（人工 on-the-loop）
        │
        ▼
ralph start ──► 读取 sprint-status.yaml，调度可并行 Story
        │
        ▼
Worker 在隔离 worktree 中执行 dev-story
        │
        ▼
开发者监控 + 质量门禁（人工审批合并）
```

---

## 注意事项

1. **新上下文**：每个 slash 命令开新 Claude Code 窗口，避免幻觉与上下文串扰。
2. **校验模式**：步骤 2（VS）与步骤 1（CS）用同一命令，选择 Validate 模式。
3. **ATDD 先于开发**：步骤 3 必须在步骤 4 之前完成。
4. **CR 内循环**：评审返工只重跑 DS，不重跑 QA。
5. **门禁决策**：步骤 9（TR）是 Story 完成的最终质量门禁。
6. **产物位置**：Story 与测试产物在 `_bmad-output/implementation-artifacts/` 与 `_bmad-output/test-artifacts/`。

---

## 延伸阅读

- [README.zh-CN.md](README.zh-CN.md) — **完整示例：开发用户管理系统**
- [WORKFLOW.md](WORKFLOW.md) — English version
