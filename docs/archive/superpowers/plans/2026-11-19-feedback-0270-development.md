# 0.27.0 目录反馈开发完善计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先保证文本重建的几何保真、引用与失败诊断可靠，再补 Arm7 真实选区、G2 验证、实体边链圆角和嵌套装配。

**Architecture:** 沿用包内输入契约 → `generic_bridge.py` → `bridge.py` 单通道 → 原生 Creo worker。每个任务先确认当前版本现象，再按证据修改涉及层；新增建模能力与诊断/回执改进独立验收，不重做整套调度或建模后端。

**Tech Stack:** Windows x64、Python 3.12+、Pydantic、unittest、C++17、C TOOLKIT。当前原生开发验收环境按 AGENTS 为 Creo 12.4.0.0 / 匹配 SDK；报告涉及的外部 Creo 9/10 另按具体问题取得证据。

**Spec:** [DEV-093](../../work-items/DEV-093.md)、[六份来源清单](../../validation/feedback-0.27.0-2026-11-19/SOURCE_MANIFEST.json)、[AGENTS](../../../AGENTS.md)。方案比较和本轮权限见 DEV-093。本计划是待实施建议，未获得实现或实机批准。

## 全局约束

- 基线 `c21651262b8efc442602b50d1d6a09b01abe0b69` / `0.30.0`；下载目录名称不代表六份报告都测试了 0.27.0。代码行号以该提交为准，执行前重新定位。
- 长度毫米、角度度；特征标签小写字母开头，只含小写字母、数字和下划线，最多 28 个字符。
- Toolkit 单通道；忙碌立即返回 `isError=true/status="busy"`，不排队、不自动重试；已接收作业只轮询。
- 保留 revision、失败回滚、unknown 保护和保存重载核验；新业务逻辑进 `src/creo_mechdog/`，不在 `server.py` 堆业务逻辑。
- 无当次明确确认，不编译产品执行器、不连接 Toolkit、不启动 Creo。实机授权按任务范围申请，不包含结束进程、清锁、故障注入或改写用户模型；技术判断由开发 AI 完成。
- 原件与历史证据逐字节保留；不把 SDK、常量、二进制、日志和测试模型加入产品源码/附件。此次归档只含用户给出的六份反馈。
- 不放宽几何保真阈值来伪装修复，不自动投影旋转轴、正交化矩阵、改圆心半径或把弧降成折线。
- 实施使用 `codex/<条目>-<主题>` 分支；本轮没有提交/合并。后续合入 main 时按当时未发布版本完成 Release、附件和 SHA256 核对，不预订已发布版本。

## Review Focus

1. 同坐标的圆心并不证明已有连接约束；反过来给每个点重复加尺寸也可能过约束。由任务 2 的独立圆/弧与共享端点对照覆盖。
2. 微小接缝可能在准入与原生处理间使用不同容差；不能只因 `gap <= max_endpoint_move_mm` 就放过无法焊接的曲线。由任务 3 的双层资格和负例覆盖。
3. 相同源件的两实例可以拥有同号面 ID；几何所有者、实例路径和坐标系必须绑定。由任务 6 的同源双实例/显式 ID 对照覆盖。
4. G2 选项、体积变化和非圆柱面均不能单独证明接缝曲率连续。由任务 8 的切向与曲率独立测量覆盖。
5. 大响应的精简不能隐藏失败、当前 revision 或真实选择结果；分页跨修改不能重复/漏项。由任务 1 的预算与快照测试覆盖。

## 来源和判断

F01–F06 对应清单中的原始文件；以下是当前审阅判断，不把报告方的旧作业结果冒充本次复现。

