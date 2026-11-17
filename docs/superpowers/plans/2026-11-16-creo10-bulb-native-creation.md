# Creo 10 球鼻艏原生创建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完善 MCP，使目标 Creo 10.0.0.0 能依据 v2 的七个截面、尖点和三条完整导线生成原生边界混合曲面，进一步封闭成球鼻艏实体并保存重载。

**Architecture:** 保留现有 `surface_loft` 元素树路线，增加显式 `creation_route="resident_panel"`。新路线由驻留回调向原生边界混合面板按方向注入引用，完成后用真实特征/面组验收，不依赖 `ProFeatureElemtreeExtract` 补全特征；先在目标机取得可行性证据，再实现通用调度与兼容准入。

**Tech Stack:** Windows x64、Python 3.12+/unittest、C++17/MSVC、目标 Creo 10 TOOLKIT、现有驻留 loader/payload、PTC 原生界面及录制的 mapkey。

**Spec:** [BUG-120 当前结论与设计约束](../../work-items/BUG-120.md)，配套 [BUG-122](../../work-items/BUG-122.md)。本文件为待实施方案，**不表示面板路线已实现或已通过 Creo 10 实机**。

## Global Constraints

- 用户本次要求先解决 Creo 10 创建球鼻艏失败；BUG-130 STL 后排，不纳入本计划。
- 长度使用毫米，角度使用度；特征标签以小写字母开头，仅含小写字母、数字和下划线，最多28字符。
- Toolkit 单通道；忙碌立即拒绝，不排队、不自动重试；接受后只轮询原 job。
- 实机测试须用户当次明确确认；本次要求计划不构成启动、编译或连接 Creo 的授权。
- 不擅自结束/重启 Creo 或 nmsd，不清 `toolkit.lock`/unknown 保护，不覆盖用户模型或历史证据。
- 开发者测试与 WorkBuddy 黑盒分开；后者不读源码、SDK、配置或运行本地脚本。
- `server.py` 只转发；新业务逻辑放包内或原生模块；新增原生文件及其实际 include 进入构建指纹和源码包清单。
- 原有省略路线的调用继续走元素树；不静默换路线、改形、降低精度或导入替代几何。
- 本项的 Creo 10 是直接目标，必须有其运行证据；不恢复全项目 Creo 10/12 双版本发布门槛。

## Review Focus

1. 宏返回0但面板未完成：不得提前提交、保存或释放 Toolkit 通道；由 Task 1/4 验证完成栅栏。
2. 旧 worker、旧驻留 DLL 或上一作业结果混入：身份/请求 nonce 不匹配须拒绝；由 Task 2/3 验证。
3. 第二方向导线或末端点被选入错误位置：按 role/index/kind 回执，真实几何复核；由 Task 3/5 验证。
4. 曲线有微小交点差或 autodim 移动：分别测输入与结果，不自动吸附、不临时放宽容差；由 Task 2/5 验证。
5. 失败/取消/超时时面板仍活跃：只有确证恢复才报回滚；无法确认则 unknown 并保护；由 Task 4/5 验证。

## 可行性与取舍

**2026-11-17 T1-C复核后的范围裁定：** 原始回执已补齐并关联，近似bbox来源、可回放取消序列和中间截面对形状的作用已取得目标机证据，详见[T1-C复核](../../development/CREO10-T1C-REVIEW-2026-11-17.md)。允许转入第一方向的正式协议/后端离线开发，不再重复索取已齐的T1-B原件；这不是Task 1全范围go或入口开放。Task 1的点/第二方向取样仍待完成，第一方向的可靠结束/保存重载由正式实现验证：修复Done排队被误标committed、类型/来源弱校验、共享请求跨作业复位。Task 2—4可以先实现受控的第一方向子集并保持不可用，取得正式工具端到端证据后才开放该子集；不靠未验证的点/导线支撑能力声明。本机本轮只复核，不编译或连接Creo。

**2026-11-17 T1-B完整包后执行裁定：** 六份PRT和原始选择日志已匹配，按ID的第一方向路线取得外部积极证据；几何原件仍缺12份，三/五截面bbox未过，collector实际顺序、可靠自动取消/完成结束仍未闭环。Task 1整体保持未通过，Task 2—6的新panel入口、协议升级及原生后端不提前开放。允许先完成独立于新UI流程的旧BUG-122观测接线和unknown保护回归，以及离线审计/补证工具；它们不计为通用面板后端完成。补测交接见 [T1-C](../../development/CREO10-T1C-HANDOFF-2026-11-17.md)。用户本轮“看看继续处理”覆盖离线审查和修改，不替代本机Creo实机授权。

