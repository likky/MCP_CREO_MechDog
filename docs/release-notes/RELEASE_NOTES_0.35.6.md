# MCP_CREO_MechDog 0.35.6 版本说明

版本类型：PATCH。承接 0.35.5。

上一版本：0.35.5（`v0.35.5`，提交 `91642489e708f1c2ac7ee3fa1ff6f8565a53851b`）。

## 亮点

- **装配质量属性放开**：[FEAT-057](../work-items/FEAT-057.md) 用 `ProSolidMassPropertyWithDensityGet` 的装配支持取代此前的“只允许零件”拒绝。单位密度一次给出体积、表面积与几何重心 `center_of_volume_mm`，材料密度一次给出质量重心 `center_of_mass_mm`，混合密度时两者可分。新增只读 occurrence 扫描（组件特征递归，子装配 ≤32 层、活动实例 ≤4096），证明整棵活动树参与求和；缺材料、模型未解析或扫描不完整时 `mass_g` 保持 `null`，并分别给出 `component_material_missing`、`component_unavailable`、`component_scan_incomplete`、`no_components` 与对应 occurrence path。装配由真实材料求得质量时，`density_g_cm3` 是总量/总体积的有效平均密度并带 `density_is_effective_average=true`。能力清单移除 `assembly_mass_parts_only`、`parts_only=false`。本机 Creo 10 实机 12/12：A 件 1000 mm³ 两实例 + B 件 200 mm³ 得体积 `2199.9999999999986` mm³、面积 `1679.9999999999998` mm²、几何重心 `[22.727…, 2.727…, 2.3636…]`，与解析加权值一致。
- **有界批量只读查询**：[FEAT-073](../work-items/FEAT-073.md) 新增 `creo_get_mass_properties_batch`（公开工具 110→111）。1–16 个模型、10–600 s 预算在提交前校验，重复或超限不创建作业；每项一次只读 `mass_properties` 作业、逐项回执，失败项带 `error_kind`（`invalid_request`/`query_failed`/`toolkit_busy`/`timeout`）与 `blocking_job_id`，未执行项带 `reason`；坏 id 或查询失败只影响该项。仍是单通道串行，并发 busy 立即拒绝属已声明行为（BUG-009）。实机 15/15 与补验 11/11：16 项满批 `elapsed_seconds=131.188`（预算 180 s），真实 `toolkit_busy` 可查回 `blocking_job_id`，真实在飞超时后该作业 3.06 s 自行 `succeeded`。
- **多会话可选定、无需重启**：[FEAT-072](../work-items/FEAT-072.md) 在 `creo_startup_status`/`creo_session_status` 报告 `session_candidates`（逐进程 pid、镜像、创建时间、安装路径匹配、窗口状态，每条 `identified=false` 并说明 `ProProcessHandle` 是 `PeerIdx`、PID 不能换算会话 ID），`retry=true, session_id=…` 在进程内选定目标、覆盖配置且不写 `config.json`，失效 ID 不回落。实机双 Creo 现场得到 `toolkit_code=-36`/`selection_required`，关闭多余会话后无需重启即恢复 `connected=true`。
- **停滞恢复有终态出口**：[BUG-146](../work-items/BUG-146.md) 记录意图启动者（`launched_by`：PID + 创建时间）；意图已落盘而 runner 未起 worker 时，`inspect` 给出 `stalled_recovery` 与 `recovery_wait`，`abandon_stalled_recovery`（需显式确认）只释放 `recovery_pending`，保留 `pending_job`、revision 与会话保护。实机（Creo 10 镜像挂死现场自然产生）走通：`stalled_recovery.proven=true`（basis=`runner_exited`）→ 放弃意图 → `restore_baseline` 成功，体积回到 `1999.9999999999998` mm³。
- **固体特征镜像挂死根因**：[BUG-143](../work-items/BUG-143.md) 两次复现实体镜像停在 `mirror:block_mirror`（330 s / 240 s、Creo 窗口仍响应、随后 `toolkit_code=-38`），末行是 `ProArrayAlloc(…ProFeatureCreateOptions…)=0`。根因是 `PRO_E_MIRROR_REF_ITEMS` 只接受曲线/轴/quilt/基准面/坐标系/点/整体零件，`ProMirror.h` 明确排除 `PRO_FEATURE`。现契约与原生都在创建前拒绝全部 feature 引用，并分别指向 `{kind:"part"}` 与 `{kind:"quilt",id:N}`；实机复验拒绝发生在提交阶段（无作业、会话 `toolkit_code=0`），`{kind:"part"}` 路线 4000 mm³、保存重载 true。
- **材质密度失败可归因**：[BUG-147](../work-items/BUG-147.md) 的失败回执给出 Toolkit 调用名、返回码与显式密度用法；Creo 10 实测材料已分配但密度查询 `-1`，指定 `density_g_cm3=7.85` 可得正确 what-if 质量。
- **多开放轮廓有明确指引**：[BUG-148](../work-items/BUG-148.md) 在曲面拉伸失败时区分单个与多个开放轮廓，给出“每个开放轮廓一次曲面拉伸”的指引与原生截面计数；单开放轮廓单特征与闭合对照均成功。
- **桌面 worker 去掉批处理编码依赖**：[BUG-145](../work-items/BUG-145.md) 的真实 Explorer 对照（ASCII 0、中文脚本参数 2、中文临时目录无回执）修复后中文路径与参数逐字返回。

