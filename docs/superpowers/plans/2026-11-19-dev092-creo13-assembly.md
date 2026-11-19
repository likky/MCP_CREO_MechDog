# DEV-092：Creo 13.4 装配反馈处理计划

> **For agentic workers:** REQUIRED SUB-SKILL: 实施时使用 `subagent-driven-development` 或 `executing-plans`，逐任务核对下列验收。当前用户要求先分析和计划；本文件是待评审方案，不代表已实施或已获 Creo 实机授权。

**Goal:** 让外部矩阵输入在各层按同一约定和容差解释，并能用原生测量检查组件的真实位置；把 22 条配合的可解性作为独立验证任务。

**Architecture:** 沿用 stdio → server → bridge/generic_bridge → C TOOLKIT。Python 负责输入契约与保护；原生共享 helper 解释位姿，原生测量提供装配坐标中的几何证据。约束写入继续按组件整组替换，不在本轮未经查证增加 FIX 与配合混写。

**Tech Stack:** Windows x64、Python 3.12 / Pydantic / unittest、C++17、Creo C TOOLKIT；本机实机环境按现有项目规则为 Creo 12.4.0.0 / 匹配 SDK，反馈环境声称为 Creo 13.4.0.0。

**Spec:** [DEV-092](../../work-items/DEV-092.md)、[BUG-133](../../work-items/BUG-133.md)、[原始反馈与本次证据](../../validation/feedback-creo13-assembly-2026-11-19/EVIDENCE.md)。源报告针对 0.26.0，本计划按最新 0.27.0 主干 `f6da6334c38007e265bf75cfb3891a62a021963f` 制定。

## Global Constraints

- 长度毫米、角度度；原有 label 规则、单通道、busy 立即拒绝、revision、检查点/回滚、unknown 保护保持。
- 默认矩阵准入容差保持 `1e-6`。显式容差不表示 Creo 内核必然接受该精度；不自动正交化、修复或猜测矩阵约定。
- 原生执行器构建、启动/连接 Creo、建模与保存重载须用户当次明确确认；纯 SDK 无关 C++ 数学算例不建立 Toolkit 连接。
- 不结束/重启 Creo 或 nmsd、不清锁/unknown、不改用户模型；故障注入需单独授权。
- SDK 与常量表不复制进源码/发布包。历史 `docs/validation/` 原件保持字节不变；本次只新增归档。
- Creo 13 目录名和头文件声明不构成受支持版本或运行期成功声明；本机 12.4 结果不外推到反馈环境。
- 本轮只交付分析与计划；不改版本、不合入 main、不发布。以后合入 main 时按项目要求同步版本与完整 Release。

## Review Focus

1. Python 接受的显式容差在原生创建、重定位和回执重算中必须一致；以本次 28° 六位小数矩阵覆盖。
2. 非对称矩阵才能暴露转置错误；以已知点及非立方体覆盖列/行两种输入，不用单位阵或体积单独验收。
3. 同一源件重复插入及嵌套 occurrence 必须返回各自在根坐标中的几何；不能把源件局部 bbox 当实例 bbox。
4. 第二次约束写入替换整组，按两次累计追加来拆 22 条会丢失旧约束；用 mock 请求和获准的实际约束快照分别验证。
5. 未加载/抑制组件、求解整体失败或几何查询失败要返回明确 unavailable/原始码；不能伪造 bbox、逐条失败原因或自动补提交。

每项的测试归属分别为 T1、T2、T3、T4、T3/T5；它们是未来实施验收要求，本轮未执行这些新增测试。

## 1. 方案比较与建议

| 方案 | 收益与代价 | 判断 |
| --- | --- | --- |
| 仅提供 Rᵀ、显式容差和 fixed 放置说明 | 改动小，但显式容差目前被原生忽略；也不增加独立测量 | 可作为说明的一部分，无法完整解决软件缺陷 |
| 一次加入 keep_fixed/append、parallel/distance 和 22 条原样回放 | 覆盖报告全部建议，但混入未经证实的求解语义，缺原始引用/设计输入，无法定义可核对的成功条件 | 当前不采用 |
| **分批：先修容差 → 明确矩阵输入 → 原生几何检查 → 最小约束查证 → 原样回放** | 前三项可按现有架构开发，后两项以目标和实际求解证据决定 | **推荐方案；未声称用户已经选定实施** |

