# Ralph

中文 | [English](README.en.md)

Ralph 是一个自主 SDLC 流水线运行器，目前正在迁移为 Python CLI 守护进程。它用于编排多个并行的 Claude Code worker 会话，执行 BMAD stories，并提供自愈能力。

Ralph 与 [BMAD-METHOD](https://github.com/bmad-method) 配合使用，把交付模式从 human-in-the-loop 转向 human-on-the-loop。

## 工作方式

1. BMAD 生成带有顺序和依赖关系的 sprint plan。
2. Ralph 守护进程读取计划，并分析可并行执行的机会。
3. 多个 Claude Code worker 在隔离的 git worktree 中并发执行 stories。
4. 三层自愈机制处理 step retry、worker restart 和 diagnose 升级。
5. 开发者通过终端状态和 dashboard 命令监控进度。

## 架构

Python 包结构保留了原 Rust 方案中的边界上下文：

```text
src/ralph/cli.py          # CLI 入口
src/ralph/pipeline/       # 状态机和调度契约
src/ralph/worker/         # Claude 进程启动和输出解析
src/ralph/config/         # TOML 配置加载
src/ralph/common/         # 共享模型、协议类型、SQLite schema
```

关键选择：SQLite + WAL 用于持久化，JSON request/response 类型用于协议结构，`asyncio` 用于进程管理。

迁移期间，旧 Rust workspace 仍保留在仓库中作为参考。

## CLI

```bash
ralph start      # 启动 daemon，开始处理 sprint plan
ralph stop       # 优雅停止
ralph status     # 查看流水线状态、story 进度和 worker 健康状态
ralph watch      # 实时终端 dashboard
ralph diagnose   # 为失败 story 生成诊断报告
ralph retry      # 将修正后的 story 重新送回流水线
ralph init       # 在项目中初始化 Ralph
ralph completions bash|zsh|fish
```

当前 Python CLI 已包含配置解析、项目初始化、shell completion 生成，以及 daemon/runtime 命令的可运行 stub。

## 开发状态

**早期开发阶段** - Python 迁移基础已建立。

### 已完成

- Python 包脚手架和 `ralph` CLI 入口
- 共享领域模型、协议 DTO 和 SQLite schema
- 从 TOML 加载配置
- Claude 进程抽象和输出解析器
- 覆盖 CLI、配置、common 模型/schema、worker 输出解析的 Python 回归测试
- 三层配置优先级：CLI 覆盖项、项目 TOML、用户 TOML、默认值
- `ralph init` 项目脚手架和 `ralph completions` 生成

## 构建与测试

```bash
python -m ralph --help
make test-all
```

需要 Python 3.11 或更高版本。未安装包、直接从源码目录运行时，可使用 `PYTHONPATH=src python -m ralph --help`。

迁移期间，如果本机安装了 Cargo，也可以运行旧 Rust 目标：

```bash
make rust-test
```

## 许可证

MIT
