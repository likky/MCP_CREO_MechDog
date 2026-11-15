# 0.24.1 钣金基体法兰与装配配合反馈实施计划

> **For agentic workers:** 实施时使用 `subagent-driven-development`（推荐）或 `executing-plans` 按任务执行；本次只制定计划，以下未勾选步骤均未执行。跨模块公共契约先冻结，实机任务只能使用一个 Toolkit 通道。

**Goal:** 让文本给出的边/面、折弯首壁和配合关系能转成可测量、可编辑且保存后仍成立的 Creo 原生结果，并逐项说明尚不支持的部分。

**Architecture:** 沿用 stdio → `server.py` → `bridge.py` → `generic_bridge.py` → C TOOLKIT 原生执行器。先补几何引用与现有约束一致性，再分别交付钣金首壁、静态配合、细节特征；Python 只做输入适配和保护，实际几何匹配/测量由原生执行器完成。

**Tech Stack:** Windows x64、Python 3.12+ / Pydantic / unittest、C++17、Creo C TOOLKIT；当前本机资料依据为 Creo 12.4.0.0 SDK。

**Spec:** [DEV-089 目标、方案比较与边界](../../work-items/DEV-089.md)；[指定反馈原件](../../validation/feedback-0.24.1-2026-11-15/report.md)；[AGENTS](../../../AGENTS.md)。方案为本次推荐，尚未进入实现。

## 全局约束

- 输入长度使用毫米，角度使用度；特征标签以小写字母开头，仅包含小写字母、数字和下划线，最多 28 个字符。
- 新业务模块进 `src/creo_mechdog/`；根兼容导出与包内共享定义；`bridge.py` 是 Toolkit 通道锁唯一持有者，不新增旁路调度。
- Toolkit 通道忙立即拒绝，`isError=true`、`status="busy"`，带 `blocking_*`；不排队、不自动重交，已接受任务只轮询 `creo_get_job`。
- 保持 revision、检查点、失败回滚和 unknown 保护；成功不能只看返回码、参数回显、正体积或固定摆放。
- 用户明确确认后才可编译执行器、连接/启动 Creo 或原生测试；确认按次按范围生效。本次未获得这类确认。故障注入、结束进程、清保护仍需单独授权。
- 不擅自操作用户模型或改写历史原件；常量表由本机 SDK 生成，不提交、不跨机复制；SDK/官方整册资料不进仓库。
- 原生验收使用本机 Creo 12.4.0.0 / 匹配 SDK，记录环境、源码提交、dirty、源码指纹、命令与未测范围；不把结果外推到 Creo 9/10，不添加全项目双版本门槛。
- `version.py` 仅在未来交付时按规则更新。任何合入/直接提交 main 都须同次发布对应新版本 Release、附件与 SHA256；本次只交付本地规划。

## 审查重点

1. 同坐标多条边、同轴多实例或对称面：不能挑第一个候选，须有歧义拒绝和候选诊断（T1/T5）。
2. 宽度、厚度侧、折弯腿长、K/Y 因子：不能字段同名/数值相同就判定几何等价（T3/T4）。
3. 固定组件改约束后“返回成功但位置不符”：须原生测残差、保存重载和驱动变化后的随动（T2/T5）。
4. 圆弧端点误差和草图求解变形：分别测量，不能靠放宽阈值或跨环吸附掩盖（T0/T7）。
5. 从文件读取计划后文件变动、重复键、非法数据或原有请求混用：须冻结身份并复用原准入/事务（T8）。

## 1. 基线、证据和判断修正

2026-11-15 检出基线为 `main / 03b884d5795ed753adae9cae316b0a419d58d0fa`，`version.py=0.24.0`，本地标签仅见 `v0.24.0`；反馈自报 `0.24.1 / Creo 10.0.0.0 / release_numeric=42`。本次不推定两者为何不同，不将未核对的远端/运行服务称为当前版本。

反馈中的体积、23 个组件、61 个未建配合、12 条跳过项及 job/model ID 都是**外部报告事实**，未在本机重放。报告列出的 TXT v1.5、`txt_to_creo_plan.py`、`creo_plans/*.json`、端点残差和 native 日志未随本次指定材料提供；不能从文档摘要还原完整机械臂、区域签名或 61 条配合。离线检查可证明代码限制存在，不能证明报告对折弯扣除或求解漂移的全部因果解释。