**2026-11-17目标机反馈更新：** 用户回传T1-A最小两线案例的GUI与半自动mapkey回放摘要，两份收养结果报告均为800mm²、120mm边界、`[[0,0,0],[20,40,0]]`、单面开放quilt、保存重载通过。原始294B录制文件已接收并[按原字节归档](../../validation/bug120-creo10-t1a-2026-11-17/originals/t1_blend_mapkey.pro)，确认命令 `ProCmdFtBndBlend`、第一方向表格FocusOut、3次拾取暂停和 `dashInst0.Done`；原生几何/重载完整回执尚待接收。FocusOut不是collector激活，3暂停不代表3条引用，宏也未记录Ctrl和过滤/基准显示前置。本案例可进入T1-B自动选取探针准备，但本计划Task 1还包含点、第二方向和可靠完成/取消观察，**不得整项打勾或把GUI成功视为回调成功**。详见[BUG-120最新进展](../../work-items/BUG-120.md)。

| 方案 | 能交付什么 | 依据与缺口 | 本计划定位 |
| --- | --- | --- | --- |
| 原生面板＋驻留回调 | 原生边界混合特征，引用截面、导线、尖点 | 现有实体 Blend 已用回调选取；但边界曲面需新面板流程，目标机命令/控件/完成时序未验证 | **主方案，有条件可行；Task 1 是继续投入的前提** |
| 内存 NURBS＋`ProImportfeatCreate` | 在 Creo 内生成曲面/实体导入特征 | PTC 有任意几何数据导入接口；仍需曲面求解、修剪边、拓扑及 Creo 10 SDK/运行核验 | 主方案失败后的独立备选；不自动切换，不等同参数化放样 |
| 已有精确 STEP 导入 | 几何参照或临时可用实体 | 已有导入工具；目标机仍需实测单位、几何和重载 | 可用于诊断，不计为本计划原生创建完成 |
| 只修拒绝、换 XML 或跳过 Extract | 清楚报错/减少无效尝试 | 不能把不完整空壳变成有效曲面 | 不作为成型方案 |

PTC [Creo 11 发布说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r11.0/usascii/creo_toolkit/protoolkit_rln/Support_for_Boundary_Blend_Feature_11000.html)说明边界混合元素树支持从11加入；当前失败链是 `INCOMPLETE create → Extract=-18 → 未到 redefine → 回滚`。符号能编译不证明旧宿主能完成特征。

PTC [ProMacroLoad](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/italian/creo_toolkit/api/dita/3136.html)仅保证载入命令序列，且不保证跨版本有效；[命令录制说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/chinese_tw/creo_toolkit/Entering_Creo_Parametric_Creo_Commands.html)明确手工编辑 mapkey 不是受支持的脚本语言。因此主方案是**限定版本、经过实测维护的工程兼容路线**，不能宣称获得了一个跨 Creo 版本稳定的官方边界混合 API。

## 最小交付范围

- 沿用 `creo_surface_loft` 工具和 `surface_loft` 操作，不新增公开工具。
- 新增可选 `creation_route: Literal["element_tree", "resident_panel"] | None = None`；省略/None 不写入操作，旧序列化与默认行为保持。native 有效默认值为 `element_tree`。
- 第一版 panel 子集：2—8个截面（含点），仅 MCP 管理的单条开放草图曲线标签；允许最后一项为单点 datum feature；导线为0、2或3条单曲线草图标签。两截面 `straight`，多截面 `smooth`。先覆盖 YZ@X 的目标案例，不声称支持任意曲线/边/闭合截面。
- panel 拒绝 `template`、非空 `boundary_conditions`、首端/中间收敛点、曲线/边裸引用、非目标子集；错误在可能的最早阶段给出具体原因。元素树路线的既有输入范围不缩减。
- 缺新 worker 路线声明、匹配模板或匹配驻留身份时，panel 不运行。`readiness=not_loaded` 给现有注册/启动说明，不由建模请求加载 DLL 或修改安全设置。
- 只在 Task 1 的实测版本/界面模板范围内开放。初始目标10.0.0.0；模板记录真实日期码/语言、来源、命令片段与 SHA256。不能用数字42推断所有 Creo 10 日期码都适用。

