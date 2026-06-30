# Ralph

中文 | [English](README.en.md)

Ralph 是一个自主 SDLC 流水线运行器。它编排多个并行的 Claude Code worker 会话，在隔离的 git worktree 中执行 BMAD stories，并提供三层自愈能力。

Ralph 与 [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) 配合使用，把交付模式从 human-in-the-loop 转向 human-on-the-loop。

## 前置要求

| 依赖 | 版本 / 说明 |
|------|-------------|
| Python | 3.11+ |
| Node.js | 20.12+（`ralph init` 通过 `npx bmad-method install` 安装 BMAD） |
| Git | 用于 worktree 隔离 |
| Claude Code CLI | 默认命令为 `claude`，可通过环境变量覆盖 |
| Cargo（可选） | 仅在本仓库开发或运行遗留 Rust 测试时需要 |

## 安装

### 从源码安装（推荐用于开发）

```bash
git clone https://github.com/ykwylyyyn/bmad-ralph-auto.git
cd bmad-ralph-auto

# 可编辑安装
pip install -e .

# 或直接从源码运行（无需安装）
PYTHONPATH=src python -m ralph --help
```

### Shell 补全（可选）

```bash
ralph completions bash >> ~/.bashrc
# 或 zsh / fish
ralph completions zsh  >> ~/.zshrc
ralph completions fish >> ~/.config/fish/completions/ralph.fish
```

## 快速开始

以下流程适用于**任意目标项目**（不限于本仓库本身）。

### 1. 初始化项目

在目标项目根目录执行：

```bash
cd /path/to/your-project
ralph init
```

`ralph init` 会创建：

```text
your-project/
├── ralph.toml                          # 项目级配置
├── .ralph/                             # 运行时目录（daemon、数据库、worktree）
│   ├── logs/
│   └── worktrees/
├── _bmad/                              # BMAD 安装目录（由 npx bmad-method install 生成）
├── _bmad-output/
│   ├── planning-artifacts/             # PRD、架构、Epic 等规划产物
│   └── implementation-artifacts/       # sprint-status.yaml、story 文件
├── .claude/skills/                     # BMAD v6+ skills（如 bmad-sprint-planning）
└── .ralph/bmad-pin.json                # BMAD 安装版本记录
```

`ralph init` 会自动运行 `npx bmad-method install` 安装 BMM + TEA 模块。需要已安装 Node.js 20+。

若之前误用 git submodule 安装了 BMAD 源码仓库（会出现 `required planning workflow layout is missing`），重新执行：

```bash
npx --yes bmad-method install --directory . --modules bmm,tea --tools claude-code --yes
```

或再次运行 `ralph init`（会自动尝试修复）。

### 2. 使用 BMAD 生成 Sprint Plan

在 Claude Code 中按 [WORKFLOW.md](WORKFLOW.md) 执行 BMAD 工作流。每个 sprint 至少需要：

1. **Sprint Planning**（`/bmad-bmm-sprint-planning`）— 生成 `sprint-status.yaml`
2. **Create Story**（`/bmad-bmm-create-story`）— 为每个 story 生成实现规格

关键产物路径：

```text
_bmad-output/implementation-artifacts/
├── sprint-status.yaml          # Ralph 启动时自动摄入
├── 1-1-example-story.md        # 各 story 的规格文件
└── ...
```

`sprint-status.yaml` 中需包含 `development_status` 映射，以及可选的 `story_location` 字段。

### 3. 配置 Claude Code

确保 `claude` 命令在 PATH 中可用，或设置环境变量：

```bash
export RALPH_CLAUDE_BIN=/path/to/claude
```

### 4. 启动流水线

```bash
ralph start
```

`ralph start` 会：

1. 确保项目目录与 `.ralph/` 运行时存在
2. 解析并摄入 `_bmad-output/implementation-artifacts/sprint-status.yaml`
3. 将 stories 与依赖写入 SQLite（`.ralph/ralph.db`）
4. 启动后台 daemon，按依赖关系并行调度 worker

### 5. 监控与干预