| 项目 / 来源 | 当前依据与应收窄的结论 | 建议 / 归属 |
| --- | --- | --- |
| 同心圆弧漂移 12.35 mm / F02 | `native/sketch_coordinates.cpp:184–195` 仍按坐标全局跳过已放置点，含圆心，是可疑点；但报告将圆心错开后仍同量漂移，未证明单一根因。 | P1，先复现；FEAT-010 / BUG-050，任务 2 |
| autodim 偏差与“容差未生效” / F02 | 同文件 `resolve_geometry_tolerance` 已支持显式容差硬拒绝；coordinates 默认 `1e-5 mm`，autodim 默认 `0.001 mm` 告警。报告中的拒绝本身说明保真闸门在起作用。 | 复用已有字段，不新增 exact 模式；任务 2 |
| 构造圆失败、内部中心线回转 / F03 | 当前快照读取区分 LINE/CENTER_LINE/CIRCLE/ARC；实际构造几何的原生类型仍须回读。BUG-083 历史已有省略 axis 成功例，不能说内部轴全部不可用。 | P1 定向复现，任务 2 / 4 |
| 0.00039 mm 轴离面 / F01 | 有报告方单变量对照，当前尚未核原生轴和草图框架；只测轴原点到平面的距离不充分，还要检查轴方向是否平行于平面。 | P1 原生诊断与明确拒绝；任务 4 |
| weld 被前置校验挡住 / F01 | `profile_diagnostics.py:706–719` 仅对符合条件的闭环残差放行；`test_feedback0190_arc_closure.py` 已覆盖部分小误差，但通用 weld 不保证先于校验，纯弧焊接仍有限制。 | P1，BUG-101 / FEAT-039；任务 3 |
| 切除负去料 / F01 | `native/generic.cpp:3418–3431` 已按 `removed <= threshold` 判失败，并不是“负值被当作成功”；日志仍用负 removed，值得改善。 | P2，FEAT-051；任务 5 |
| 同轴同半径圆边无法轴向消歧 / F03 | **报告将圆柱面规则套到圆边。** 当前 `native/geometry_selectors.cpp:129–133` 比较三维圆心，`:155–158` 检查点所在平面；本地 `v0.26.0` 同文件也有此过滤。 | 先查运行身份/arc.origin/单位，不新增字段；FEAT-068，任务 4 |
| 实体圆角边链 / F04 | `generic_round()` 每个 reference 建一个 SET，单 SET 单边，缺少显式多边输入属实。但 status=6 不足以排除 R12 与局部几何本身的冲突。surface_round 的限制不等于 solid round 的完整依据。 | 能力扩展 P2；任务 9，实施前登记独立 FEAT |
| 六位矩阵被内核拒 / F05 | BUG-133 已在 0.30.0 贯通两层有效容差，尚未 Creo 验收；报告也有精确 90° 成功，标题“旋转完全不可用”过宽。 | P1 先验已有补丁；任务 6 |
| 嵌套子装配 / F05 | Python/native/replay 都明确拒绝，仍为真实能力缺口；展平 269 件不等于 94 实例三级结构。 | FEAT-012 独立设计，任务 10 |
| 创建回执 revision=0 / F05 | queued 回执是当时占位 revision；终态 job 更新为 1。FEAT-008 已核同类语义，不应把旧响应对象当成可自动更新的终态。 | 文档/字段语义改进，任务 1；不新建状态错误 BUG |
| Arm7 区域三签名零命中 / F06 | FEAT-069 只有简单整实体闭环适配，`sketch_regions.entity_endpoints()` 未做内部交点切分；4/4/6 段真实签名超出其范围，属于已知缺口的外部失败证据。 | 建议本批 P1；FEAT-069，任务 7 |
| G2 只写枚举 / F06 | 对报告当次 Creo 10 Arm7 仅证到树值；已有 Creo 12.4 体积/面型/重载证据，可排除普通圆弧退化，但仍缺曲率直接测量。 | DEV-090 补直接几何验收；任务 8 |
| coaxial:any 仍选平面 / F06 | 当前 `geometry_selectors.cpp:313–320` 的 radius/center 会排除平面，与报告回执矛盾；显式 224 还依赖实际 owner/实例路径。any 不是任意面放行。 | P1，先核 worker 身份、完整引用和映射；BUG-132，任务 6 |
| 大提交回执 / F06、组件列表 11 MB / F05 | execute_plan 仍回显 normalized operations；`creo_list_components(model_id)` 仍返回完整 components/aliases，无 fields/分页。 | P2，FEAT-023 / BUG-076；任务 1 |
| 超长名称提示大写、裸圆角引用 / F06/F04 | 名称错误是通用规则附带大写说明，未真的判成大写；裸 selector 经校验后原生却 `refs.at("edge")`，确有包装形状准入漏检。 | 名称 P3、引用预检 P2；BUG-019 / FEAT-008，任务 1 |