## 文件与职责

| 文件 | 计划变更 |
| --- | --- |
| `src/creo_mechdog/surface_ops.py`、`server.py` | 可选路线字段、panel 子集校验、工具转发 |
| `src/creo_mechdog/capabilities.py`、`bridge.py`、`generic_bridge.py`、`native/worker.cpp` | 新 worker 路线声明、BUG-122 观测接线、按路线准入/披露 |
| `native/blend_sync.cpp`、`callback_identity.h`、`callback_runtime.h`、`blend_create.cpp`、`src/creo_mechdog/blend_callback.py` | 驻留协议4、分方向选取、身份/代际与旧普通 Blend 兼容 |
| 新 `native/panel_selection_request.h` | 无 Toolkit 的请求校验、顺序及状态模型；被 payload/worker 实际使用 |
| 新 `native/surface_loft_panel.h/.cpp`、`native/generic.cpp`、`src/creo_mechdog/job_projection.py`、`operation_results.py` | 独立 panel 后端、最小分派及完整/compact回执；不改旧树的补全策略 |
| 新 `templates/panel/manifest.json` 和目标机录制模板 | 仅收录 Task 1 实测成立的命令/完成证据；不存用户模型/SDK |
| 新 `examples/frigate_bulb_creo10_geometry.json`、`tools/test_creo10_bulb.py` | 固定输入、离线核验与需显式 live 的目标驱动 |
| 新/现有 `tests/unit/test_*panel*.py`、callback/admission 单测 | 输入、身份、准入、状态与兼容回归 |
| `bridge.py` 构建入口、`src/creo_mechdog/release_integrity.py`、打包相关测试 | 新独立编译单元、真实依赖指纹、模板白名单与摘要校验 |

### Task 1：目标 Creo 10 面板路线可行性试验

**Files:** 新 `tools/probe_surface_loft_panel.py`；证据在 `build/bug120_creo10_panel_probe/<run>/`；通过后新增 `templates/panel/manifest.json` 及实测模板。

**Interfaces:** 输入为用户当次授权的 Creo 10 GUI、匹配 SDK/许可、已显式启动的回调及临时零件；输出 `probe.json`，包含 `host_identity`、`callback_identity`、`profile_sha256`、`selection_intent`、`collector_acceptance_evidence`、`completion_observation`、`geometry`、`saved_file_reloaded_and_verified`、`decision`。回调的选取意图与面板真实接受证据分开，不伪装成元素树引用回读。

- [ ] 核对目标机真实版本、SDK声明、GUI与回调身份；不能拿本机12.4或配置路径当目标10运行证据。开发 AI 负责实际取样，不要求用户手工创建参照/判定节点。
- [ ] 使用原生 UI 在临时零件录制边界混合操作，确认真实命令、collector、提交、取消及返回空闲的观察方法。禁止采用旧文档猜测的命令名。录制和后续回放须由开发 AI 执行并记录。
- [ ] 用现有选取注入机制验证两条线：YZ@X=0和X=20，各从(Y,Z)=(0,0)到(40,0)。必须生成**边界混合曲面**，不能用实体 Blend 替代。
- [ ] 核对：完整/有效特征、1个开放 quilt、面积 `800±0.01 mm²`、边界总长 `120±0.01 mm`、包围范围X=0..20/Y=0..40/Z=0（坐标误差≤0.001mm）、无实体材料；保存重载后复核同一结果。
- [ ] 分别验证带末端点与两方向选取的最小案例：由开发AI操作UI或在build/内使用明确标记为throwaway的最小选取探针，确认原生面板能接受这些引用及相应选取API。此处不依赖Task 3尚未实现的通用协议；通用回放/角色状态在Task 3重新验收。几何案例定义见Task 5；不得用加载返回0当作完成证据。
- [ ] 确认能够区分面板完成、正常取消和未完成；若无法可靠判断空闲或执行完成，`decision="no_go"`，停止后续通用实现，报告具体缺口并评估备选方案。
- [ ] `completion_observation` 必须记录独立的结束标记、面板退出检查方法及实际返回、与新增特征出现的时序；collector证据采用已核对的界面值/高亮或编辑定义观察，配合真实父引用集合和独立几何。仅回调次数或注入成功码不是面板接受证据；无法取得必要证据则不将相关子集判为go。
- [ ] 只有以上成立才写 `decision="go"` 并冻结实测模板/摘要/适用范围；未取得目标机访问时为 `not_run`，不宣称可行性已证实。

