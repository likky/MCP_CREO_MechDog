# MCP_CREO_MechDog 0.28.0

一句话：Creo 10 的边界混合从“元素树不可提取”推进到“resident_panel 认证路线可用”，并把第二方向导线、末端单点与两段式球鼻艏实体化做成可复现、可黑盒验收的链路；单特征“点 + 导线”的再生边界、真实船体剖面映射与 Creo 9 运行期仍明确留在后续。

- 类型：MINOR（新增 `creation_route="resident_panel"` 的公开能力、第二方向导线/末端点输入与 11 位置上限；无破坏性改名）
- 日期：2026-11-19
- 公开工具：**109 个**（不变；新增能力通过既有 `creo_surface_loft` 的路线与输入表达）
- 上一版本：0.27.0
- 主台账：[BACKLOG](../BACKLOG.md) · 发布记录：[RELEASE-0.28.0](../validation/RELEASE-0.28.0.md) · 工作卡：[BUG-120](../work-items/BUG-120.md)

## 对外可见变化

### 1. Creo 10 `resident_panel` 认证路线（BUG-120）

- `creo_surface_loft(..., creation_route="resident_panel")` 在 Creo 10.0.0.0 / `release_numeric=42` 上通过认证 profile `creo10-bbl-candidate-2`：2—8 个 MCP 自有草图标签，每个标签一条开放非复合曲线，2 截面直纹、3 截面及以上 `smooth`。
- 该路线不依赖 `ProFeatureElemtreeExtract`，因此不受 Creo 10 元素树 `-18` 限制；缺 profile、部署不匹配或形式超出认证范围时在打开对话框前拒绝，且不回退 `element_tree`。
- 回执保留 `panel_receipt`、退出括号 `command_bracket` 与 `saved_file_reloaded_and_verified`；`selection_record=null`、`geometry_check.verified=false` 的既有缺口不变，几何由 `creo_inspect_model` 与只读 `creo_measure_surface_group` 复核。

### 2. 第二方向导线、末端单点与 11 位置上限（candidate-3）

- candidate profile `creo10-bbl-candidate-3` 增加 `second_direction_macro`、方向票据与 `{kind:"datum_point_feature",label:...}` 末端收敛点；位置上限从 8 扩到 11（7 曲线 + 1 点 + 3 导线）。
- 实机通过的组合：2 截面 + 2 导线（800.0 mm²）、2 截面 + 3 导线（828.9745 mm²、4 边 120 mm）、2 截面 + 末端单点（1301.2531 mm²、3 条开放边、点处无开放边界）、7 曲线 + 点（2643.27 mm²）、7 曲线 + 3 导线（2400.0 mm²、4 边 200 mm）。
- **未通过**：7 曲线 + 点 + 3 导线（11 位置）与 7 曲线 + 点 + 2 导线（10 位置）的 `selected` 与 `codes` 全部成功，但 Creo 10 在 Done 后报“特征重新生成失败”。隔离实验把边界收窄为“末端基准点 + 任意第二方向导线”同时存在；不是票据、宏顺序或位置上限。该边界随版本披露，不列为公开能力。

### 3. 两段式球鼻艏演示体与实体化

- 用“点收敛段 + 带导线段”拆开失败组合：带导线段 4 个半圆截面 + 3 条导线（7/7），点收敛段 2 个半圆截面 + 点（3/3），共享 x=60 截面；再 `quilt_merge` → `mirror`（XZ 对称面）→ `quilt_merge` → `surface_fill` 后盖 → `quilt_merge` → `solidify`。
- 最终 rev 9：`has_solid=true`、体积 **167543.67 mm³**（解析 167551.3，-0.0046%）、质心 `(25.0002,0,0)`、1 个 active 含材料实体（5 面）、8 条边均有 2 个相邻面（零自由边）、bbox 对称 ±40.12，全部作业保存重载 true。
- 范围：轴对半圆截面演示体，不是最终船体剖面；真实非圆截面/导线拼合仍属后续形状映射。

### 4. WorkBuddy 黑盒两轮通过

