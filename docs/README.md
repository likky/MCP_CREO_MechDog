# 文档目录与维护规范

## 1. 核心入口文档（常青维护）

| 文档 | 用途 |
| :--- | :--- |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发者入口与当前开发边界 |
| [BACKLOG.md](BACKLOG.md) / [BACKLOG_COMPLETED.md](BACKLOG_COMPLETED.md) | 唯一活跃工作台账 / 已完成台账归档 |
| [INSTALL.md](INSTALL.md) | 安装、环境配置与构建说明 |
| [COMPATIBILITY.md](COMPATIBILITY.md) | Creo 版本与 Toolkit SDK 兼容边界 |
| [REFERENCE_SYNTAX.md](REFERENCE_SYNTAX.md) | 建模计划、选择器与参考语法 |
| [SEED_LIBRARY.md](SEED_LIBRARY.md) | 种子库模板与使用说明 |
| [development/RELEASING.md](development/RELEASING.md) | 分支、版本与 GitHub Release 发布流程 |
| [development/GOVERNANCE_HISTORY.md](development/GOVERNANCE_HISTORY.md) | 治理规则演进与历史例外记录 |

## 2. 专题与门禁相关目录（受发布/单测门禁约束，勿随意改名或移动）

- `release-notes/RELEASE_NOTES_<version>.md`、`releases/<version>.json`、`validation/RELEASE-<version>.md`、`development/RELEASE-POSTCHECK-2026-11-07.md`：由 `creo_mechdog.release_integrity` 与 `tests/unit/test_release_records.py` 强制校验。
- `validation/`：实机与黑盒验证证据原件；部分 `.md` 文件被单元测试检索，且受 `pyproject.toml` Ruff 排除保护，保持原样。
- `work-items/`：条目工作卡（与 `BACKLOG.md` 状态同步）。

## 3. 归档目录

- [archive/README.md](archive/README.md)：存放已完结的阶段性说明、历史排查快照、过程性 AI 开发计划及早期版本流水账（`archive/stage-notes/`、`archive/superpowers/`、`archive/development/`、`archive/DEVELOPMENT_LOG_2026.md`、`archive/BACKLOG_TIMELINE_2026.md`）。

## 4. 防膨胀准入规范（后续开发遵守）

1. **过程草稿不入主干**：临时排查笔记、AI 执行计划草稿放本地 scratch 目录，不随 PR 合入 `main`；历史计划归入 `docs/archive/`。
2. **变更优先更新现有文档**：新增功能/修复直接更新对应核心文档或工作卡，避免为单次小改动在 `docs/` 根目录新建平级 `.md` 文件。
3. **控制验证产物入库体积**：单次实机测试的大体积原始 JSON/日志（建议 > 100 KB）不直接提交到 `docs/validation/`，仅提交结构化摘要、关键断言与校验指纹。
4. **后续合并优化预留**：若未来需要将平铺的 `release-notes/RELEASE_NOTES_*.md` 合并为分卷 `CHANGELOG`，须同步调整 `src/creo_mechdog/release_integrity.py`、`tests/unit/test_release_records.py` 与 `tools/package.py`。