**Deliverable:** 可以在该 Creo 10 环境重复运行的最小原生曲面证据。Task 2—6 以该结果为前提；不先发布一条未经此门槛验证的 panel 入口。

### Task 2：公开路线契约、输入冻结与准入一致性

**Files:** 修改 `surface_ops.py`、`server.py`、`capabilities.py`、`bridge.py`、`generic_bridge.py`、`native/worker.cpp`；新增 `examples/frigate_bulb_creo10_geometry.json`、`tests/unit/test_surface_loft_panel_schema.py`；扩展 `test_surface_loft_kernel_admission.py`、`test_surface_loft_runtime_observation.py`。

**Interfaces:** `SurfaceLoftOp.creation_route` 按“最小交付范围”；新增 worker 自报 `features.surface_loft_panel={available,state,supported_profile_ids}`，旧自报缺字段视为 panel 未证实，不允许 panel；新增 `bridge.surface_loft_admission_identity() -> dict` 返回复制并合并同 worker 运行观测的身份，不修改编译身份缓存。

- [ ] 先写失败回归：省略字段的旧操作序列化不变；新字段能从公开工具透传；panel 的8截面/末端点/3导线通过，而9截面、1或4导线、首端/中间点、template/非空连续条件/裸边引用/未知路线明确拒绝。
- [ ] 实现最小字段及 native 自报。后端尚未实现时panel自报available=false，不因新增字段提前开放；完成后仍将编译身份与宿主实测能力分开。按路线查询编译状态，补 `tree不可用/panel可用` 的独立准入用例，不能先用树门禁把整个操作拒掉；工具层披露可用路线及默认树的真实状态，不用一个available混淆二者。panel 的未知/旧worker/无匹配profile必须在产生建模副作用前拒绝，不落回旧元素树分支。
- [ ] 修 BUG-122 数据接线：提交前与能力报告读取相同、同 worker 的实测观测；门禁仅针对有效的 `element_tree` 请求。panel 成功不写成“元素树已支持”，不能清掉旧路径的 `unsupported` 观测。
- [ ] 使用真实 `_parse_worker_build_info()` 和实际观测生产/读取函数做离线回归：第一次不支持回执落盘后第二次树请求在 lock/job 前拒绝；支持、无观测、不同worker保持既有规则；panel 单独按新自报准入。不得继续只 mock 一个生产者不会生成的已合并字典。
- [ ] 从既有 `build/creo10_bulb_creation_20261116/geometry_only_plan.json` 冻结可分发输入：7截面与点来自反馈，3条导线完整；记录源v2 SHA、反馈输入SHA、缩比100mm/m、例子摘要。不要把 build/ 目录当发布依赖。
- [ ] 离线比较 guide/section 的真实交点：分节点区间括根二分，不用最近离散采样点冒充交点。当前输入最大分量差约 `0.004305mm`（X=7400下端），详见现有 `guide_intersections.json`；这不是原有 `Extract=-18` 的原因，也不能悄悄吸附或扩大模型精度。
- [ ] Run: `python -m unittest tests.unit.test_surface_loft_panel_schema tests.unit.test_surface_loft_kernel_admission tests.unit.test_surface_loft_runtime_observation -v`。预期全部通过；此项不替代目标机创建。

**Deliverable:** 后端选择及能力披露一致，已知旧失败不会阻止明确选择的新路线，输入有可复算来源。

### Task 3：驻留回调协议支持曲线、点和两个方向

**Files:** 新 `native/panel_selection_request.h`；修改 callback相关文件与 `blend_create.cpp`、`bridge.py` 的实际依赖清单；新增 `tests/unit/test_panel_selection_protocol.py`，扩展 `test_blend_callback.py`、`test_blend_callback_inventory.py`、`test_callback_admission.py`。

**Interfaces:** 协议升为4，contract=`blend-selection-v4-role-aware-mm`，现有 host API vtable 能满足选取时不改 loader ABI。普通 Blend 仍可用原 `curve_ids` 形状（由新worker发协议4）；panel 请求为 `{protocol,operation:"boundary_surface",request_id,model_name,profile_id,sections:[{kind,id}],guides:[{kind:"curve",id}]}`。`kind` 仅 curve/point，ID由worker从同一模型解析，不能来自任意 owner。