- 第一轮 `wb_te_panel`：两次 `resident_panel` 放样、quilt 查询、4 边测量（20/40/20/40=120 mm）、保存重载 true、旧 revision 被拒/当前 revision 成功（rev 0→7）。
- 第二轮 `wb_te_solid`：半圆柱壳 → 镜像 → 合并 → 两端封口 → 合并 → 实体化，rev 1→13，闭合壳 1884.9556 mm²、实体体积 **6283.1853 mm³**、质心 [10,0,0]，全部保存重载 true。
- 黑盒记录的面数偏差（闭合壳 4 面而非预估 3 面）、bbox Y ±10.0208 与密度不可读已按实际情况披露。

### 5. 工程修复

- `configure_panel_request` 与 `check_sections` 仍按 8 检查的缺口已修复为按 `position_limit` 检查；构建指纹补入 `panel_run.h`、`panel_references.h`、`panel_references_sdk.h`。
- Creo 10 会把注册文件的 `delay_start` 写回 `true`；同时置 `allow_stop=false` 后才能保持自启动。
- `REFERENCE_SYNTAX`、`README`、`COMPATIBILITY` 与发布资料同步了 `creation_route` 的认证边界和候选能力范围。

## 行为变化与升级注意

1. `creation_route="resident_panel"` 是显式路线；省略或 `element_tree` 保持原 2—32 截面语义，两条路线不回退混用。
2. 认证范围仍是 2—8 条开放曲线，不支持 guides、点、边界条件或模板；candidate-3 的导线/点需要候选票据，不能按公开能力使用。
3. 单特征“点 + 导线”在 Creo 10 再生失败，升级后不要把它作为可用配方；球鼻艏请使用已验证的两段式或分段方案。
4. 本版修改 `native/blend_sync.cpp`、`native/panel_*.h`、`native/panel_run.h`、`native/panel_selection_state.h` 等原生文件，升级后必须重编译 worker（`bridge.py build`）。
5. 种子库 `compatible_server_version=0.28.0`，与 0.27.x 的种子包不通用。

## 验证

- 离线：`tools/dev_check.py --work-item BUG-120` 通过，`lint_findings=0`、`unformatted_files=0`；全量单测 **4040 项通过（6 跳过）**；`bridge.py build` 退出码 0。
- 原生规则：`tools/test_panel_references.py` 与 `tools/test_panel_selection_state.py` 通过。
- 实机（本机 Creo 10.0.0.0 / release 42，用户当次授权）：T-C 的 2+2、2+3、2+点、7+点、7+3 与 T-D 两段式实体化，均记录作业号、面积/体积/质心、保存重载；11 位置的失败与边界见工作卡。
- WorkBuddy 黑盒：两轮均使用公开 MCP 工具，覆盖创建、查询、测量、保存重载、revision 保护与实体化；记录见工作卡。
- 发布资料：`tools/check_release_records.py --version 0.28.0` 与 `tools/package.py` 的四附件/发布记录门禁通过。

## 仍未验（本版不声称）

- 11 位置“点 + 导线”单特征几何；共享顶点/顶点的替代构造未验证。
- 真实球鼻艏的非圆截面、真实导线拼合与最终船体外形。
- Creo 9 运行期、Creo 12.4 之外的 Creo 版本与多环境。
- guides/点/boundary_conditions/template 在公开认证范围内的拒绝行为未由黑盒构造请求实测。
- 密度/质量（`material_query_failed`）与真实 UI 观察。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.28.0-source.zip`
- `MCP_CREO_MechDog-0.28.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.28.0-seed-library.zip`
- `MCP_CREO_MechDog-0.28.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 `dfac1ec5b62a0a926d0debf1efaf77ab13cf627ee0c6318ff6993be5201aacf9`，见[发布记录](../validation/RELEASE-0.28.0.md)与 `docs/seed_package.json`。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.28.0>
- 发布后核对：发布后执行，当前未验证；`docs/releases/0.28.0.json` 的 `remote_verification` 在打包时为 `pending`，远端列表、标签指向与附件摘要只追加到 `main` 的 [POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md)。

## 升级

1. 覆盖源码后运行 `python bridge.py build` 重编译 worker，并重启 MCP 连接器。
2. 种子库换成本版 `seed-library.zip`（`compatible_server_version=0.28.0`）。
3. 需要 Creo 10 面板路线时，先按 [Creo 10 运行手册](../validation/bug120-creo10-runbook-2026-11-18.md)注册 callback 并确认 `creo_callback_status.readiness="ready"`。