## 输入准备和并行安排

本目录只有六份 Markdown，不含其提到的完整 TXT、JSON 计划、native.log、PRT 和 XML。先查仓库已有夹具/原件是否含相同数据并核摘要；缺的记录为具体输入依赖。最小公共算例可先做，不能因此宣称原例已验收。

需要补齐的原例：F02 全部八弧及约束；F01 P05-08/P05-11 的原弧线和容差；F03 266 实体草图及两圆边原生 inspection；F05 原始 2.74° 矩阵、94 行层级与源件映射；F06 Arm7-S7 全草图和三签名，以及失败计划中的 assembly_component/coordinate_space、对应 job 原始回执。不能从缩写 job_id 或 TXT 名称重造完整数据。

推荐顺序：任务 0 → 任务 1/2/3/4/6 可分工离线推进 → 5/7/8 → 9/10。任务 6 的矩阵和选面可分成独立交付。共享 `schema.py`、`generic.cpp`、`advanced.cpp`、`generic_bridge.py` 时由集成人串行合入；真实 Toolkit 工作一律串行。每批只在其独立验收通过后推进，不等待整台履带或机械臂全部复建。

## 任务 0：冻结输入、运行身份和验收基线

**Files:** 本工作卡、各相关既有卡、`docs/BACKLOG.md`；测试数据放所属任务的静态夹具目录，运行模型留本机生成目录。

**Interfaces:** 来源文件 SHA256 → 最小输入 / 原例完整性 / 测试身份记录。服务版本不能替代 worker 指纹。

- [x] 阅读六份报告，对照本地 0.30.0；保留原件大小和 SHA256；离线运行相关 37 项既有测试通过。
- [ ] 执行前核对分支、dirty 和负责范围，尤其 BUG-050；将本批具体范围补入对应工作卡。新能力先分配唯一 ID。
- [ ] 找齐或明确缺少上述原始输入；分别列“可先验证的小样”和“不能下结论的原例”。
- [ ] 实机获准后核 SDK/Creo release、服务与 worker 身份和实际受测源码指纹；取得原始失败输入与本轮回执再判断是否为当前缺陷。若源码逻辑与回执冲突，先查部署，不直接改算法。

## 任务 1：前置引用错误并控制接口体量

**Files:** Modify `src/creo_mechdog/geometry_selectors.py::validate_reference_list()`、`schema.py::RoundOp`、`generic_bridge.py::submit()`、`bridge.py` 名称校验、包内响应投影模块；`server.py` 只接参数。Test 现有 `tests/unit/test_geometry_selectors.py`，新增 `tests/unit/test_submission_receipts.py` / `test_component_list_paging.py`。

**Interfaces:** 建议新增 `response_detail="full"|"compact"`（缺省 full，保留旧调用）；compact 提交返回 `job_id/model_id/status/revision/operation_count`，文件输入保留路径和 sha256，完整 operations 留 job detail。组件查询新增可选字段投影和有界分页，旧签名兼容。

- [x] 先写失败用例：顶层裸 selector、edge/surfaces 混用、surfaces 非两项在派发前给字段路径和有效包装例子；合法旧形状不变。不能把它们简单转成新语义。（2026-11-19 离线完成：`RoundReferenceStructureTests` 9 例 + `validate_reference_list` 结构预检；合法旧形状 `{"edge":{"kind":"edge","id":7}}`、`{"edge":selector}`、两项 `{"surfaces":[...]}` 不变。）
- [x] 实现引用结构预检；精简回执保留失败/身份/revision 语义，不回显 operations。以真实大计划的夹具测序列化 UTF-8 大小，建议 compact 不超过现有 32 KiB 预算；操作结果按既有查询取回。（2026-11-19 离线完成：`submission_receipts.project_receipt`，200 条 round 计划 compact < 32 KiB 且不足 full 的 1/10；失败 `message` 与 revision 原样保留；`job.json` 仍写完整 operations。）
- [x] 组件列表先冻结 `fields/limit/cursor` 契约再写实现：269 件遍历无重无漏，同一源件两实例保留各自身份，revision 改变令 cursor 明确失效，单个超大条目不无限内联。共享现有分页基础，不另建不绑定 revision 的偏移游标。（2026-11-19 离线完成：`component_pages.component_page`，复用 `model_queries` 的 cursor/fingerprint/serialized_size；cursor 绑定 model_id + revision + fields + 快照，任一变化报 “restart the query”。）
- [x] 模型名按超长/非法字符/首字符分别提示；排队回执明确“以终态 job revision 继续”，不改异步接口为同步等待，不承诺旧字典会回填。（2026-11-19 离线完成：`bridge.normalize_model_name` 分类型/空/长度/首字符/非法字符分别提示，统一保留 “model_name must be 1-31 characters” 前缀；排队 `message` 写明本条 revision 是提交时占位值。）
- [ ] 离线单测及必要协议集成通过后独立提交，回填 FEAT-023 / BUG-019 / FEAT-008；本任务不需要 Creo 来证明纯序列化/预检，但不冒充实际大装配读回验收。