| 反馈项 | 当前项目核对 | 计划 / 归属 |
| --- | --- | --- |
| A1 多折线基体法兰 | 真缺口。`sheetmetal.py::first_wall_section_problem` 单直线首壁是已知路线的保护；`flange_profile` 是附着于既有壁的候选，不是首壁 | T3，关联 FEAT-014、DEV-078；首壁新能力实施前单立 FEAT |
| A2 D2 符号改尺寸 | `DimensionValue.id` 必填，`expected_symbol` 只是保护；Creo 符号不保证等于 SolidWorks `D2` | T4，沿用 FEAT-004 尺寸保护，跨软件映射另记 |
| A3 距离+角度倒角 | 真缺口。round/chamfer 共用 RoundOp，原生目前等距倒角；统一用 `angle_deg` | T6a，新 FEAT |
| A4 方向线阵 | 真缺口。已有轴阵列和尺寸阵列，不等于指定方向/间距的原生线阵；FEAT-032 是沿曲线阵列 | T6b，新 FEAT，不重做旧阵列 |
| A5 曲率连续圆角 | 真缺口。实体 G2（曲率连续）不等于恒半径圆角、曲面 G1 测量或 FEAT-040 变半径 | T9a，关联 FEAT-040/055，新 FEAT |
| A6 区域选择切除 | 真缺口。ExtrudeOp 尚无区域选择；报告摘要缺真实签名数据 | T6c，新 FEAT；先冻结选区定义 |
| A7 配合枚举与锚点 | 锚点接口真缺；`align` 可覆盖部分同轴，mate/align_offset 已有偏移。平行/距离须按面、轴、点分别定义；gear 单独评估 | T1/T2/T5/T9b；BUG-036/041 优先，FEAT-049 六类回放保留 |
| A8 文件提交计划 | 真缺口；`creo_execute_plan` 当前只收 operations。DEV-080 H07 已登记相关需求 | T8，沿用 DEV-080，不另造第二套提交服务 |
| B1 按中点/端点选边 | 真缺口；`edge_geometry` 目前是 flange 专用，generic resolve 与 round/chamfer 尚不通用支持 | T1，共用引用新 FEAT |
| B2 圆心/两端点弧 | 当前 Arc 为圆心/半径/角度。过定输入必须先核半径残差，不能承诺任意三点都能维持原圆心圆弧 | T7，关联 BUG-101；显式适配，超差拒绝 |
| B3 JSON 六位舍入 | 报告的调用方精度损失，不直接归服务缺陷；保留 full double precision 文档/反例 | T0/T7；不宣称 1e-9 是所有版本固定内核容差 |
| B4 coordinates 阈值 | 默认 coordinates 1e-5 mm 严格拒绝、autodim 1e-3 mm 警告，显式阈值已有。阈值是验收界限，不改变求解精度 | T0/T7，沿用 FEAT-010，刚体漂移关联 BUG-108；不默认放宽 |
| B5 含弧/多环焊接 | 已有受控焊接；圆弧不可移动、separate_loops 拒绝是当前明确边界 | T7，沿用 BUG-101/BUG-049；不直接开放跨环焊接 |
| B6 offset 与 origin | 已支持 plane dict，origin 须落支撑面。两套坐标定义需转换；取消校验不能解决定义冲突 | T0/T3，关联 FEAT-010、BUG-095/097、FEAT-058 |
| B7 双向贯穿 | 已有 `direction="symmetric", depth_type="through_all"`，原生同时设 FROM_ALL/TO_ALL | T0，补示例/针对性验收，不新增 through_all_both 或自动猜方向 |
| B8 负折弯角 | 正角限制存在，但 native 写 SEC_FLIP，历史已测另一侧；“flip 只改材料侧”的判断需专门验证 | T3，先核角度/截面翻转/厚度侧，不只扩枚举 |
| B9 候选可预期性 | DEV-078 候选有离线实现且明确未获实机证明；不能因需求接近而解除门禁 | T3/T9，披露准入证据和未承诺范围 |