本次没有把报告的 P0 标签直接继承为项目优先级，也不采纳 30—45 分钟等未经独立验证的工期估算。

## 2. 报告逐项核对

| 报告判断/建议 | 当前 0.27.0 核对 | 处理结论 |
| --- | --- | --- |
| 列向量说明书应传 Rᵀ | 现有输入契约确为 `p_parent = p_local * M + T`，原样使用 M；这是约定差异，未发现原生擅自转置 | T2 可扩展显式 convention；不改变旧调用 |
| P03 六位小数残差超默认门槛，传 `1e-5` 可解决 | 缺 P03 原矩阵，不能复现该具体数值；合成 28° 用例已复现舍入超限。**Python 可准入，原生仍固定 `1e-6` 拒绝** | 新增 BUG-133，T1 优先修复；内核是否接受仍待测 |
| 报错没有实测残差 | **不成立**：当前及 `v0.26.0` Python 文本均含残差/det；原生也有数值，但 `std::to_string` 精度不足 | 不重复实现 Python 已有能力；T1 改善原生有效门槛与精度 |
| fixed 与 constraints 互斥、后补会覆盖 FIX | **成立**：创建分支互斥，后续调用整组 `ProAsmcompConstraintsSet` | T4 明示替换语义；不由此推导“约束驱动必然改变正确位姿” |
| 增加 keep_fixed/append 就能保位姿并保关系 | **未证实**：API 可读写数组，但不保证 FIX 与普通约束一起可解；物理设计目标也未冻结 | T5 最小实机查证，不能直接承诺写入模式 |
| 22 条超过单次 20 条，所以总装放不下 | **推论错误**：`ComponentConstraintsOp` 为单个组件一次修改，max 20；`AssembleOp.constraints` 没有此上限。不同组件本来就分别写入 | T4 文档说明；不能把同一组件的替换调用误当追加来拆批 |
| parallel/distance 当前硬拒 | **成立**：现有 named gap 保留；SDK 有枚举不等于写路径已验证 | T5 单独查证。align 还约束面的位置，不等价于仅平行；面偏移不等价于任意轴/点距离 |
| 同一零件对多条 mate 必然冗余/应去重为 10—12 条 | **只是推测**：未提供各条引用几何、方向、偏移、目标自由度；多平面约束也可能约束不同自由度 | 不能按类型和件名删除关系；先取得完整输入 |
| 约束失败能准确给第几条及冗余/冲突原因 | 预解析/引用/类型检查可定位索引；`ConstraintsSet` 求解失败只给整组通用错误 | T4 改善可确知阶段；整体失败索引为空并保留原始码。逐项试探另议，不自动执行 |
| inspect_session_assembly 缺逐组件世界 bbox | **成立**：当前有解算变换/约束，没有实例世界 bbox；受管装配 inspect 同样缺 | T3，测量语义与单位须先核对 |
| bbox 是唯一独立验收方式 | **过度表述**：已知点、轴向、原生质心及实际几何极值也可独立验收；bbox 也可能来自错误变换或保守近似 | 不能把变换局部 bbox 八角点所得外包络叫精确世界 bbox；不能只验体积 |
| inspect_model surfaces 无逐面面积 | **成立**：当前有 bbox/法向/原点/半径/轴，无逐面面积；已有原生面积 helper 可复用 | T3 面积字段与单位/查询失败状态一起设计 |
| feature_state 缺说明、旧边 ID 写入静默失败 | 当前材料只转述“前两份文档”，没有实际请求、旧 ID、回执或上游操作 | 先列为待核实，不根据本报告直接改状态或猜“被某特征消耗” |

源码定位：`schema.py:65–85, 99–155, 2082–2109`；`assembly_constraints.py:17–48`；`native/assembly_pose.h:38–116`；`advanced.cpp:2317, 2360, 2402–2405, 2547–2575`；`generic.cpp:728–753, 6577–6623, 8128`。行号指本次基线；实现时按符号重新定位。