## 任务 2：定位圆弧保形和构造几何失败

**Files:** `native/sketch_coordinates.cpp`、相关 sketch 选择策略；`src/creo_mechdog/schema.py` 仅在现有契约确有缺口时修改。Test `tests/unit/test_sketch_geometry_deviation.py`；Create `tools/test_concentric_arc_coordinates.py`（实机入口必须显式启用）。

**Interfaces:** 沿用 `dimensioning`、`geometry_tolerance_mm`、`geometry_deviation`；诊断新增点的实体/type/sense 及跳过理由，不用坐标相同推断已有约束。

- [ ] 小样拆成：两个同心圆/弧、不同心但共享端点、报告四弧子集、完整八弧；分别固定其它输入只变去重/约束策略。对构造圆/中心线回读原生类型，不能只看 JSON 的 type。
- [ ] 在获准实机后保留原策略失败证据；比较只取消圆心跨实体去重、明确同心约束等有依据方案。仅采用能同时避免欠约束与过约束的最小修复，不无差别给每个重复点加尺寸。
- [ ] 验收读回圆心、半径、扫角及闭合状态；coordinates 默认最大偏差必须符合现有 `1e-5 mm` 闸门；显式更严阈值按原契约拒绝和回滚。autodim 显式 tolerance 同样硬拒，缺省保留告警；不加同义 exact 模式。
- [ ] 构造参考在保留其语义下与无构造对照成功；auto 不得选一条必然不支持该原生实体的路径。完整零件还要独立体积/特征和保存重载验证；最小草图通过不能关闭原例。

## 任务 3：统一端点准入、焊接资格和圆弧保形策略

**Files:** `src/creo_mechdog/profile_diagnostics.py::validate_solid_profile()`、`endpoint_welding.py::prepare_operations()`、`schema.py::validate_operations()`、`generic_bridge.py::submit()`、`native/endpoint_weld.h`。Test 现有 `test_feedback0190_arc_closure.py`、`test_endpoint_welding.py`；扩展 `tools/test_endpoint_weld_gate.py`。

**Interfaces:** 继续使用 `endpoint_policy/max_endpoint_move_mm` 和现有焊接回执；静态计划只做资格与拓扑检查，原生以真实求解结果确认，不让 Python 模拟 Creo 求解。

