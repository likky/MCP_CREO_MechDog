# MCP_CREO_MechDog 0.31.0

一句话：放样前先量导线，建成后按实际新增面组回读——缺参数在建作业前说清楚，三导线曲面和完整实体链都能带回面积、边界与保存重载证据。

- 类型：MINOR（`resident_panel` 输入契约收紧、回执新增字段；无新增公开工具）
- 日期：2026-11-19
- 公开工具：**109 个**（不变）
- 上一版本：0.30.0
- 主台账：[BACKLOG](../BACKLOG.md) · 发布记录：[RELEASE-0.31.0](../validation/RELEASE-0.31.0.md) · 工作卡：[BUG-120](../work-items/BUG-120.md)

## 对外可见变化

### 1. 裸标签在建作业前被拒（任务 1）

- `creation_route="resident_panel"` 的 `sections`/`guides` 现在必须在 Python 校验阶段写成 `{label, open_confirmed:true}`。裸标签字符串在 `validate_operations` 时被拒绝，错误信息给出可操作的写法，并说明“未建作业、未触碰 Toolkit 通道”。
- `creo_surface_loft` 与 `creo_execute_plan` 共用同一校验；`element_tree` 路线的裸标签行为不变；首/末截面为收敛点 `{kind:'datum_point_feature',label:...}` 时仍按点处理。
- 工具说明与 `creo_capabilities.routes.resident_panel.limits` 同步说明该写法。

### 2. 开面板前的曲线配合诊断（任务 2）

- 新增纯 C++ 的 `native/panel_fit.h`，在引用解析完成、`MechDogPanelPrepare`/宏提交之前，用 `ProCurveXyzdataEval` 采样并做局部交替细化，输出 7×3=21 对截面×导线记录：角色、标签、实际 feature/curve ID、测量状态、方法、`section_t`/`guide_t`、位置、间隙 mm/native、原始码、端点闭合与穿过顺序。
- 采样失败或局部最小超容差记 `unverified`/`no_sample_intersection`，不写零、不宣称“不相交”。本版只报告、不新增拒绝规则；缺特征、复合/闭合曲线、零/未知长度仍由既有硬规则拒绝。
- 新增 `panel_preopen` 未开面板正向证据：worker 在宏提交前失败时携带 job/nonce/profile/phase，Python 可退本任务 guard，不再把这类前置拒绝投影成 `unknown_outcome`。

### 3. 成功回执关联实际面组（任务 3）

- 面板作业前快照 feature/quilt ID，作业后按“唯一新增 quilt + 其新增 owner feature”关联；保存重载后在重载模型上用 `quilt_record` 与 `surface_group_receipt` 读取面积、开闭、面组和边界记录。
- `panel_receipt.geometry_check.verified` 改为由 Python 依据“正面积 + 唯一目标面组关联 + 重载后读数 + 保存重载证明”计算，缺项保留 `unverified` 并列出原因；测量失败不回写事务结论。

### 4. B/C 实机回归（任务 4）

- B（三导线曲面）：新模型 `ceda66c1…`，作业 `01` `9d854dd0…` → `09` `66a65ab2…` → 面板放样 `744abfff…`，rev 3，面组 **142** / 特征 **136**，单面、开放、面积 **46,555,189.24528535 mm²**；`curve_fit_check` 21/21 对 `crossing`、0 `unverified`，导线穿过顺序 upper=forward、side/lower=reverse 且均 monotone；独立 `creo_measure_surface_group` 4 条开放边 **11916.01893 / 11924.14083 / 4612.01158 / 2126.66969 mm**；`geometry_check.verified=true`，保存重载 true；PRT SHA256 `d186b587…`。
- C（完整实体链，在 B 的 PRT 副本上）：采用作业 `3dbf8e89…`，艏段几何 `9a3b1f50…`、艏段放样 `61f1430f…`（quilt 172）、缝合 `660a10ee…`（142）、镜像 `48d9e87c…`（新 quilt 194）、左右缝合 `a2888e30…`（142）、后盖 `e228c80f…`（新 quilt 241）、封盖缝合 `2a987299…`（142）、实体化 `c41a497d…` 全部成功，rev 9。最终一个活动含材料实体、体积 **55,087,038,135.823044 mm³**、质心 `(69198.6544,0,-5595.6546)`、5 面/14 边/58 特征；独立闭合测量为 5 面、14 条共享边、**0 开放边**、`state=closed`；保存重载 true；PRT SHA256 `22223de9…`。

## 行为变化与升级注意

1. `resident_panel` 的 `sections`/`guides` 裸字符串现在是输入错误；请改用 `{label, open_confirmed:true}`。`element_tree` 路线不受影响。
2. 成功回执新增 `curve_fit_check` 与更严格的 `geometry_check` 判定；`selection_record` 仍为 null（本版载荷不写），几何证据由新增字段与保存重载后的测量提供。
3. 本版**有原生改动**（`native/panel_fit.h`、`native/panel_run.h`、`native/generic.cpp`）：升级后需重新编译 worker（`bridge.py build`）并在 Creo 辅助应用程序中重新加载回调。
4. 种子库 `compatible_server_version=0.31.0`，与 0.30.x 的种子包不通用。

## 验证

- 离线：全量 unittest **4078 项通过（6 跳过）**；`tools/test_panel_fit.py` 通过；`tools/dev_check.py --skip-unit`（Ruff + clang-format）通过；`bridge.py build` exit 0。
- 实机：Creo 10.0.0.0 / release 42，B/C 均 `saved_file_reloaded_and_verified=true`，几何与保存重载结果见上节；证据目录 `build/bug120_task4/`（`B_report.json`、`C_report.json` 与两份 PRT 副本）。
- 实机跑在 worker `9d353a47…` / source digest `058e8cdb…` / 面板载荷 `eba1b25b…`；收尾把 `panel_fit.h` 加入 `bridge.callback_relatives` 后同源重建为 worker `39fafb98…` / 载荷 `5dc6b5a4…`（仅构建依赖清单变化，运行代码未变，未重跑 B/C）。
- 发布资料：`tools/check_release_records.py --version 0.31.0` 与 `tools/package.py` 的四附件/发布记录门禁。

## 仍未验（本版不声称）

- 任务 5 接缝 G1：历史失败基线最大 **6.28°**（判据 0.5°），本版未重测，按用户要求单独排期。
- WorkBuddy 黑盒本轮未重跑。
- 真实船体非圆剖面、STL 导出与自动加载回调不在本批。
- Creo 10 release 42 之外的版本；本机结果不外推。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.31.0-source.zip`
- `MCP_CREO_MechDog-0.31.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.31.0-seed-library.zip`
- `MCP_CREO_MechDog-0.31.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 `fef385db303722c3279b9fc6525dc8fd06717b6d67f99d6128c587d04a2e8356`，与 `docs/seed_package.json` 一致。
- Release：发布后执行，当前未验证；当前 `docs/releases/0.31.0.json` 的 `remote_verification` 为 `pending`。