- [ ] 先写协议失败回归：错nonce/模型/协议、负ID、错误role/点位置、重复或超量输入、跨作业结果不得被接受；旧普通 Blend 输入的顺序与选择语义保持。
- [ ] 将请求校验及 ordered selection 状态做成无 Toolkit helper。录制模板每次激活collector后调用绑定该 `direction/index` 的专用选择命令；命令集合按首版8截面/3导线固定上限注册，不按每个job无限增加。active请求nonce、预期slot与命令ID三者匹配才允许注入，重复/跳序须拒绝；记录 `{direction,index,kind,id,code}`。不能用无参数的“下一个引用”计数器猜当前collector，也不声称callback天然知道UI焦点。
- [ ] 通用自动回放须重做Task 1的collector接受观察，检查真实父引用集合与网络几何；把注入意图与实际观察分别回执。Creo10不能取树时，不伪造真实有序输入回读字段。
- [ ] 纳入T1-A新取得的选择语义：每步显式记录 `selection_action="replace"|"toggle"`，分别映射官方 `PRO_SELECT_OVERRIDE` / `PRO_SELECT_TOGGLE`；新collector首个引用与同collector后续Ctrl追加分别验证。旧普通Blend继续保持原OVERRIDE语义，不做全局替换。toggle可能反选，因此重复/丢失确认不得靠重放“补一次”，需检查真实选集或保留不确定状态。取得原始macro后先解释3次暂停的真实作用，不把3次暂停自动映射成3条曲线。
- [ ] 结果逐阶段包含 `request_id`、`prepared`、`selected_count`、逐项记录、`selection_complete`、`ui_sequence_finished`、`released`。最后一个状态来自Task 1已实证的结束方式，不能以选择完毕推断面板已完成。
- [ ] 更新身份常量、不可变payload/loader代际和摘要依赖。旧注册的协议3与新worker混用应明确 `not_ready`，给出更新/注册说明；不自动卸载、重启或改安全设置。所谓兼容是旧**公开普通 Blend 行为**在整套升级后保持，不强行混用二进制代际。
- [ ] 回调边界不抛C++异常；检查并回传每次ProError，按现有所有权释放选取和参数数组；同一模型/同一请求不允许重入。
- [ ] Run相关新增/既有callback单测与纯原生协议helper测试；获授权后按匹配SDK构建，验证普通实体Blend与新角色选择冒烟。只有协议验证不能证明曲面已生成。

**Deliverable:** 可追踪且不串单的引用注入；已有普通 Blend 无业务回归。

### Task 4：原生 panel 后端、完成判断和事务收尾

**Files:** 新 `native/surface_loft_panel.h/.cpp`；修改 `native/generic.cpp` 最小分派/安全收尾、`generic_bridge.py` 终态判定、`bridge.py` 构建/指纹、`src/creo_mechdog/job_projection.py`/`operation_results.py` 回执投影及必要的terminal_effect接线；新增 `tests/unit/test_surface_loft_panel_state.py`、`test_surface_loft_panel_receipt.py`。

**Interfaces:** `nlohmann::json run_surface_loft_panel(const PanelRequest&, const PanelRuntime&)`。新header定义：`PanelRequest` 持有解析后同模型引用、经验证模板与nonce；`PanelRuntime` 显式传入ProSolid、模型名、job目录、resident handle、选择命令、job截止时间及现有回调调用/inspection适配函数，不读取隐藏的全局模型。新.cpp单独编译；既有全局适配留在generic入口，不做全库架构迁移。