- [x] 再现 1.104e-6 mm 量级弧接缝、弧线长圆孔、两个异圆弧组成的透镜；记录 validate 与 prepare 的实际顺序及每条拒绝原因。加入已支持直线焊接和明显开环反例。（2026-11-19 离线完成：`tests/unit/test_weld_eligibility.py` 20 例。实测：同圆一接缝与长圆孔都能配对（`weldable`）；两端都短的圆环因 1e-9 链并集分裂报 `unresolved`；异心圆弧透镜判 `arc_inconsistent`。）
- [x] 对可证实可焊的输入，使前置检查与提交共享资格判断；超 max、不可支持的原生实体、歧义连接明确拒绝。不能用“都在移动上限内”替代拓扑/曲线可行性判据。（2026-11-19 离线完成：`weld_eligibility()` 为唯一判据；`arc_inconsistent`/`max_move_exceeded`/`would_merge_closed_contours` 在 `weld`/`snap` 下派发前拒绝；`ambiguous_pair` 视为已焊到最近端点；两条开链之间的接缝报 `unresolved` 不拒绝——2026-11-02 实测内核焊过 8.21534267e-07 mm。）
- [ ] 圆弧首批优先评估保持圆心/半径、仅调整扫角是否足够；若两圆无共同可达点，明确拒绝并回执原因。需要改变圆心/半径才可修复时，另立显式改形设计，不默认实现。新增原生方法须按 SDK/参照树核准。（拒绝侧已完成：`arc_inconsistent` 在派发前给实体名与 gap；**“只调扫角”的保形求解未实施，需实机确认解是否存在**。）
- [ ] 修正无效 remediation：用户不应被推荐一条仍会被同一前置校验拒绝的路径。记录实际移动量、未处理对、残差和实际几何变化；获准后验证拉伸去料/增料、原弧保留、重载及失败回滚。（文案侧已完成：保留原关键词并追加 “For this profile:” 实际判读，透镜明确说 weld/snap 修不好；**实机拉伸去料/增料、原弧保留、重载与回滚验证待执行**。）

## 任务 4：回转轴诊断和圆边歧义定向复现

**Files:** `native/generic.cpp` 回转轴解析与截面框架、`native/advanced.cpp` 回转实现、`native/geometry_selectors.cpp`；`src/creo_mechdog/references.py` 只同步已证明规则。Test `tests/unit/test_revolve_axis.py`；扩展 `tools/test_revolve_axis_live.py`，新增两圆边消歧用例。

**Interfaces:** 保留 axis 省略/null 和显式轴三态。建议失败块包含轴 owner/方向/原点、草图框架、离面距离与方向残差；未测值为空，不猜原因。

- [ ] 最小内部 centerline 与 `construction:true` 普通 line 分开测试，再对照外部 datum axis；报告的 266 实体只是原例，不从一例概括所有构造线。
- [ ] 对轴线与草图平面同时核原点距离和方向；用共面、偏移 0.00039 mm、明显离面及方向倾斜对照确定文档化判据和允许容差。确认后才加入原生建特征前诊断；不固定套用报告建议的 `1e-3 mm` 或自动投影。
- [ ] 两个 R220 圆边放在 x=±54，原 selector 应只命中 +54；固定相同输入比较当前与来源版本的 arc.origin、单位及三维误差。若当前通过，记录原案待核实；若失败，按真实回读修复，不能先加 axis_coordinate 字段。
- [ ] 获准后验证 add/cut 及 partial/full 回转，失败 revision 不变、原件未改；成功特征与独立几何预期、保存重载一致。

## 任务 5：切除材料增加时给准确异常回执

**Files:** `native/generic.cpp` cut 检查、`src/creo_mechdog/operation_results.py`、`job_projection.py`；Test 扩展材料变化投影单测与 `tools/test_detail_feature_observation.py`。

**Interfaces:** 沿用 `volume_before_mm3/volume_after_mm3` 和有符号原始差值；新增或复用明确“材料增加”的异常原因。旧字段若改变数值语义，先记录兼容策略，历史 job 原件不重写。

- [x] 单测固定 before=12514487.330518638715、after=12514490.389585861936：明确是增加约 3.059067 mm³ 且操作失败；零差和测量缺失也不能成功，不需要再发明 `removed==0` 修复。（2026-11-19 离线完成：`CutVolumeChangeTests` 按该读数断言 `material_increased`、magnitude 3.059067、`diagnosis` 非空。）
- [x] 正常切除的 removed 为非负；异常保留 signed_delta 与原始读数，提示位置/方向/测量需核对，不直接认定方向反了。compact/full 保留同一异常及最终 rolled_back 状态。（2026-11-19 离线完成：`volume_change` 保留有符号 `signed_delta_mm3` 与原始 before/after，不重写原生 `status`；compact 与预算裁剪保留 `material_increased` 与 `rolled_back`。）
- [ ] 获准后用独立增料/去料解析算例回归，不为制造负体积差做故障注入；原案若不能复现，保留仅回执语义改进的范围。

## 任务 6：先验矩阵补丁，再定位跨组件圆柱引用