报告中的 P0 是报告方业务优先级；项目本批按 P1 优先处理准确引用和装配一致性，不把缺失功能统称为已复现 P0 缺陷。Arm6 源数据不足单列未验证，不通过补料追体积；体积吻合不能单独证明拓扑 EXACT 或机械功能。

## 2. 接入文件与职责

下列“新建”路径为计划中的实现位置，本次均未创建。开工前给新增功能登记 FEAT ID，确定与原负责人边界；公共文件由一个集成人串行合入。

| 范围 | 主要文件 | 职责 / 验收入口 |
| --- | --- | --- |
| 输入与引用 | `src/creo_mechdog/schema.py`、`references.py`；新建 `geometry_selectors.py`、`native/geometry_selectors.cpp` | Python 定义合法选择器，native 枚举/测量/唯一匹配；由 generic resolve 接入，并核实际 include 链 |
| 草图/坐标 | `native/generic.cpp`、`native/sketch_coordinates.cpp`、`src/creo_mechdog/endpoint_welding.py` | 平面与 frame 转换、精度/求解诊断、受控弧端点适配；现有保护不改义 |
| 钣金首壁 | `src/creo_mechdog/sheetmetal.py`、`schema.py`；新建 `native/sheetmetal_base_flange.cpp` | 独立首壁契约与原生创建；复用板厚/身份/保存核验，不套附着折边 |
| 尺寸 | `schema.py`、`dimension_guards.py`、`native/generic.cpp` | feature + Creo symbol 唯一解析；继续先核完整批次再写尺寸 |
| 装配 | `native/advanced.cpp`、`component_transform.h`、`schema.py`、`assembly_replay.py` | 实例路径、约束写入/求解与残差；回放按实际可写范围更新 |
| 细节/阵列/选区 | `native/generic.cpp`；按冻结树结构新建聚焦实现文件 | 角度倒角与方向线阵独立于旧 RoundOp/轴阵列；选区身份不得依靠不稳定编号 |
| 计划文件 | 新建 `src/creo_mechdog/plan_files.py`，`server.py`、`generic_bridge.py` | 文件只读加载、字节哈希、一次冻结、原准入链；不创建额外锁/队列 |
| 共同接线 | 包内 `capabilities.py`、`operation_results.py`、`job_projection.py`、`compact_sections.py`（按需） | 开关、结构化诊断、compact/full 保留必要标量；server 只做薄包装 |
| 回归与说明 | `tests/unit/`、`tools/test_*.py`、`docs/MODELING_0.21.md`、`README.md`、能力/兼容文档 | 具体输入、独立预期、保存重载、失败回滚与未测范围；不更改历史反馈 |

## 3. 分期任务

### T0：冻结复现输入和坐标/精度契约（P1，先离线）

**Files:** 本计划、DEV-089；后续专项测试 `tests/unit/test_feedback0241_contracts.py`，草图相关说明。消费报告，产出每个复现例的输入、坐标矩阵、预期和来源。

- [ ] 核对开始实施时 HEAD、源码版本、运行服务版本（服务仅在获准后查询），保留差异，不以数字字符串认定已安装最新。
- [ ] 获取/定位 TXT v1.5、12 件计划、61 条配合、区域签名、原始回执与 native 日志；按 SHA256 固定原件。没有材料时先使用独立合成算例，整机回放仍标缺材料，不扫描无关用户目录。
- [ ] 为 Arm2 分开定义：支撑面位置、草图局部 frame、原点所用坐标系、挤出宽度方向、厚度侧、内/外腿长、内半径与展开系数。原值留在来源记录，交付显式变换后的 Creo 输入；定义冲突则拒绝，不能丢 offset 或静默投影。
- [ ] 增加对照用例：相同圆弧计划全精度/六位舍入；坐标偏移与形状变形分别记录；最小跨越草图两侧的实体用 `symmetric + through_all` 预先算出切除体积。该贯穿例进入获准后的原生测试。
- [ ] 输出逐项 `已存在 / 真缺口 / 语义待核 / 源数据不足 / 未验证`，不根据报告摘要填写整机通过。

**完成条件：** 每个进入实现的样例有可复算预期；T3/T6c/T9b 所需缺失设计数据列明。示例文档本身用链接/输入静态检查；实际双向切除需 T10 的原生证据。

### T1：通用几何锚点解析（P1，最高复用价值）