PTC r13 [ConstraintsSet 说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/usascii/creo_toolkit/api/dita/159.html) 描述整数组设置、组件再生及整体失败返回；[装配指南](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/usascii/creo_toolkit/user_guide/Assembling_Components_by_Functions.html) 区分初始位姿与约束求解后的位姿。本次查证不证明任意 22 条约束可解。

## 3. Task T1：修复 BUG-133 容差跨层不一致

**Files:** 修改 `native/assembly_pose.h`；按实际调用补 `native/advanced.cpp` / `native/generic.cpp` 回执；回归 `tests/native/test_assembly_pose.cpp`、`tests/unit/test_rotation_admission.py`、`tests/unit/test_assembly_matrix_poses.py`；同步 BUG-133 与 FEAT-012/相关能力说明。

**Interfaces:** `assembly_rotation_admission(const Matrix&, double tolerance = assembly_admission_tolerance())`；`assembly_rigid_transform(const Json&, double[4][4])` 读取同一 op 的有效 `rotation_tolerance`，缺省/null 仍 `1e-6`。数值保持原样；直接原生入口也检查布尔、非有限、非正数等非法容差。回执的 accepted/admission/advice 使用同一有效门槛，不再回落到固定常量。

- [ ] **编码前冻结输入边界**：当前 Python 允许任意正有限容差；简单贯通会把超大容差放行反射/缩放的风险带入原生。先根据刚体变换契约确定允许上限或独立判定，并写入 BUG-133、两层 schema/helper 与兼容说明；未确定前不开始 T1 产品实现。本次计划不猜测一个没有依据的上限。
- [ ] 在现有原生测试加入本次矩阵 `[[.882948,.469472,0],[-.469472,.882948,0],[0,0,1]]`：默认拒绝；`1e-5` 接受且矩阵逐值相同；有效容差小于残差拒绝。先确认当前失败。
- [ ] 补显式容差非法值、反射/缩放和创建/更新一致性回归；反射等非法变换不能因异常大的容差静默绕过既有刚体要求，必要的容差范围规则先在本卡明确并同步两层。
- [ ] 统一有效容差与原生高精度错误文本；同步成功/失败回执，不改默认门槛或自动修复数据。
- [ ] 运行 `python -m unittest tests.unit.test_assembly_pose tests.unit.test_rotation_admission tests.unit.test_assembly_matrix_poses -v`、`python tools/test_assembly_pose.py`、`python tools/dev_check.py --work-item BUG-133`。Python/纯 C++ 一致才通过软件层验收。
- [ ] 当次获准后构建执行器，用不对称长方体做默认拒绝/显式容差放置、原生测量、revision、保存重载与失败回滚；如内核拒绝，保持原始 SDK 错误和未验收状态，不把放宽 Python/C++ 门槛写成几何成功。

## 4. Task T2：显式矩阵约定（FEAT-012 扩展）

**Files:** `src/creo_mechdog/schema.py` 的 `AssemblyPose`、`server.py` 两个装配位姿工具、`native/assembly_pose.h`、`native/advanced.cpp`/`generic.cpp` 回执、`src/creo_mechdog/capabilities.py`、`docs/REFERENCE_SYNTAX.md`；回归上述位姿测试及 `tests/unit/test_assembly_pipeline_requests.py`、`tests/native/test_assembly_pose.cpp`。

**Interfaces:** 提议 `rotation_convention: Literal["row", "column"] = "row"`，仅显式矩阵适用；column 表示 `p_parent(column) = R * p_local(column) + T`。两层均按**有效的规范行向量矩阵**计算准入残差：Python 只构建校验视图，保留请求输入与 convention 不变，原生唯一应用转换点将 column 转置一次；输出 `rotation_convention` 继续表示解算变换的既有完整行向量约定，另增 `input_rotation_convention` 说明请求，避免与返回变换混用。Euler 带显式 convention 时拒绝，不让无效字段悄悄生效。此为提议契约，实施前写入 FEAT-012。

