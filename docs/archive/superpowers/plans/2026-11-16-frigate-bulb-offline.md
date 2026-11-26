# FEAT-065 原始球鼻艏离线准备 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 不连接 Creo，交付原始球鼻艏数据、精确单曲线导线及可复查的待用 MCP 最小输入。

**Architecture:** 包内离线模块读取固定 TXT 段落或冻结 JSON，精确升阶并拼接导线，生成现有 schema 的操作。独立线性/Bezier 计算验证 B 样条求值；只产出数据与数学诊断，不模拟 CAD 曲面或内核结果。

**Tech Stack:** Python 3.12+ 标准库、已有 Pydantic schema、unittest、Ruff；不新增依赖。

**Spec:** [FEAT-065 离线子项](../../work-items/FEAT-065.md#2026-11-16-原始-txt-球鼻艏离线子项)，用户已同意执行前述离线方案，授权不覆盖 Creo。

## Global Constraints

- 全程不连接/启动 Creo、不编译执行器；离线准备入口不启动 MCP 服务、无 live 模式。全量单测中的 stdio 模拟子进程沿用既有框架，不连接 Toolkit。
- A18—A23 原始米制数据保留，默认 1000 mm/m；只建正 Y 半体。
- 拼接及坐标还原误差 ≤1e-7 mm；源网络连接阈值固定为原尺寸 0.01 mm，随缩放同比变化。
- 不改原始曲线来凑交点；不把控制点包络当曲面包络；不生成未经 CAD 核验的面积/体积。
- 复用当前 codex 分支，保留既有 dirty 修改；本批不提交/合并/发布，不改历史反馈原件。

## Review Focus

- 单位/缩比和 XZ、YZ 坐标变换必须能还原所有原始控制点。
- 上下导线需反向 Bézier 后接升阶直线；内部三重节点和接点两侧均核验。
- Sketch67 仅取纵向样条，不能把辅助横线当第二条导线。
- 中导线和中截面按真实求值求交，允许报告原始舍入残差，禁止自动修正。
- 数据来源 SHA256、计划校验与实机未验证状态必须随报告交付；任意失败不能标为全部通过。

## Task 1: 提取、适配及独立校核

**Files:** `src/creo_mechdog/frigate_bulb.py`、`tests/unit/test_frigate_bulb.py`、`examples/frigate_bulb_source.json`。

**Interfaces:** `extract_source(path)` → 原始数据字典；`build_plan(source, mm_per_m=1000)` → 公共 MCP payload；`audit(source, plan, mm_per_m=1000)` → 离线诊断。

- [x] 先写测试：原始数据提取、源单位/符号、Bezier 与直线拼接等价、接点两侧、辅助线排除、缩放与反变换、原始网络残差及负例。
- [x] 运行专项测试并观察失败，再实现模块；冻结 TXT A18—A23 的来源和数据快照。
- [x] schema 校验生成 payload，原始控制点与节点权重不做拟合或修正。

## Task 2: 可重跑入口与交付记录

**Files:** `tools/prepare_frigate_bulb.py`、`examples/frigate_bulb_minimal.json`、`docs/development/FRIGATE-BULB-OFFLINE-2026-11-16.md`，以及 FEAT-065/BACKLOG 原行。

**Interfaces:** 消费 Task 1 三个函数；CLI `--source TXT` 可选、`--mm-per-m` 默认 1000、`--output-dir` 默认 `build/frigate_bulb_offline`。仅写报告/计划/摘要清单，失败返回非零。

- [x] 运行 CLI，核对冻结数据与 TXT 逐项一致、报告的来源与源码身份、待用 payload 和文件摘要。
- [x] 运行专项 unittest、Ruff 和适用全量开发检查；独立审阅者检查数学与授权边界。
- [x] 将实际结果、命令、源码身份、dirty 和未测范围回填工作卡与说明，保持整卡状态及历史记录。

## 执行记录

用户已授权本轮离线实现，按现有工作树继续；不因流程文件再请求同一授权。任务完成和审阅结果在此回填，不把未授权实机列为已完成。

Task 1 / Task 2 完成：最终专项 11 项通过，原 TXT/冻结数据/生成计划/摘要清单一致，数学拼接与坐标还原符合预设阈值。独立审阅提出的来源自比问题已用两条 RED→GREEN 回归修复并复核。

全量运行 3711 项有 1 项既有 dirty 几何选择器测试失败（`test_circular_edge_needs_centre_and_radius_together`），隔离复现，不修改其他任务现场；全量启动后来源增量另用最终专项验证，最终语言检查通过。完整失败与最终语言报告分别保留，不把后者当全量通过。未连接 Creo、未编译执行器、未做实机验收，未提交/合并/发布。