**Files:** 上表引用模块、`tests/unit/test_geometry_selectors.py`；新建 `tools/test_geometry_selectors.py`。消费当前受管模型/实例及锚点；产出 native owner/type/id/path、候选数量和各项匹配残差。

- [ ] 先写契约反例：缺坐标系/实例路径、负/非有限容差、零匹配、多匹配均拒绝，旧显式 ID 引用仍接受；单个中点命中多边不得任选。
- [ ] 首批仅做直边端点（无向）、边上点辅助过滤，以及平面/圆柱/圆形边的点或中心、单位轴、半径联合匹配。每种选择器都显式记录坐标空间与 `tolerance_mm`；方向误差用度，与长度容差分离。轴向中心不唯一的圆柱只比较有几何意义的轴线距离/半径/范围，不盲比圆柱参数原点。
- [ ] 由原生测当前模型；在 round/chamfer/flange 和装配引用中复用同一匹配规则。初版不承诺任意曲线“中点”或最近面，不引入只凭距离的模糊选取。
- [ ] 装配先限定单层受管组件，根装配坐标必须经 occurrence 路径转换。重复源件的两个实例分别验收；结果绑定模型/revision，不把解析 ID 永久缓存到变更后的模型。
- [ ] 正例为已知尺寸长方体/带孔轴；反例为相同半径双孔、对称边、两个同源实例。保存重载后重新解析并检查实际几何，不要求 ID 数字永久不变。失败必须保留候选计数/原因，revision 和模型不变。

**验收：** `python -m unittest discover -s tests/unit -p test_geometry_selectors.py -v`；获准后运行新驱动并检查唯一匹配、拒绝分支及保存重载。选择器正式 JSON 字段在本任务首个契约提交冻结后，T3/T5/T6 才能依赖。

### T2：约束写入与实际位姿一致性（P1，BUG-036/041）

**Files:** `native/advanced.cpp`、`component_transform.h`、现有 `tools/test_assembly_pose.py`、`tests/unit/test_assembly_pose.py`；必要时新增 `tools/test_assembly_constraint_semantics.py`。消费旧六类约束和显式引用；产出每类适用的可测残差及写入结果。

- [ ] 用两件合成零件重现“已固定于非零平移/转角 → 三正交面零偏移约束”，先分别记录约束存储、求解状态、`ProAsmcomppathTrfGet` 位姿和面法向/距离；不预设根因就是缺 regenerate。
- [ ] 对普通 mate/align 传非零 offset、mate_offset/align_offset 的正负值分别核 SDK 和实际行为；定义普通类型是拒绝还是显式转换，不能静默忽略。旧调用兼容策略在 BUG-041 卡明确后再改。
- [ ] 可解约束须满足预设距离/角度残差；无法证明一致则返回明确失败/未验证，不能仅凭 `underconstrained=false` 宣称通过。冲突/无效引用保持原约束、位置、文件与 revision。
- [ ] 增加驱动平面偏移变化后的组件随动及保存重载，固定矩阵方案不能替代；同时保留单通道行为。

**完成条件：** 在当前目标环境复现/排除并取得一致性证据；外部 Creo 9 原案保持未复测，不因此阻断其它独立批次。T5 公开新约束必须通过本任务对应分支。

### T3：独立开放折线钣金基体法兰（P1，需先原生取证）

**Files:** `sheetmetal.py`、`schema.py`、新建 `native/sheetmetal_base_flange.cpp`、`tests/unit/test_sheetmetal_base_flange.py`、`tools/test_sheetmetal_base_flange.py`；关联 FEAT-014、DEV-078。