```bash
ralph status              # 快照：健康状态、sprint 进度
ralph status --detail     # 附加 story / worker 明细表
ralph watch               # 实时终端 dashboard（默认 2 秒刷新）
ralph watch --detail --refresh 5
ralph diagnose [STORY_ID] # 失败 story 的诊断报告
ralph retry STORY_ID      # 将修正后的 story 重新送入流水线
ralph stop                # 优雅停止 daemon
```

## 配置说明

Ralph 采用**三层配置优先级**（高到低）：

```text
CLI 参数  >  项目 ralph.toml  >  用户 ~/.config/ralph/ralph.toml  >  内置默认值
```

### 项目配置 `ralph.toml`

`ralph init` 生成的示例：

```toml
max_workers = 5
retry_limit = 3
```

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `max_workers` | `5` | 并行 worker 上限 |
| `retry_limit` | `3` | 自愈 Layer 1：单步失败的最大重试次数 |

使用 `--force` 可覆盖已有配置：

```bash
ralph init --force --project-dir .
```

### 用户级配置

```bash
mkdir -p ~/.config/ralph
cat > ~/.config/ralph/ralph.toml <<'EOF'
max_workers = 3
EOF
```

用户配置作为全局默认值；项目 `ralph.toml` 会覆盖同名字段。

### CLI 覆盖项

所有子命令均支持以下全局参数：

```bash
ralph --config /path/to/custom.toml \
      --user-config ~/.config/ralph/ralph.toml \
      --max-workers 8 \
      --project-dir /path/to/project \
      start
```

| 参数 | 说明 |
|------|------|
| `--project-dir` | 目标项目根目录（默认当前目录） |
| `--config` | 项目配置文件路径 |
| `--user-config` | 用户配置文件路径 |
| `--max-workers` | 覆盖 `max_workers` |
| `--no-color` | 禁用 ANSI 颜色 |
| `-q` / `--quiet` | 减少非必要输出 |
| `-v` / `--verbose` | 显示更多细节 |

### 环境变量

| 变量 | 说明 |
|------|------|
| `RALPH_CLAUDE_BIN` | Claude Code 可执行文件路径（默认 `claude`） |
| `RALPH_BMAD_MODULES` | BMAD 安装模块列表（默认 `bmm,tea`） |
| `RALPH_BMAD_TOOLS` | BMAD 目标 IDE 工具（默认 `claude-code`） |
| `RALPH_BMAD_NPM_PACKAGE` | npm 包名（默认 `bmad-method`） |
| `RALPH_BMAD_INSTALL_CHANNEL` | 设为 `next` 使用 `@next` 预发布版 |
| `RALPH_BMAD_SUBMODULE_URL` | 仅测试/高级：用 git submodule 代替 npx 安装 |
| `NO_COLOR` | 设置任意非空值时禁用颜色输出 |

## 工作方式

```text
BMAD Sprint Plan
       │
       ▼
ralph start ──► 摄入 sprint-status.yaml + story 文件
       │
       ▼
Daemon 调度器 ──► 依赖感知并行分配（受 max_workers 限制）
       │
       ▼
Worker（git worktree 隔离）──► Claude Code 执行 story
       │
       ├── Layer 1: 步骤重试（retry_limit）
       ├── Layer 2: Worker 重启（新 worktree）
       └── Layer 3: Diagnose 升级（标记 failed，生成报告）
       │
       ▼
ralph status / watch ──► 开发者监控（human-on-the-loop）
```

## 项目目录结构

### 目标项目（使用 Ralph 的项目）

```text
.
├── ralph.toml
├── .ralph/
│   ├── ralph.db            # SQLite 状态（WAL 模式）
│   ├── ralph.pid
│   ├── daemon.json
│   ├── ralph.sock          # Unix socket IPC（或 loopback 回退）
│   ├── logs/               # Worker 输出日志
│   └── worktrees/          # 隔离的 git worktree
├── _bmad/                  # BMAD-METHOD submodule
└── _bmad-output/
    ├── planning-artifacts/
    └── implementation-artifacts/
        ├── sprint-status.yaml
        └── *.md            # Story 规格文件
```

### 本仓库（Ralph 源码）