- [ ] 非对称 90° Z 旋转：列矩阵 `[[0,-1,0],[1,0,0],[0,0,1]]`，点 `[2,3,5]`、平移 `[7,-8,9]`，结果必须 `[4,-6,14]`；转置后的 row 输入结果相同。旧缺省 row 输入与原来逐值一致。
- [ ] 补创建/重定位/execute_plan/独立工具一致性、重复验证不再次转置、Euler 冲突、未知约定和缺矩阵拒绝；保留原始输入用于追溯。
- [ ] 加阈值附近的舍入矩阵等价测试：column 为 `[[.965337,-.258191,.038222],[.258661,.965936,-.007826],[-.034899,.017442,.999239]]`，直接按其行计算残差约 `9.62666e-7`，转置后的规范 row 残差约 `1.023309e-6`。column 输入与等价 row 输入在两层都按后者判定，默认均拒绝、明确允许的 `1e-5` 均接受，避免仅检查原始数组导致前后门槛不一致。
- [ ] 修改共享契约、原生转换与能力/文档，运行 T1 专项、`test_assembly_pipeline_requests` 与纯 C++ harness；主干兼容行为不变。
- [ ] 获准的实机使用 10×20×30 mm 非立方体及已知点/轴对照，查询解算变换和原生 bbox/质心，保存重载后仍一致；单位阵或体积相同不足以通过。

## 5. Task T3：实例几何与逐面面积（FEAT-045 等现有检查能力扩展）

**Files:** 修改 `native/generic.cpp` 会话装配遍历和 `surface_cb`、`native/advanced.cpp` 受管装配 inspect，按需复用 `native/surface_measure.h`；检查 `src/creo_mechdog/session_assembly.py` / `src/creo_mechdog/assembly_replay.py` 的缓存与消费兼容，修改实际涉及的投影和 `src/creo_mechdog/compact_sections.py`；扩展 `tests/unit/test_session_assembly.py`，新建 `tools/test_assembly_geometry_inspection.py` 承载本任务的原生几何/保存重载验收。

**Interfaces:** 提议组件增加 `bbox_world_mm`（`[[xmin,ymin,zmin],[xmax,ymax,zmax]]` 或 null）、`bbox_status`、`bbox_query_code`，声明 frame=root_assembly / method / exclusions；surface 增加 `area_mm2` 或 null 与 `area_query_code`。响应预算保持，完整实例数据可由已有分页/详情路径取得；不把所有大字段强塞 compact。先确认当前实际模块名和字段投影路径再编辑。

- [ ] 离线核对 `ProAsmcomppathTrfGet(bottom_up=true)` 的 member→root 变换、`ProSolidOutlineCompute` 的方向矩阵与平移语义、`ProSurfaceAreaEval` 的面积单位及现有单位转换。SDK 原文留在本地；不把八角点变换外包络冒称精确极值。
- [ ] 为 root mm、源件非 mm、重复源件不同实例、嵌套、抑制/缺件与查询失败建立回执/分页测试；未测量必须 null+原因，不返回零盒。
- [ ] 接入原生几何查询，排除基准/曲线等非目标实体对 bbox 的污染；非实体/子装配的范围先明确，不能默认混为实体包围盒。逐面面积复用 `surface_area_native` 前检查单位是否已经换算。
- [ ] 获准实机：长方体 10×20×30 绕 Z 90°、平移 `[7,-8,9]`，原始体位于正坐标时，预期世界 bbox `[[-13,-8,9],[7,2,39]]`，体积 6000 mm³，质心 `[-3,-3,24]`；同时验旋转圆柱等非盒状件，排除“只旋转局部 bbox 八角点”的虚大包络。面面积按解析尺寸验证。
- [ ] 验重复/嵌套实例、单位转换、保存重载和只读前后状态；包围盒查询失败不改变模型/登记/revision。通过专项、统一检查后再声称新增字段可用。

## 6. Task T4：公开约束边界与可靠阶段错误