- [ ] 先写拒绝/兼容测试：旧 sheetmetal_wall 仍只接受一条直线；新候选仅接受连续、不分叉、不自交的开放 line 链、正宽度/板厚/内半径和明确厚度侧。首批两线直角，未测一般折线不公开。
- [ ] 用户当次确认后，由开发 AI 自行找/生成适用的原生首壁参照、提取完整树，与只改宽度、半径、翻转、系数的参照作单变量对照；按指南自行完成 owner/id/type 引用重绑与重建。没有可行参照/自动化路线时保留候选门禁和具体证据缺口，不让用户代建/代判。
- [ ] 在取证结果上冻结 `sheetmetal_base_flange` 契约：sketch、width、thickness、bend_radius、显式系数种类/值和方向字段；不得默认 `reverse` 就等于原有 `flip`。K/Y 采用经过核对的转换 `Y=K*pi/2`，`K=0.5` 对应 `Y≈0.7853981634`，原 y_factor 调用保持原义。
- [ ] 实现原生首壁和结果回读；不把 planar_wall + flange 的补长、实体 union 或去掉校验当等价修复。参照树/重建与目标几何需分别验证，不能只比较两份同源树一致。
- [ ] 独立预期至少包含：两腿外/内尺寸、半径、宽度、厚度有符号区间、bbox、截面面积×宽度的体积、真实钣金 body、展开长度及折回一致性。Arm2 `(-10,-2,-2)..(10,8,12)` 和 `792.323 mm3` 只是完整后续工序的外部目标，先核原始 TXT，不能拿最终体积验未经切孔/圆角的首壁。
- [ ] 分别测反向折弯、厚度侧与深度侧；B8 若现有 SEC_FLIP 已满足则补说明，确实不能表达才新增有文档和实测支持的方向字段。失败后核回滚，合法后续建模仍可用。

**完成条件：** 有完整依据、原生创建/完成/再生、独立几何与展开、尺寸编辑和保存重载证据才公开此 op；DEV-078 的 hem/joggle/角部候选不随之解禁。取证失败可交付明确边界，但不能将本能力记为完成。

### T4：按特征和符号唯一定位尺寸（P1）

**Files:** `schema.py`、`dimension_guards.py`、`native/generic.cpp`、`tests/unit/test_dimension_guards.py`，扩展 `tools/test_adoption_dimension_guards.py`；关联 FEAT-004。

- [ ] 新增目标二选一契约：旧 `{id,value,...guards}` 或 `{feature,symbol,value,...guards}`，feature 为明确 label/ID；两者混用、无匹配、多匹配、参考/关系驱动尺寸拒绝。不得仅按 feature_type 在全模型搜第一个 D2。
- [ ] 原生先在目标特征内定位 Creo symbol，并在整批全部解析/守卫通过后才写；回执保留解析 ID、owner、旧/新值与符号，compact 保留关键结果。
- [ ] 对外部 `D2@SMBaseFlange`，由建模时生成的角色映射明确到“宽度”对应 Creo 尺寸；不能用原样 D2 猜测。T3 的宽度编辑还须检查 feature 身份、板厚、腿长及 bbox。
- [ ] 写旧 ID 兼容、重复符号拒绝、批内第二项 guard 失败时第一项未写、保存重载后宽度变化及后续合法编辑用例。

**验收：** 专项 unittest 与获准后的尺寸驱动测量；只返回解析 ID 不代表 CAD 改型成功。

### T5：静态配合语义和锚点装配（P1，依赖 T1/T2）

**Files:** `schema.py`、`native/advanced.cpp`、`assembly_replay.py`、`tests/unit/test_assembly_constraint_semantics.py`、`tools/test_assembly_constraint_semantics.py`。

- [ ] 冻结配合转换表：coincident 按面法向和 side 映射 mate/align；concentric 先覆盖轴/圆柱的同轴，明确轴向移动和旋转自由度；distance 按面/轴/点种类定义；parallel 不可用零距重合来冒充。无可靠映射则拒绝并保留原参数。
- [ ] 仅对本机 SDK 有声明且通过原生验证的类型增加写侧映射/能力登记。ORIENT/LINE_PARL/LINE_DIST/PNT_DIST 等是查证候选，不因枚举存在直接开放；OffsetSet 的适用条件逐类核对。
- [ ] 每条约束报告 source mate id、两侧模型/实例引用、解析几何、有效类型、side/offset 和实测残差。先插入全部组件，再按组件合并完整约束集；当前 component_constraints 是替换语义，不能逐条调用覆盖先前配合。批次先解析全部，检查每组件条数上限/引用依赖/冲突，冲突整批回滚；不自动降级为 fixed、不删实例、不靠省略配合凑成功。
- [ ] 测同源双实例、反向轴、间距正负值、共面/平行区别、同组件多条配合全部保留、欠约束/冗余/矛盾组合，核实际相对位置、预期自由度、驱动变化随动及保存重载。旧六类回放在 FEAT-049 范围回归，新类型只有新快照/回放契约通过后才宣布可回放。
- [ ] 整机回放按逐条配合映射记录建成/拒绝/缺数据。61 条中 60 条非 gear 也只是候选范围，不承诺全部可建或全部相容；61/61 只能在 gear 和完整输入均通过后报告。