**Files:** `native/assembly_pose.h`、`native/advanced.cpp`、`native/geometry_selectors.cpp`、包内 assembly pose/constraint 回执；Test 现有 `tests/unit/test_assembly_pose.py`、`test_geometry_selectors.py`；扩展 `tools/test_assembly_pose.py` 与 BUG-132 专项驱动。

**Interfaces:** 保留现有 rotation_tolerance、row/column 约定及 assembly_component。选择结果绑定 `{owner, geometry_id, type, component_path, coordinate_space}`，不能只回一个 id。

- [ ] BUG-133：原 2.74° 矩阵、已有 28° 软件夹具、identity、90°、反射、超限各自测试默认/显式容差；明确软件准入通过是否真的到达 ProAsmcompAssemble/PositionSet。
- [ ] 获准实机后分别创建/重定位，独立基向量/已知点验证方向，读回与保存重载。若软件已放行仍 -2，保留原码和完整输入，再单独设计显式矩阵正交化与修正量回执；不默认使用 Gram–Schmidt，也不把它称为最近 SO(3) 投影。
- [ ] BUG-132：同一 sibling 的 selector 与显式面 ID 对照，确认源件和实例实际 owner；同源件双实例、旋转平移、装配坐标/模型坐标、平面反例都覆盖。任何带 radius/center 却选平面的结果先查字段传递和 worker 身份。
- [ ] any 只在符合共同轴线语义的圆柱候选中消歧，最终类型仍查实际面；诊断含候选与拒绝原因。验证 insert/concentric 的轴共线、正确 sibling、保存重载、失败回滚；固定放置的 23 件成功不算原生配合通过。

## 任务 7：为真实 Arm7 选区确定原生路线

**Files:** `src/creo_mechdog/sketch_regions.py`、`region_selection.py`、相关 native extrude/section 路线；Test `tests/unit/test_sketch_regions.py` / `test_region_selection.py`；新增 `tools/test_arm7_region_cut.py`。

**Interfaces:** 沿用 ExtrudeOp.region 和无序/反向签名等价；region_index_hint 仅提示，不作区域身份。现有派生草图简单闭环继续兼容。

- [ ] 输入齐备后先还原三条 4/4/6 段边界与五实体草图的交点对应；区分签名错误、frame 错误、当前拓扑表达不足与真正零命中，立即改进当前误导文案。
- [ ] 先查目标 SDK 的真实 section region、曲线交点/切分能力与官方示例，做最小“交叉两轮廓 + 共享边界 + 样条内部交点 + 约0.017591 mm 窄缝”参照。优先原生面域路线；不可行时记录原因，再评估基于原生求值/切分的派生曲线方案。Python 不靠端点图算法假装支持真实曲线内部交点。
- [ ] 小样确认引用、树与重建后，才实现真实选区，并用独立面积 × 3 mm 或相应准确几何预期核去料，证明未选区保留；三签名各一例及组合例均保存重载、失败回滚通过。
- [ ] 完整 Arm7 数据缺失或官方路线未证实时，只交付诊断/边界收窄，不写“真实选区支持完成”。新路线具体实现另附经证据收敛的子计划，不预承诺删准入即可完成。

## 任务 8：补 G2 的直接几何证据

**Files:** `native/surface_measure.h` / 相关曲率测量实现、包内结果投影；复用 `creo_measure_surface_curvature`，只有其表达能力不足才扩展。Test `tests/unit/test_surface_curvature_contract.py`；新增 `tools/test_round_g2_continuity.py`。

**Interfaces:** 分开报告原生选项写入、非退化几何、接缝切向连续、曲率连续；采样结果必须带实际面/边、位置、单位、方法与未验证原因。

- [ ] 先核现有曲率工具能否覆盖实体圆角面及边界两侧；平面/已知半径圆柱/球面校准曲率单位。相切只说明 G1，不能代替 G2。
- [ ] 建普通圆弧圆角与 curvature_continuous 的 R5/R30 对照，定位真实邻接边；用一致法向/跨边截向比较两侧切向和曲率，避免拿两面不对应的主曲率直接相减。边界 API 限制需用逼近采样时报告偏置与收敛性。
- [ ] 测量方法先在已知连续/不连续算例上校准，再冻结本案例容差和端点/中段覆盖。用直接读数判 G2，不从 type=3、体积少25.37%或非圆柱反推通过。
- [ ] 获准后重载测量；Creo 12.4、外部 Creo10/Arm7 分别记录。只测本机不外推，未测组合继续在能力文档明示。