**Files:** `src/creo_mechdog/schema.py`、`src/creo_mechdog/assembly_constraints.py`、`src/creo_mechdog/capabilities.py`，`server.py` 工具说明，`native/advanced.cpp` 约束解析/设置、`native/generic.cpp` 失败投影，适用 compact/详情投影，`docs/REFERENCE_SYNTAX.md`；`tests/unit/test_assembly_constraint_semantics.py`、`tests/unit/test_assembly_pipeline_requests.py`。

**Interfaces:** 现有整组替换不变；可确知的预解析错误增加 `failed_constraint_index`（0-based）、`failed_constraint_type`、`stage`、API/原始 code。求解器整组失败索引为 null，`reason="solver_failed"`；不无依据返回 redundant/inconsistent 等类别。

- [ ] 固定组件改约束、同组件第二次整组替换、不同组件各自约束、新插入和后续修改的数量差异，分别用准入/请求测试冻结；明确 22 条跨组件不是整组上限。
- [ ] 文档列出支持类型、offset 与 sides 要求、insert 允许的引用及 `radius_mm` / `coaxial` 边界；parallel/distance 给受限替代的适用条件，不能写成无损同义映射。
- [ ] 加预解析第 N 条失败与整体求解失败的投影回归，确保 compact 仍保留可操作诊断；不自动逐项重提交、删除关系或改 fix 状态。
- [ ] 获准实机在临时独立装配验证约束快照确实整组替换、失败回滚/revision 不前进、保存重载；保持用户模型不动。

## 7. Task T5：固定/求解语义查证与原样总装回放

**Files:** 先补 DEV-090 / FEAT-068 和相关新功能卡；原生实现文件在最小试验得到依据后确定。不得先暴露 keep_fixed/append 或解除 parallel/distance 门禁。

**Interfaces:** 本阶段首先产出设计目标与查证结论。必须区分：固定位置快照、实际驱动位姿的配合、只读关系测量。只读检查关系不等于原生配合条目。

- [ ] 明确每个组件目标自由度、哪些关系应驱动位姿、哪些只需检查成立。查官方 Get/Set 约束和原生树，比较最小 FIX、FIX+非冲突约束、冲突、替换、必要时独立显式追加方案；每个变体的实机操作均限当次授权范围。
- [ ] parallel 与 axis/point distance 各立最小参考场景并核对元素/引用/偏移、方向与保存重载；没有正向证据保持 named gap。
- [ ] 收齐说明书 8.2/8.5、9 件 PRT/源件 revision、完整 R/T、22 条引用/方向/offset 与原始回执；不依据件名或“重合”文字猜引用。
- [ ] 在新建独立装配按组件逐步求解，先做最小非对称件方向探针；已接受任务只轮询，不自动重交。保留失败原码、约束快照、位姿前后、效果/回滚与保存重载。
- [ ] 全量验收同时检查原生实例几何、三轴质心、体积、约束读取与目标自由度。报告的 P05 `z=352.50…402.50` 和总质心 `(-.380,.032,324.470)` 仅在原始输入来源核实后作为该案例目标；机械功能判断另需依据。

## 8. 实施顺序与当前停止位置

T1 是根因与修复方向明确的缺陷；编码前还需冻结超大容差的保护边界，不需要等待液压缸原始模型。T2、T3、T4 是范围可控的能力/诊断扩展，但需要各自完成原生与实机验证。T3 的 API 测量语义要先查证，不能把字段输出本身当验收。T5 仍缺原始输入与求解依据，当前不能承诺“完整保留 22 条且位姿正确”。

建议先完成 **T1 + T2 + T4** 的软件层，再推进 T3 与获准的最小实机；完整液压缸数据不阻塞这些合成场景。共享的 `server.py`、`schema.py`、原生 helper 与失败投影由集成人顺序修改，避免并行冲突。

本轮已完成源码/SDK 查证、41 项现有离线单测和 BUG-133 纯 C++ 反例，结果见 EVIDENCE。产品实现、统一开发检查、原生执行器构建、Creo 实机及 WorkBuddy 黑盒均未执行；不将本轮规划写成问题已经修复。
