# Ralph

Ralph is an autonomous SDLC pipeline runner — a Python CLI daemon that orchestrates parallel Claude Code workers to execute BMAD stories with self-healing.

Ralph pairs with [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) to shift delivery from human-in-the-loop to human-on-the-loop.

## Documentation

| Language | Guide |
|----------|-------|
| 中文 | [README.zh-CN.md](README.zh-CN.md) — 安装、配置、使用与开发 |
| English | [README.en.md](README.en.md) — Install, configure, use, and develop |

## Quick Start

```bash
pip install -e .
ralph init
# Run BMAD sprint planning → produces sprint-status.yaml
ralph start
ralph watch
```

See the language-specific README for full configuration, BMAD workflow integration, and development setup.

## License

MIT