## 变更总览

- 原生：`native/generic.cpp` 装配质量属性与 occurrence 扫描、镜像 feature 引用拒绝、多开放轮廓诊断；`native/inspection_units.h` 新增 `area_mm2()`。
- Python：`src/creo_mechdog/mass_properties.py`（装配字段与扫描证据校验）、`generic_bridge.py`（`get_mass_properties_batch` 与 `_mass_properties_receipt`）、`server.py`（新工具与就绪检查）、`capabilities.py`（移除 `assembly_mass_parts_only`，新增 `mass_properties.batch`）、`session_candidates.py`/`session_choice.py`、`reconciliation.py`（停滞恢复与 `abandon_stalled_recovery`）、`schema.py`。
- 桌面链路：`desktop_worker.py`、`creo_startup.py`、`bridge.py`（探测失败上报与会话选择接线）。
- 测试：新增 `tests/unit/test_feat073_batch_mass.py`、`test_feat072_session_selection.py`、`test_bug146_stalled_intent.py`、`test_mass_assembly_admission.py`；扩充 `test_mass_properties.py`、`test_reconciliation.py`、`test_desktop_worker.py` 等；工具数 110→111 的断言同步八处。
- 文档：README 特性段与工具清单、`docs/REFERENCE_SYNTAX.md`、`docs/INSTALL.md`、工作卡、主台账与反馈计划同步。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [FEAT-057](../work-items/FEAT-057.md) | 装配质量属性：体积/面积/两个重心、occurrence 扫描证据、有效平均密度标记；Creo 10 实机 12/12。 |
| [FEAT-073](../work-items/FEAT-073.md) | `creo_get_mass_properties_batch`：≤16 模型、逐项回执与 `error_kind`、预算截断；实机 15/15 与满批/占用/超时 11/11。 |
| [FEAT-072](../work-items/FEAT-072.md) | 候选列表 + 进程内 `session_id` 选定 + 失效不回落；单会话与双会话实机。 |
| [BUG-143](../work-items/BUG-143.md) | 固体特征镜像挂死根因（`PRO_E_MIRROR_REF_ITEMS` 排除 `PRO_FEATURE`）与创建前拒绝；实机复验。 |
| [BUG-145](../work-items/BUG-145.md) | 桌面 worker Unicode 路径/参数与清理异常；Explorer 对照修复后逐字返回。 |
| [BUG-146](../work-items/BUG-146.md) | `launched_by` 身份、`stalled_recovery`、`abandon_stalled_recovery`；实机恢复全链路。 |
| [BUG-147](../work-items/BUG-147.md) | 材质密度失败的调用名/返回码/显式密度用法；Creo 10 复现与 what-if 质量。 |
| [BUG-148](../work-items/BUG-148.md) | 多开放轮廓曲面拉伸的拆分指引与截面计数；三例实机。 |

## 已知限制（如实记录）

- 装配质量属性未验：缺材料组件（模板自带材料，MCP 无移除工具）、抑制装配组件（`feature_state` 仅零件/钣金）、嵌套子装配（`creo_assemble_component` 未支持）、混合密度真实质量、主惯量与英寸装配。
- 批量查询的完整 120 s 超时窗口只有离线覆盖；本机造不出“查询卡满整窗”的现场，实机超时来自预算窗口不足（作业随后自行成功）。
- Creo 10 的模板材料密度查询返回 `-1`（BUG-147 同源），真实材料质量仍需显式 `density_g_cm3`；`creo_cancel_job` 无法清除客户端退出遗留的只读 pending job（建议另立 BUG-149，本版未处置）。
- 本版继续按 PATCH 递增：新增一个公开工具（110→111），未删除或重命名既有接口；装配质量属性沿用同一工具，只放宽准入与回执字段。

## 附件与摘要

Release 发布后见 `https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.6`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.6-source.zip`
- `MCP_CREO_MechDog-0.35.6-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.6-seed-library.zip`
- `MCP_CREO_MechDog-0.35.6-seed-library.zip.sha256`

- 种子包 SHA256：`32ea2d0324e329f46bce7ac9dd41bd3086e2b7f151b1227e035038f0b1bd81fe`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）复跑。