**完成条件：** 支持矩阵与每类独立测试相符，约束存在和求解后实际关系都成立；固定变换一致只保留为初始摆放证据。

### T6：常用细节特征（三个独立交付，P1/P2）

每项分别登记新 FEAT、先核 SDK 文档/树，再写单元反例与获准后的原生驱动；不能把三项全验完成作为单项交付的条件。

- [ ] **T6a 角度倒角：** `schema.py` 将 ChamferOp 从 RoundOp 共用模型分离，旧 size/reference 输入兼容；新增 distance_angle 模式和 `angle_deg`，明确距离所量的面及 reference side。新增 `tests/unit/test_chamfer_angle.py`、`tools/test_chamfer_angle.py`；90°长方体棱验证实际两面退距比/斜面角及去除体积，包含约 70°和反向参考，不只回读角度值。
- [ ] **T6b 方向线阵：** 新建聚焦的 `native/linear_pattern.cpp` 与 `tests/unit/test_linear_pattern.py`、`tools/test_linear_pattern.py`；契约 direction 为模型坐标单位向量、spacing 为正 mm、count 包括首例且至少 2、flip 只反方向。先单方向原生特征阵列，明确组/多特征首版边界；Hom 目标 `X / 42 / 2 / flip=true` 的第二例相对首例须为 `[-42,0,0] mm`。测真实 pattern leader/成员、中心间距与后续尺寸随动，不用复制实体代替。
- [ ] **T6c 区域切除：** 取得真实 B-REGION 后定义稳定签名（参与实体、环方向/包含关系、采样点）及去歧义规则；原生解析截面区域，再交给拉伸。新增 `tests/unit/test_extrude_regions.py`、`tools/test_extrude_regions.py`；独立三矩形只切指定两区，分别测各区材料和总切除量；相交、重合、过期签名拒绝且 revision 不变。不能以临时重建删掉未选轮廓冒充原草图区域选择，无法稳定引用则保持不支持。

### T7：圆弧、焊接与草图容差（P1 诊断，P2 扩展）

**Files:** `endpoint_welding.py`、`schema.py`、`profile_checks.py`、`native/sketch_coordinates.cpp`、`tests/unit/test_endpoint_welding.py`、`tests/unit/test_sketch_geometry_deviation.py`；沿用 BUG-101、FEAT-010。

- [ ] 先改善失败回执：实测 shape deviation、刚体位移、所用模式、有效阈值/来源、失败阶段和无法测量原因；full/compact 均保留必要标量。不自动重试、不自动建议“放宽到这个值就正确”。
- [ ] 保持 coordinates 默认 `1e-5 mm`；若增加计划级默认容差，优先级固定“单 sketch 显式值 > 计划显式默认 > 模式默认”，只影响未显式设置的新草图，冻结到作业输入并报告来源。先做 bool/NaN/Inf/0/负值拒绝和旧请求相同结果测试。
- [ ] `arc_by_endpoints` 作为显式新输入候选，先检查两端到圆心半径是否一致、方向/整圆/退化与共享端点约束。只能在调用者声明的最大移动和形状误差预算内规整，报告 before/after 与 max_endpoint_move；不能默改中心/半径或把残差写成 0。
- [ ] 焊接仅在明确同一拓扑链内处理圆弧关联；独立相邻环默认仍不跨环合并。测试同环 line-arc/arc-arc、半径不一致、相切双环和会产生自交的吸附，创建与编辑均覆盖；超过预算拒绝。
- [ ] 获准后比较实际 SectionRegenerate/CompleteFeature 两阶段原生几何、闭合与形状误差、成形/保存重载；报告 0.005 mm 聚类或 0.0025 mm 阈值不是本项目默认值，不能直接照搬。

### T8：从受控本地 JSON 提交计划（P2，可与几何研究并行）

