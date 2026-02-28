# bmad-ralph

泛化工具平台 repo，包含 BMAD framework + Ralph pipeline + workflows + commands。

## 约定

- 所有路径使用环境变量（`$WORKSPACE_ROOT`、`$TOOLS_ROOT`、`$PROJECT_DIR`），不硬编码项目路径
- 不包含任何项目特定数据
- `_bmad/` 是 submodule，通过 `git submodule update --remote _bmad` 升级