- [ ] 先写完成状态回归：`macro_loaded`或`selection_complete`不能提交；只有本nonce的 `ui_sequence_finished`、面板退出证据和真实新特征检查完成，才允许进入保存/提交。超时不补发同一宏。
- [ ] 在创建前验证profile、callback实时身份、当前模型及引用owner；缺任何前置则保持模型/revision，返回具体准备指引。实际模板只来自分发白名单和SHA校验，不接受客户端传入任意宏字符串。
- [ ] 按Task 1模板加载宏并等待该请求完成；等待预算不超过原job剩余deadline，不开第二Toolkit通道，不从后台线程越过现有调用上下文。
- [ ] `ui_sequence_finished` 由录制并验证的Done之后的独立尾命令触发，携带当前nonce，只是候选完成栅栏；仍须Task 1定义的面板退出观察与新增特征几何同时成立。Done未成功而尾命令执行时，不能当成功。未观察到尾命令时不得随意Release/恢复模型来“解除等待”。
- [ ] 对比before/after：唯一新增目标特征、状态有效且 `ProFeatureIsIncomplete=false`，存在目标quilt和正面积，实体材料未增加。只看模型已有quilt不算成功；多出意外特征/面组也应拒绝并按现有事务恢复。
- [ ] 结果带 `creation_route="resident_panel"`、profile/nonce、`macro_load_code`、选取回执、feature/quilt/面积与状态；`element_tree_extraction.executed=false`。不伪造 `create_code=0`/`extract_code=0`，不把panel成功写进旧树运行观测。
- [ ] 补原生 `input_geometry_check` 与 `network_geometry_check` 测量回执：从真实section定义回读次数/节点/权重/控制点并按placement转换，不能复制aliases输入当回读；对源曲线取样后，以 `ProSurfaceParamEval` 查最近UV、`ProSurfaceUvpntVerify` 检查有效面域，再重算XYZ距离（先核对目标SDK声明/契约）。底层无限延伸面上的投影不等于实际face；未落入有效域且未验证真实边界最近点时标记距离未验证，不能计为通过。保存重载后重复测量；compact保留最大值/数量/状态和原始API失败，详细数据置作业附件，预算仍32KiB。
- [ ] 接入既有保存重载和revision收尾；锁内完成验证、持久终态后按既有约定发布。成功必须 `saved_file_reloaded_and_verified=true`。
- [ ] 对正常取消，仅在确认面板关闭、引用释放、模型/文件/revision恢复后报失败回滚；未确认则沿用 `unknown_outcome` 保护，不假报安全回滚/可重试。无创建副作用才能报no_effect。
- [ ] 显式接通未知终态：native报告 `success=false, panel_execution_unconfirmed=true, rollback_succeeded=false`，跳过可能与活动面板冲突的checkpoint重载/新模型erase；`generic_bridge`在成功/普通失败分支之前识别该可信原生标记，登记 `status="unknown_outcome"`、保留pending_job且不增加revision，沿用通道健康/模型保护。`delivery_complete`只描述结果投递，不能替代面板状态。补回归：即使进程正常退出、disconnect=0、结果投递完成，执行未确认仍必须为unknown；历史无标记结果保持既有行为。
- [ ] Run新增状态/回执测试、单通道与revision相关既有回归；获授权后运行最小panel实机。单测模拟状态只证明软件契约，不替代UI完成时序证据。

**Deliverable:** 用户得到的是已验证、已保存的原生曲面，而不是宏加载成功或不完整空壳。

### Task 5：Creo 10 球鼻艏几何与保存重载验收

**Files:** 新 `tools/test_creo10_bulb.py`，扩展必要的离线driver测试；运行证据在 `build/bug120_creo10_bulb/<run>/`。

**Interfaces:** driver默认仅离线输出/验证输入，只有显式live参数及用户当次授权才连接。使用现有公开工具和新 `creation_route="resident_panel"`，不使用猜测树节点。

- [ ] 固定下列矩阵，每次单独临时模型/基线；记录实际调用、源码提交和dirty、源码指纹、worker/回调/profile摘要、宿主环境、job/model/revision、保存文件SHA、几何、终态及未测范围。

| 用例 | 单变量目的 | 事先确定的成功依据 |
| --- | --- | --- |
| A：两条40mm线，X间距20mm | 最小面板曲面路线 | Task 1的800mm²、120mm周长、范围、完整性和重载 |
| B：A加入X=10的同一共面40mm线 | 第三截面与smooth | 仍为800mm²；三截面真实通过，非分片或实体替代 |
| C：B仅加入末端点(X=30,Y=20,Z=0) | 点选择/收敛 | 有效单quilt，指定点位于收敛边界；各截线/尖点到面距离≤0.01mm，不预填未知面积 |
| D：A加入沿X方向的Y=0/40边界导线，再加Y=20导线 | 第二方向及2→3导线 | 分别2、3条都真正选入；仍为800mm²，导线到面距离≤0.01mm |
| E：7曲线截面，无尖点/导线 | 目标截面能力 | 单quilt，逐站截线到面距离≤0.01mm，肩部截线保留 |
| F：E仅加入末端尖点 | 隔离真实端点收敛 | 在E基础上尖点正确，无不完整/失败特征 |
| G：F加入3条完整导线 | 完整B030 | 8截面含末点、3导线；截线/导线/尖点到面最大抽查距离≤0.01mm；完整性、边界和重载通过 |
| H：G镜像、合并、后端封盖、实体化 | 最终球鼻艏 | 一个有效封闭实体、无开放边、正体积、Y对称、源截线和位置保持，保存重载一致 |