**Files:** 新建 `plan_files.py`、`tests/unit/test_plan_files.py`，修改 `server.py`、`generic_bridge.py`；沿用 DEV-080 H07。

- [ ] 首版建议给现有 execute_plan 增加可选 plan_file，与 operations 互斥；服务接受的 JSON 文件为现有 operations 数组，其它 model/revision/assertions/timeout 参数继续由工具显式传入，文件不含第二套顶层元数据。这是建议契约，不是对未取得的外部计划文件形态的判断：T0 取得原件后须记录是否需要显式抽取 operations，不能承诺 `creo_plans/*.json` 直接兼容；若要支持完整请求对象，先更新本任务契约与冲突优先级测试再实施。
- [ ] 首版仅允许明确绝对本地普通文件，拒绝 UNC/设备路径，设 `MAX_PLAN_FILE_BYTES=16*1024*1024`；以 UTF-8/可选 BOM 解码，拒绝重复 JSON 键、非有限数字、非法 schema。文件内容读取一次形成不可变 bytes/parsed 快照，记录实际 bytes、SHA256 与 resolved path，不在排队/执行时再次读可变文件。
- [ ] 后续走完全相同的能力门禁、revision、busy、超时、事务与断言；文件路径不是直接发给 native 的执行脚本。不自动递归加载 include/外部文件，不执行文本中的命令。
- [ ] 先写：边界字节数、相对/UNC/设备路径、编码/重复键、双来源冲突、读取后文件改变、过期 revision、busy 拒绝、合法 inline/file 规范化结果一致的单元回归；必要集成由新驱动在当次获准后验证。

### T9：独立预研，不能阻塞前面单项交付（P2）

- [ ] **T9a 实体 G2 圆角：** 核对实体圆角曲率连续的实际树、半径/形状控制及相邻面条件；用官方依据和成功参照做单变量重建。验收沿接缝测位置、切向与曲率连续，而非只看设置值或 G1 角度。无证据保持不可用，不借用 surface_round 或变半径的通过结论。
- [ ] **T9b gear：** 单立可行性卡，查 C TOOLKIT 可用机制/运动 API、许可、关节/运动轴、传动比符号和保存关系；现有组件 placement 约束枚举不足以证明支持。验收须改变输入转角并测输出转角比例及方向、保存重载后关系仍可驱动；仅静态两齿轮摆放和 ratio 参数存储不算通过。不可行则发布明确边界，不将整个装配计划标全部完成。
- [ ] **T9c DEV-078 候选：** 逐候选列“已有离线实现 / 尚缺参照或实机 / 不承诺版本”，仅在本候选板厚、钣金身份、展开、保存重载及回滚都通过时解禁；首壁通过不替代附着 hem/jog 验收。

### T10：集成、分层验收与交付

- [ ] 每项先运行该项有意义的单元回归（unittest，新增放 tests/unit），再在冻结源码执行 `./.venv/Scripts/python.exe tools/dev_check.py --work-item <实际ID>`；不得重建风格基线来掩盖失败。
- [ ] 用户当次明确确认的测试范围内，由一个执行者串行 `./.venv/Scripts/python.exe bridge.py build` 及对应原生驱动。工具脚本先检查默认行为/参数，默认只离线，`--live` 明确进入实机；不机械沿用旧“确认会话可操作”前置。所有步骤由 AI 完成与判定。
- [ ] 原生正例须 `status=succeeded`、特征最终有效、独立几何/关系断言通过、`saved_file_reloaded_and_verified=true`；反例核原始错误、回滚、文件/模型/revision 与后续合法编辑。需测试 busy 时实际并发才记为并发证据，不做未获准故障注入。
- [ ] 完整材料取得后回放 12 唯一零件/23 实例，逐一对照原始工序、尺寸、bbox、体积、跳过特征与配合；Arm6 缺数据、未建 gear、容差接受等逐项保留。阶段目标是消除已覆盖缺口，不以“全部有实体”升级为 EXACT/VERIFIED。
- [ ] 后续 WorkBuddy 单独走 MCP 黑盒：确认公开环境/服务版本、记录输入与 job/model、几何/配合、保存重载、revision/失败结果；不读源码/配置、不跑本地测试，开发者与黑盒证据不互代。
- [ ] 更新对应工作卡、唯一 BACKLOG、能力/工具描述和未测范围；按独立能力提交。实施分支日常提交不发版；若用户授权合 main，再选未发布目标版本并执行 RELEASING 全流程，标签指向该主干提交，附件由该提交生成，远端 Release/附件/SHA256 核对完成才算交付。