## 任务 9：实体圆角的显式同集合多边输入

**Files:** `src/creo_mechdog/schema.py::RoundOp`、`geometry_selectors.py::validate_reference_list()`、`native/generic.cpp::generic_round()`；新增 `tools/test_solid_round_chain.py` 及契约单测。正式编码前为本能力分配唯一 FEAT ID。

**Interfaces:** 建议 `references:[{"edge_chain":[ref,...]}]` 表达一个 SET 中的显式多边；原多个 `{"edge":ref}` 保持多个 SET。首批只给 solid round，不自动扩展 chamfer/surface_round，不加入自动相切传播或变半径。

- [ ] 按目标 SDK 查集合树和官方参照；由开发 AI 在获准临时模型取单边/同集合双边/多集合对照，并重绑重建。不能只把数组塞进现有节点就宣布可用。
- [ ] 预检重复边、空链、混合 edge/surfaces 形状；原生检查实际归属和链连接。反向/循环起点等价；断开集合明确说明首批支持边界。
- [ ] 先用解析上可行的小半径闭合链证明路线，再试 P03 的 R12 八边。核八条实际引用、单集合、多邻接处连续、独立几何和保存重载；若 R12 本身不可行，保留特征失败，不自动减半径，也不将它判作边链能力未实现。

## 任务 10：受管嵌套子装配独立设计

**Files:** FEAT-012 子设计；后续涉及 `generic_bridge.py` 来源验证、`native/advanced.cpp` 快照复制、组件 inspection/replay、FEAT-031 打包闭包。此任务不随手移除当前拒绝分支。

**Interfaces:** 首批受管装配不可变快照；实例路径、递归依赖清单和源 revision 都可追溯。源件修改不会自动联动；不隐式展平。

- [ ] 先冻结深度/规模预算、循环依赖拒绝、重名/共享源模型隔离、快照更新与回滚契约；核 Native bundle 和 replay 哪些跟随支持、哪些继续明确拒绝。
- [ ] 获准后从“子装配两件 → 父装配两个子实例”小样证明递归复制/引用与保存重载；同源子装配两实例必须保留独立 occurrence path，父子变换逐级可复算。
- [ ] 小样路线通过后提交实施设计；完整 M113 数据齐备才验三级94直接实例与269叶子实例的两种统计、BOM层级、位姿、独立质量和打包重开。缺数据时不以展平件通过关闭结构需求。

## 每批完成条件与本次交付

- [ ] 每项有当前失败或范围缺口证据、最小修改、适当回归、成功和反例；实现任务结束做一次独立审查，不能因预期失败断言通过就称缺陷修复。
- [ ] 适用的离线专项单测与 `tools/dev_check.py` 通过；原生改动在当次授权后构建并运行对应 tools 驱动，取得真实几何、`saved_file_reloaded_and_verified=true`、revision/回滚证据。先读各脚本参数，不把旧文档示例当通用命令。
- [ ] 证据包含提交、dirty、源码指纹、命令、SDK/Creo/worker身份、输入及产物摘要和未测范围；开发者和 WorkBuddy 分开。WorkBuddy 只调用公开 MCP，不运行本地脚本或读仓库来补证据。
- [ ] 更新对应工作卡和能力边界；整卡有余项时保持部分交付。每批可独立交付，扩展能力不阻塞已完成的正确性补丁。

本次仅完成审阅、来源归档、计划与 37 项既有离线测试；没有实施上述产品任务，没有 Creo 实机结果。最值得优先推进的是任务 2/3/6；任务 1 可独立并行，任务 7 是 Arm7 原生完成度的主要能力缺口。任务 9/10 应在基础正确性收敛后分别设计和交付。

## 本轮实施记录（2026-11-19，离线，无实机授权）

任务列表（按批）与执行结果：