```text
src/ralph/
├── cli.py              # CLI 入口（7 个子命令）
├── config/             # TOML 配置解析
├── daemon/             # 进程生命周期与 IPC
├── pipeline/           # 状态机、调度、artifact 摄入
├── worker/             # Claude 进程与 worktree 隔离
├── status/ / render/   # 终端渲染与状态快照
├── diagnose/ / retry/  # 自愈 Layer 3 与手动重试
├── planning/           # BMAD submodule 集成
└── watch/              # 实时 dashboard

tests_python/           # Python 单元与集成测试
scripts/ci-local.sh     # 本地复现 CI
.github/workflows/ci.yml
```

迁移期间，遗留 Rust workspace（`crates/`）仍保留在仓库中作为参考。

## 在本仓库开发

### 克隆与依赖

```bash
git clone https://github.com/ykwylyyyn/bmad-ralph-auto.git
cd bmad-ralph-auto
pip install -e ".[dev]" 2>/dev/null || pip install -e .
```

### 运行测试

```bash
# Python 测试（151 项）
make test-all

# 本地复现完整 CI（Python + Rust）
./scripts/ci-local.sh

# 仅 Rust（迁移期）
make rust-test
make rust-clippy
make rust-fmt-check
```

### 开发工作流

1. 阅读 [WORKFLOW.md](WORKFLOW.md) 了解 BMAD + TEA 步骤顺序
2. 查看 `_bmad-output/implementation-artifacts/sprint-status.yaml` 确认当前 sprint 进度
3. 创建功能分支：`git checkout -b cursor/<name>-a391`
4. 实现 story，运行 `make test-all` 确认通过
5. 推送并创建 PR；CI 会在 `main` 上自动运行 Python + Rust 质量门禁

### 常用开发命令

```bash
# 直接运行 CLI
PYTHONPATH=src python -m ralph --help
PYTHONPATH=src python -m ralph init --project-dir /tmp/ralph-demo

# 清理 Python 缓存
make clean

# 格式化 Rust 代码
make rust-fmt
```

## CLI 参考

```bash
ralph start      # 启动 daemon，摄入 sprint plan 并开始调度
ralph stop       # 优雅停止
ralph status     # 流水线状态、story 进度、worker 健康
ralph watch      # 实时终端 dashboard
ralph diagnose   # 失败 story 诊断报告
ralph retry      # 将修正后的 story 重新送入流水线
ralph init       # 初始化项目（配置 + BMAD + 目录结构）
ralph completions bash|zsh|fish
```

## 故障排查

| 现象 | 处理 |
|------|------|
| `No sprint plan found` | 先运行 BMAD sprint planning，确保 `_bmad-output/implementation-artifacts/sprint-status.yaml` 存在 |
| `claude: command not found` | 安装 Claude Code CLI 或设置 `RALPH_CLAUDE_BIN` |
| BMAD 布局校验失败 | 勿将 BMAD-METHOD 源码仓库作为 submodule 放入 `_bmad/`；运行 `npx bmad-method install --directory . --modules bmm,tea --tools claude-code --yes` |
| `npm error Invalid or unexpected token` | 多为 Windows 上 Node/npm 安装损坏（常见于旧版 nvm-windows）。重装 [Node 20 LTS](https://nodejs.org)，或升级 nvm-windows 至 1.1.11+ 后以**管理员** PowerShell 执行 `nvm uninstall <版本>` 再 `nvm install <版本>`；用 `node -v`、`npm -v` 验证后再 `ralph init` |
| 缺少 Node.js | 安装 Node 20+ 后重新 `ralph init` |
| Daemon 已在运行 | 使用 `ralph stop` 后再 `ralph start` |
| Story 失败 | `ralph diagnose <ID>` 查看报告，修复后 `ralph retry <ID>` |

## 相关文档

- [WORKFLOW.md](WORKFLOW.md) — BMAD + TEA 工作流执行顺序
- [CLAUDE.md](CLAUDE.md) — 架构与编码约定（面向 AI 协作者）
- `_bmad-output/planning-artifacts/` — PRD、架构、Epic 规划产物

## 许可证

MIT