## 4. 顺序、并行与阶段产出

推荐顺序为 `T0 → T1 → T3/T4 → T5 → T6 → T7/T8 → T9`；其中 **T2 应尽早与 T1 离线并行**，T5 必须等待 T1/T2，而 T3 不依赖装配修复。T7 的诊断可前移到 T0 之后，T8 可与钣金/装配取证并行。

| 批次 | 内容 | 可独立交付的结果 |
| --- | --- | --- |
| A | T0 + T1 + T2 的对应闭环 | 精确引用与旧约束可靠性；已有双向贯穿示例和精度诊断 |
| B | T3 + T4 | 有真实钣金/尺寸/展开与重载证据的两线首壁；不承诺整个 Arm2 已精确 |
| C | T5 | 明确支持矩阵的静态配合；逐条解释未建配合，gear 独立 |
| D | T6a / T6b / T6c 分别交付，T7/T8 可穿插 | 角度倒角、方向线阵、区域切除、显式输入适配/文件提交 |
| E | T9 + 完整输入下 T10 | 经证实才开放的 G2/gear/候选及整机差异报告 |

可并行的是离线源码、SDK 核验和不同文件的实现；`schema.py`、`server.py`、`native/generic.cpp`、能力/回执投影由一个集成人协调。编译/原生会话/实机测试串行，不为提速另开 Toolkit 通道。每批仅承诺完成条件和证据，不预先绑定版本号或工期；参照树、SDK 能力或原始输入未齐时更新具体缺口，不用未经验证的实现填补。

## 5. 主要依据与本次未验证范围

- **当前源码：** `schema.py`（ExtrudeOp/RoundOp/DimensionValue/AssemblyConstraint）、`sheetmetal.py`、`endpoint_welding.py`、`references.py`；`native/generic.cpp`（resolve、origin 平面校验、双向贯穿、generic_round）、`native/advanced.cpp`（edge_geometry、SEC_FLIP/Y factor、约束映射）、`native/sketch_coordinates.cpp`（模式/容差）；具体入口在任务表中。
- **本机 SDK：** `C:/Program Files/PTC/Creo 12.4.0.0/Common Files/protoolkit/includes/ProAsmcomp.h`（约束允许引用类型、OffsetSet）、`ProDimension.h`（符号/归属查询）、`ProSmtFlangeWall.h`（附着折边与展开 Y factor）、`ProSheetmetal.h`；官方示例 `protk_appls/pt_userguide/ptu_asm/UgAsmcompConstraint.c`。声明/示例只证明查证入口，不证明新操作已可运行。
- **PTC 官方在线，2026-11-15 查阅：** [原生装配约束语义与实例路径](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/usascii/creo_toolkit/user_guide/Assembling_a_Component_Parametrically.html)、[非附着与附着壁的区别](https://support.ptc.com/help/creo/creo_pma/r12/usascii/sheetmetal/sheetmetaldesign/About_Creating_Walls.html)、[非附着拉伸壁的参数](https://support.ptc.com/help/creo/creo_pma/r12/usascii/sheetmetal/sheetmetaldesign/To_Create_an_Unattached_Extruded_Wall.html)、[Y/K 因子](https://support.ptc.com/help/creo/creo_pma/r12/usascii/electrical_design/ecad/About_Y_factor_and_K_factor.html)、[gear pair 运动关系](https://support.ptc.com/help/creo/creo_pma/r12/usascii/simulate/mech_des/About_Generic_Gear_Pairs.html)。产品界面说明不是 C TOOLKIT 创建 API 已支持的证据；本机 SDK 与实机仍需分别核验。

本次只做离线资料/源码核对、计划及文档完整性检查。无本次编译、Creo/MCP/Toolkit、原生取树/几何/展开/重载/回滚、产品单元/全量检查、Creo 9/10 或 WorkBuddy 证据；也未拉取远端、提交、推送或发布。未勾选任务不代表已实现或已获准执行。