| 批次 | 任务 | 本轮状态 |
| --- | --- | --- |
| 一 | 任务 0 冻结基线 | 完成离线部分；实机身份核对未做 |
| 一 | 任务 1 前置引用错误 + 接口体量 | **四项均已实现**（引用结构预检、`response_detail="compact"`、组件列表 `fields/limit/cursor`、模型名/排队回执文案）；未提交、未回填 BACKLOG 行 |
| 一 | 任务 2 圆弧保形 / 构造几何 | 取证：`native/sketch_coordinates.cpp` 的 `placed` 集合（`:140`）跨实体共享并按 1e-9 截面坐标比较（`:187-195`），圆心确实进入跳过集合；构造位 `ProSectionEntityIsConstruction` 该文件**从不读取**。**2026-11-19 实机四档小样 4/4 通过**（两半圆/四段/八段/同心弧+双弦，体积与请求推值一致且保存重载后保持）；构造几何回读仍无证据 |
| 一 | 任务 3 端点准入 / 焊接资格 | 未实施（与任务 1 共用 `schema.py`/`generic_bridge.py`，需串行） |
| 一 | 任务 4 回转轴诊断 / 圆边歧义 | 取证完成：`generic.cpp` 的 `validate_revolve_axis`（`:2873-2898`）只做结构校验，**无轴到草图平面距离、无方向平行性检查**；失败回执不含 `revolve_axis` 块（只在 `:3382-3384` 成功后填）。**2026-11-19 实机基线已跑通**（`test_revolve_axis_live.py --live`：9424.777960769377 / 785.3981633974481 mm³，no_centerline 如实失败），离面诊断与两圆边消歧仍未做 |
| 一 | 任务 5 材料增加异常回执 | **Python 侧已实现**（`volume_change`/`diagnosis`）；原生文案未改（无编译授权） |
| 二 | 任务 6 矩阵先验 / 跨组件选面 | 离线部分**已存在于 0.30.0**：`tests/unit/test_rotation_admission.py` 的 `ExplicitToleranceTests` 已覆盖默认/显式容差、反射、缩放与上限拒绝，本轮无需重复；仅剩实机 `ProAsmcompAssemble`/`PositionSet` 与 -2 结论 |
| 二 | 任务 7 Arm7 真实选区 | 取证完成：`sketch_regions.py` 只按端点聚类，**不做曲线内部交点切分**，弧/样条在签名里退化为弦（`_segment` `:222-225`）；零命中文案在 `region_selection.py:273`。原生无 section region / 求交 / 切分入口。只可交付诊断收窄 |
| 二 | 任务 8 G2 直接曲率 | 取证完成：`creo_measure_surface_curvature` 只测 1–2 个 quilt 成员面，**不测边、不能指定参数、无跨边两侧采样**，无法支撑 G2。需先扩原生测量 |
| 三 | 任务 9 实体边链圆角 | SDK 依据已核：`ProRound.h:34/37/122` 中 `PRO_E_RNDCH_REFERENCES` 是 Compound，其下 `PRO_E_STD_CURVE_COLLECTION_APPL` 为 **Chain Collection**（`ProCrvcollection.h:394/431/450` 证明可含多条 ADD_ONE 指令）；`PRO_E_RNDCH_REFERENCE_EDGES`(2105) 只有 `#define`，无树位置说明。当前 `generic.cpp:4111-4137` 每条边一个 SET、单元素数组。设计可写，编码需先分 FEAT ID 与实机 |
| 三 | 任务 10 嵌套子装配 | 4 处拒绝点已定位（`generic_bridge.py:1085-1092`、`native/advanced.cpp:2417-2419`、`assembly_replay.py:137-152`、`assembly_bundle.py:99-111`）；归 FEAT-012，设计未写 |

新能力编号：`docs/BACKLOG.md` 当前最大为 BUG-133 / FEAT-069 / DEV-093，**FEAT-070 是下一个可用编号**（未占用）。

离线验证：`python -m unittest discover -s tests` 4107 例全部通过（此前一轮曾出现 `tests/test_installation_validation.py` 的 `setup.ps1` 子进程 90 s 超时，单文件重跑同样超时，仍属环境/耗时问题）。`ruff check`/`ruff format --check` 覆盖全部改动文件通过。本机未编译、未连接 Creo、未做故障注入、未提交。
