# MCP_CREO_MechDog 0.29.0

一句话：把 Creo 10 `resident_panel` 的第二方向导线、末端单点与最多 11 个位置从候选升为公开认证，并让“profile 不支持导线”的请求在提交前被拒绝，普通客户端不再因此留下 `unknown_outcome` 与 panel guard。

- 类型：MINOR（扩展 `creation_route="resident_panel"` 的认证输入范围；无破坏性改名）
- 日期：2026-11-19
- 公开工具：**109 个**（不变；能力通过既有 `creo_surface_loft` 的路线与输入表达）
- 上一版本：0.28.0
- 主台账：[BACKLOG](BACKLOG.md) · 发布记录：[RELEASE-0.29.0](validation/RELEASE-0.29.0.md) · 工作卡：[BUG-120](work-items/BUG-120.md)

## 对外可见变化

### 1. 公开认证 profile 切换为 candidate-3（BUG-120）

- 新增认证记录 `templates/panel/certifications/creo10-bbl-2026-11-19.json`，绑定 profile digest `bc3bfefb…`、Creo 10.0.0.0 / `release_numeric=42`、载荷 `3c80bf15…`、loader `edceae2e…`/指纹 `83ad907d…`，收录 2+2 导线、2+3 导线、2+末端点、7+3 导线与两段式球鼻艏实体五组实机案例。
- `templates/panel/manifest.json` 把 `creo10-bbl-candidate-3` 升为 `certified` 并排在最前；它是 `creo10-bbl-candidate-2` 的超集（第一方向步骤相同，只多 `second_direction_macro`），因此 `certified_profile()` 对 release 42 返回 candidate-3。candidate-2 保留为独立认证记录，candidate-1 仍是开发驱动专用 candidate。

### 2. 公开的 resident_panel 输入范围

- 第一方向：2—8 个 MCP 自有草图标签（每个一条开放非复合曲线），或一个只在首/末的收敛点 `{"kind":"datum_point_feature","label":"..."}`（每个放样最多一个）。
- 第二方向：可选 2—8 条导线（`guides`）。
- 单次最多 **11 个位置**（7 曲线 + 1 点 + 3 导线的上限）；2 截面直纹，3 截面及以上需 `interpolation="smooth"`。
- 仍然不接受边界条件、闭合截面或模板。
- 已实机通过的公开组合：2+2（800.0 mm²）、2+3（828.9745 mm²、4 边 120 mm）、2+末端点（1301.2531 mm²、3 条开放边且点处无开放边界）、7+3（2400.0 mm²、4 边 200 mm），均保存重载 true。
- **点与导线不能同时出现在一个特征里**：Creo 10 在该组合上选择成功后再生失败。点收敛段应作为共享末截面的第二个放样提交；两段式球鼻艏演示体（体积 167543.67 mm³）即按此构造。

### 3. 准入修复

- 新增 `capabilities.require_panel_directions()`：当准入 profile 没有 `second_direction_macro` 时，带 `guides` 的请求在 `generic_bridge.submit()` 取通道锁之前被拒绝，消息明确“未建作业、未打开对话框”。
- 修复前，这类请求会穿过 Python 准入、在原生 worker 内以 `PANEL_COMMAND_MISSING` 失败，被投影为 `unknown_outcome` 并写入 panel guard（WorkBuddy 黑盒作业 `f6e1a29c…` 即此路径）。

### 4. 披露与回执

- `creo_capabilities` 的 `surface_loft.routes.resident_panel.limits` 同步为上述范围，并写明“单特征点+导线不可再生、需两段式”。
- `panel_receipt.geometry_check.verified=false`（载荷未写 `selection_record`）的既有缺口不变，几何仍由 `creo_inspect_model` 与只读 `creo_measure_surface_group` 复核。

## 行为变化与升级注意

1. `creo_capabilities` 中的认证 profile 从 `creo10-bbl-candidate-2` 变为 `creo10-bbl-candidate-3`；只做第一方向放样的调用行为不变。
2. 带 `guides` 的请求若落在没有第二方向槽的 profile 上，现在是提交前 `ValueError`，不再创建作业或留下 guard；请按错误提示改用认证 profile 或去掉导线。
3. 单特征“点 + 导线”仍不可再生，升级后不要把它作为可用配方；球鼻艏请使用已验证的两段式或分段方案。
4. 本版**没有原生改动**：`native/`、worker、loader 与面板载荷均与 0.28.0 相同，升级无需重编译 worker；只需更新源码、重启 MCP 连接器并换用新种子包。
5. 种子库 `compatible_server_version=0.29.0`，与 0.28.x 的种子包不通用。

## 验证

- 离线：全量单测 **4045 项通过（6 项跳过）**；`ruff check` 与 `ruff format --check` 通过；`tools/dev_check.py --work-item BUG-120` 通过。
- 原生规则：`tools/test_panel_references.py`（`all rules hold`）通过。
- 实机：本版没有新增实机操作，认证记录绑定的是 0.28.0 期间在 Creo 10.0.0.0 / release 42 上取得的五组案例（作业号、面积/体积、保存重载均见工作卡与 `BUG-120.md`）。
- 发布资料：`tools/check_release_records.py --version 0.29.0` 与 `tools/package.py` 的四附件/发布记录门禁通过。
- 源码包解压：`test_panel_profiles`、`test_surface_loft_panel_admission`、`test_release_integrity` 共 115 项通过（包内缺少仓库验收原件时跳过 1 项）；全量包内单测受无 `.git`/`.venv`/`build` 限制，不作为本版结论，仓库工作树的全量结果见上。

## 仍未验（本版不声称）

- 11 位置“7 曲线 + 点 + 3 导线”的单特征几何；共享顶点的替代构造未验证。
- 真实球鼻艏的非圆截面、真实导线拼合与最终船体外形。
- 用新认证 profile 重跑 WorkBuddy 黑盒（上一轮黑盒使用的是候选态、公开范围仅第一方向）。
- Creo 9 运行期、Creo 12.4 之外的 Creo 版本与多环境。
- 密度/质量（`material_query_failed`）与真实 UI 观察。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.29.0-source.zip`
- `MCP_CREO_MechDog-0.29.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.29.0-seed-library.zip`
- `MCP_CREO_MechDog-0.29.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 `cd3a5d5ec11928670f9e35aa6cdc2deb06314ce94ab9b7d8df5825af34ae8db3`，两次构建摘要一致，见[发布记录](validation/RELEASE-0.29.0.md)与 `docs/seed_package.json`。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.29.0>
- 发布后核对：发布后执行，当前未验证；`docs/releases/0.29.0.json` 的 `remote_verification` 在打包时为 `pending`，远端列表、标签指向与附件摘要只追加到 `main` 的 [POSTCHECK](development/RELEASE-POSTCHECK-2026-11-07.md)。

## 升级

1. 覆盖源码后重启 MCP 连接器；本版没有原生改动，0.28.0 已编译的 worker 与面板载荷可继续使用（若曾重建，按 `bridge.py build` 与 `panel_target_check.py deploy --deploy` 的既有步骤执行）。
2. 种子库换成本版 `seed-library.zip`（`compatible_server_version=0.29.0`）。
3. 需要 Creo 10 面板路线时，先按 [Creo 10 运行手册](validation/bug120-creo10-runbook-2026-11-18.md)注册 callback 并确认 `creo_callback_status.readiness="ready"`。