- [ ] 坐标单位固定100mm/m；阈值0.01模型mm等于原尺寸0.1mm。输入重建先核对次数、节点、权重、原生曲线/控制点（位移≤0.001模型mm），不得用aliases保存的输入当原生回读。近尖点采样避开参数退化，但必须独立核对尖点本身。
- [ ] 距离判定使用原生曲面/曲线投影或带误差说明的独立截面测量；抽查每条非零节点区间和端点，记录数量与最大值。只证明所测位置，不把抽查最大值声明为全表面误差上界。
- [ ] G失败时对照E/F/D定位接口、点、collector或交点容差；保留约0.004305mm输入间隙事实。若确需调整曲线，另写有来源、位移上限和前后几何的适配提案；不自动吸附、不放宽既定验收凑通过。
- [ ] H检查 `surface_group`真实闭合/边界及实体材料；以原生曲线取样和七站位反映外形。体积/面积与已有12.4参照按长度比s、面积s²、体积s³对照，仅作异常诊断；不因体积近似就宣称与SW全表面一致。
- [ ] 正常取消案例验证恢复后合法请求可成功；错profile、旧callback、陈旧nonce在副作用前拒绝。不要通过杀进程/清保护来构造或恢复失败。
- [ ] Run: 先driver离线检查，再在获授权的目标10环境运行其live模式；按本次改动运行适用开发检查/构建/相关原生驱动。12.4只做旧树和普通Blend的相关回归，不用其结果替代A—H。

**Deliverable:** A—H的目标环境证据。只完成A或只在12.4通过时，不关闭BUG-120成型修复。

### Task 6：能力说明、WorkBuddy黑盒与交付

**Files:** 更新 `README.md`、`docs/REFERENCE_SYNTAX.md`、能力说明、BUG-120/122和BACKLOG；新增 `docs/development/WORKBUDDY-BUG120-CREO10.md`；更新模板发布白名单/打包测试。

**Interfaces:** WorkBuddy只使用已发布/受测公开MCP工具：确认工具/版本和回调状态，创建A和目标G/H、查询job、检查几何/revision/重载；隐藏构建细节若公开接口未提供则记无法确认。

- [ ] 写清panel已验证的版本/语言/profile和输入子集、一次性回调准备方式；工具描述说明默认树与显式panel，不把compiled/ready当几何通过。
- [ ] 黑盒提示词只给MCP场景、输入、预期和报告格式；不得要求WorkBuddy查源码、运行本地driver、读取配置或录制研发用mapkey。若回调未加载，报告前置未满足及操作指引，不代替用户审阅DLL提示。
- [ ] 核对源码包包含新原生文件、helper、模板及冻结例子；白名单按bytes/SHA校验，不发行build/jobs、模型、SDK或本机常量表。缺模板、损坏摘要、未列入模板须打包失败。
- [ ] 以适用检查、目标10实机、黑盒结果分别更新状态；保留部分完成和未测事实。BUG-122保护修复与BUG-120成型成功分别验收，均不顺带关闭BUG-130。
- [ ] 开发分支阶段不擅自合main/发布；实际合入main时依AGENTS及RELEASING完成新版本、Release、附件和远端校验，不复用已发布版本号。

**Deliverable:** 可交付、边界准确且可由最终用户复测的Creo10原生创建能力。

## 建议执行方式与阶段结果

推荐先由**能访问目标 Creo 10 GUI/SDK 的开发 agent**执行Task 1。它是本计划最关键且无法由本机12.4替代的依赖；不是让WorkBuddy黑盒去做源码/宏研发。

Task 1通过后再推进Task 2—4；其中协议helper/测试与输入冻结可分给独立agent，原生面板与事务由同一实现者统筹，避免两个agent同时操作唯一Toolkit通道。Task 5负责实际成型闭环，Task 6收口。若Task 1失败，先带证据讨论内存NURBS或仅几何交付，不能静默改变目标。

本次仅编写方案文件与进行离线交点计算：未写产品实现、未构建、未连接Creo、未改变用户模型或保护状态。方案自审覆盖了旧调用、旧worker/回调、角色顺序、异步完成、输入间隙、未知结果及目标机验收；相关用例均有明确归属。
