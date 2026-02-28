# bmad-ralph 设计纲要

## 目的

解决一个核心问题：**用户产出 PRD 后，代码开发全自动完成**。

用户只需要用 BMAD 方法论产出 PRD，push 到 repo，后续的 sprint 规划、并行开发、代码合并、多轮 sprint 迭代全部自动化。用户只需要在最后 review 结果。

这不是一个 CI/CD 系统，而是一个**方法论驱动的自动化开发平台**。

---

## 三个核心概念

### 1. Workflow 是编排者

BMAD 和 Ralph 的本质都是 **workflow**（markdown 文件）。Workflow 定义了做什么、按什么顺序、什么条件下分支。

- BMAD workflow：驱动 Claude Code 产出 PRD / architecture / epics
- Ralph workflow：驱动 Claude Code 读取 PRD、开发 story、自检、提交

Claude Code 是**执行引擎**，加载 workflow 然后照着做。Workflow 才是真正的"智能"所在。

### 2. Daemon 是 Scrum Master

当需要多个 Ralph 并行工作时，需要一个协调者。但这个协调者**不决定做什么**（那是 BMAD workflow 通过 sprint planning 决定的），它负责**确保流程跑通**：

- 谁开发哪个 story（claim 防重复）
- 哪些 story 可以并行（冲突检测）
- 按什么顺序 merge（依赖管理）
- 失败了怎么办（自愈 / 通知）
- 下一个 sprint 什么时候开始（节奏推进）

类比 Scrum Master 的职责：排障、协调、守护流程、推进节奏。它不是 workflow 引擎，也不是 PM——**workflow 定义做什么，daemon 确保做得顺**。

### 3. Worker 是 cattle

每个 Ralph worker 是一个临时的 Claude Code session，运行在独立的 git worktree 中。Worker 是一次性的：
- 可以随时杀掉重启
- Worktree 就是 checkpoint（代码在磁盘上）
- 不需要保存内部状态
- 失败了就触发 correct-course workflow，再失败就通知用户

---

## 设计约束

### 自包含
- 不依赖外部 PM 工具（无 Linear、Jira、GitLab）
- 项目用 monorepo，PRD 和代码在同一个 repo
- 所有 planning artifacts（PRD、story spec、sprint status）都 git-tracked

### 工具与项目分离
- bmad-ralph 是泛化工具 repo，不含任何项目特定数据
- 项目通过 submodule 引用 bmad-ralph
- 项目配置（config、workflow 覆盖）在项目侧，不在工具侧

### 三级 overlay
- 资源查找顺序：项目覆盖 → bmad-ralph 自定义 → BMAD upstream 默认
- 允许项目自定义 workflow、agent 行为、配置，但不需要 fork 工具 repo

### 不污染 git 历史
- 协调状态（claim、进度、lock）不进 git，存在 daemon 的 SQLite 中（gitignored）
- Git 历史只包含有意义的 artifacts（PRD、story spec、代码）

### 多机支持
- Daemon 提供 HTTP API，不局限于单机
- Worker 可以在 daemon 同机或远程机器上运行

---

## 用户流程

```
你: BMAD → PRD → commit → merge → push
                                    │
Daemon (常驻): ◄──── git hook ──────┘
  │
  ├── Sprint Planning（全自动）
  │
  ├── 并行开发
  │   ├── Ralph-1 (worktree, 自愈)
  │   ├── Ralph-2 (worktree, 自愈)
  │   └── Ralph-3 → 自愈失败 → 通知你
  │
  ├── Merge main + push（按依赖序）
  │
  ├── Sprint N+1 → ... → epics 完成
  │
  └── 新 PRD push → 排队

你: 实时 dashboard / review 结果
```

### 关键决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Sprint 规划 | 全自动 | 减少人工干预，daemon spawn Claude Code 执行 planning workflow |
| Worker 失败 | 自愈优先 | 先跑 correct-course workflow，仍失败才通知用户 |
| 新 PRD 到达 | 排队 | 当前 pipeline 完成后再处理，避免状态混乱 |
| 协调状态存储 | SQLite (gitignored) | 不污染 git 历史 |
| 通信方式 | HTTP API | 原生支持多机部署 |
| Worker 模型 | Cattle（一次性） | worktree 是 checkpoint，worker 可随时重启 |
| 冲突检测 | 前置（sprint planning 阶段） | 用 merge-tree 模拟，冲突的 story 不并行 |

---

## 设计思路

### Workflow 内嵌 Scrum 调用

Scrum 不是独立的 layer，而是 **workflow 过程中的服务调用**。

```
❌ 错误理解：workflow → scrum layer → worker
✅ 正确理解：workflow 定义步骤，步骤中包含 scrum 调用（claim / progress / merge）
```

Workflow 里写："在开始开发前，调用 scrum claim 这个 story"。Scrum daemon 响应 claim 请求，返回是否允许。Workflow 根据结果决定下一步。

### Daemon 的双重角色

Daemon 既是 **pipeline 驱动者**（检测触发、spawn worker、管理生命周期），也是 **Scrum Master**（claim、merge queue、进度追踪、排障推进）。这两个角色合一是因为它们共享状态，分开会增加不必要的复杂度。注意它不做产品决策（做什么、优先级），那是 workflow 的事。

### bmad-ralph 提供三样东西

| 提供物 | 形式 | 谁用、怎么用 |
|--------|------|-------------|
| **方法论** | Workflow markdown | Claude Code 加载 workflow 执行 BMAD/Ralph 流程 |
| **协调服务** | Rust daemon（Scrum Master 角色） | Ralph worker 在 workflow 执行中调用 daemon（claim story、报告进度、请求 merge） |
| **脚手架** | 模板 + init 脚本 | 用户初始化新项目时一次性使用 |

### 命名

- **BMAD**：上游方法论框架（保留）
- **Ralph**：统一入口 CLI + 开发 worker 的代称（保留）
- **Daemon**：Scrum Master 角色，进程名待定
- **CLI 集成**：所有 scrum 功能作为 `ralph` 子命令（如 `ralph scrum status`）

---

## 待决事项

- [ ] Daemon 进程名（后续命名）
- [ ] Worker 与 daemon 的通信协议细节（MCP vs HTTP vs 混合）
- [ ] Dashboard 的具体形态（CLI TUI / Web / 两者都有）
