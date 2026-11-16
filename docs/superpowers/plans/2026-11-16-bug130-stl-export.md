# BUG-130 STL 导出崩溃修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使 `bulb_bulged` 的 STL 导出在明确质量设置下成功并保持源模型不变；异常输入/输出必须可诊断失败，不能再因应用侧未经校验的网格解引用崩溃。

**Architecture:** 优先试验 SDK 官方文件导出 `ProIntfSliceFileWithOptionsMdlnameExport`，由 Creo 直接生成 ASCII STL，绕开 worker 手工访问 `ProSurfaceTessellationData` 嵌套指针的路径。保留诊断探针定位旧故障，不把换路径成功等同于旧访问冲突已查明；官方路径不能通过同质量回归时，再验证逐实体面剖分、受检访问与逐面释放的备选方案。

**Tech Stack:** Windows x64、C++17/C TOOLKIT、本机 Creo 12.4 SDK、Python 3.12/unittest；沿用当前 MCP/bridge 的串行通道和只读导出契约。

**Spec:** [BUG-130](../../work-items/BUG-130.md)「离线复核」及 [球鼻艏重建记录](../../development/FRIGATE-BULB-BULGED-2026-11-16.md)。本文件是修复提案，未实施、未构建或连接 Creo；不是实机通过记录。

## Global Constraints

- 本轮仅离线查证与计划。后续原生构建/连接/导出测试须满足 AGENTS 的用户当次确认；不得擅自结束/重启 Creo/nmsd、清锁、清 unknown 保护或覆盖用户模型。
- 现有失败作业不重放、不改写；模型 `cda665ef57d54847bb6970e5787e7fbd` rev8 / `.prt.9` 仅作只读基线，首先在隔离的新测试副本验证。
- busy 立即拒绝；接受后只轮询 `creo_get_job`。只读导出不得推进 revision、保存源件或自动放宽恢复保护。
- 保持 `format="stl"` 现有调用可用，不新增公开工具、不改变 STEP/IGES/JPEG 等格式行为。不顺带修复曲面拟合、JPEG 视图、plan_file 提示或装配导出范围。
- 默认仍请求弦高 0.05 mm、角控制 0.1；显式质量设置与实际传入 SDK 的值可追溯，不能悄悄降低质量以得到成功。
- 提交开发使用 `codex/bug-130-stl-export`。当前主干上的未提交资料和其它任务文件全部保留；本计划不安排直接提交 main。以后如合 main，另遵守版本与 Release 规则。

## 已核实的事实与未证假设

| 证据 | 可支持的结论 |
| --- | --- |
| 两次失败 `0f2a588d…` / `14e5f18e…`，worker `0xC0000005` | STL 路径有可重复的原生访问冲突；不等于已证明 Creo 主进程退出 |
| 最后两条 API 日志都返回0 | 已走过整件剖分与外层 ProArray 计数；没有打印实际 n、每面计数或故障栈，尚不能精确定位崩溃语句 |
| 两次输出 STL 均0字节 | 已建立输出文件，但没有正常完成文件交付；结合代码，不能优先认定发生在 `out.close()` 之后的 Toolkit 释放阶段 |
| 同件 STEP 成功；小件 STL 成功 | 特定 STEP 路径和特定小模型路径可用；不证明大件的剖分数据、索引或曲面没有问题 |
| 旧球鼻艏 STL 作业 `37a35d…` 成功，197118片 / 48847489字节 | 约14m尺度本身不是 STL 必败条件；旧作业是另一会话，仍需同会话受控对照 |
| 本机 `ProPart.h:105–155` | 第四参是 `include_quilts`，不是相对/绝对弦高开关；角控制范围0～1，不是角度制数值 |
| `native/generic.cpp:4211–4242` | 有未校验面指针、顶点/面片计数及索引、异常路径资源泄漏、缺写盘失败检查等风险；这些是已见代码缺口，尚非已证此次 AV 根因 |

球鼻艏实际包络约14.001×3.636×2.000m，X在64.095～78.095m。对角线约14602.7mm；此前建议 `max(0.01,diag*1e-6)` 会得到约0.0146mm，比现有0.05mm更细，不能直接当作减负修法。新件的曲面复杂度、修剪/收敛拓扑、数组返回、SDK/IPC及内存峰值都需要区分。

## 方案取舍

1. **推荐先验证：官方 STL 文件导出。** `ProIntfSliceFileWithOptionsMdlnameExport` + `PRO_SLA_ASCII_FILE`；客户端只持有3个质量参数和文件，不自行解引用整件剖分结果。风险：路径/文件名限制、质量允许范围、旧调用语义和实际输出必须实测；内部剖分仍可能耗费大量内存。
2. **备选：逐实体面剖分。** `ProSolidBodiesCollect` / `ProSolidBodySurfaceVisit` → `ProSurfaceTessellationGet` → `ProTessellationVerticesGet` / `FacetsGet`。好处是单面日志与累计预算清晰；代价是内存所有权更多、独立剖分接缝可能不一致，而且无法保证单个复杂面不会耗尽内存。
3. **不作为单独修复：仅增大弦高、仅改为文件流、或 catch AV 继续执行。** 当前代码本来就在顺序写 `ofstream`，内存峰值来自 SDK 整件剖分而非另建的应用网格列表。放宽质量只能作为显式对照；普通 RAII/catch 不能把访问冲突变成可信的已恢复状态。

## Review Focus

- API成功但返回空数组、空指针或越界顶点索引：必须在解引用前拒绝，并保留面/片索引。
- SDK报成功但文件为空、截断、含NaN/Inf或漏面：不得发布为成功STL。
- 新旧同尺度球鼻艏与缩比复杂曲面的交叉对照：避免把形状复杂度/会话差异混同为尺度。
- 质量参数在单位换算、接口包装、计划输入及compact/full回执中丢失或悄悄被强制调整。
- 单面路径的跨面裂缝、双重释放及只读失败后自动清保护：必须分别有测试/实机证据。

## Task 1：冻结证据并建立可区分故障阶段的探针

**Files:** Create `tools/diagnose_stl_export.py`；Modify `native/generic.cpp` 的 STL 诊断路径（后续提取到 `native/stl_export.h`）；Test `tests/unit/test_stl_export_evidence.py`。

**Interfaces:** `summarize_stl_job(job_dir: Path) -> dict` 只读已有作业；诊断输出包含 job/model/revision、原始终态、退出码、日志最后阶段、输出字节、源件SHA256及可获得的源码/worker身份。不连接 Creo。

- [ ] 为已存两份失败日志、0字节文件及旧成功 STL 写回归，断言仅日志尾部相同，整份日志因时间不同并非逐字相同；不从成功API码虚构面数。
- [ ] 在旧路径所有潜在解引用/IO阶段前后增加立即flush的诊断：`tess_begin/end`、`outer_array_count`、`output_open`、`surface_begin/end`、`facet_batch`、`file_flush_close`、`tess_free_begin/end`。每面至少记录 surface id、n_vertices、n_facets、指针是否为空；面片每4096片记录进度，异常立即记录三索引，避免每片刷日志。
- [ ] 记录 worker 与 Creo 主进程的PID/创建时间、两者的内存观测和作业前后存活证据；不能仅以worker退出码说Creo崩溃。
- [ ] 若仍AV，下一次有授权的受控验证取得故障指令/读写地址/调用栈和必要的worker dump；保留原始 `unknown_outcome`，不把SEH拦截后的状态报告为已安全恢复。
- [ ] 运行证据专项 unittest。探针本身的实机重现留待Task5授权范围，不先在用户源件重复触发旧崩溃。

## Task 2：建立与 SDK 无关的 STL 文件验收

**Files:** Create `native/stl_file_check.h`、`tests/native/test_stl_file_check.cpp`、`tools/test_stl_file_check.py`；Test `tests/unit/test_stl_export.py`。

**Interfaces:** `StlFileStats validate_ascii_stl(const std::filesystem::path&, const StlOutputLimits&)`。`StlFileStats` 含 `uint64_t facet_count`、`uint64_t bytes`、`std::array<double,3> min/max`；`StlOutputLimits` 含 `uint64_t max_facets/max_bytes`。异常包含可区分的空/截断/非有限坐标/超预算/IO失败原因。无Toolkit、无Creo连接。

- [ ] 使用正确四面体 fixture（4片，包络[0,0,0]～[1,1,1]、有符号体积1/6）验证三角片读取、有限值和边界；坏输入覆盖缺vertex/缺endfacet、NaN/Inf、0片、只写header、截断文件。
- [ ] 使用小预算注入测试证明文件大小/片数门限会正常失败，不在测试里真的分配大网格。建议初始交付预算为512MiB文件/200万片，作为设计取值记录；超过后报告资源限制，不静默重采样。若本故障件合法输出超过预算，先根据Task5实测重新审定，不能仅将“受控拒绝”记为完整导出修复。
- [ ] 校验采用逐行/逐三角形扫描，不把整个ASCII STL装入内存；检查文件读取错误及完整结束。
- [ ] 接缝/闭合/绕序与体积比较由Task5独立检查，不能只因语法可解析就标几何通过。
- [ ] 用MSVC独立编译运行此C++测试；驱动复用 `tools/test_inspection_units.py` 的compiler环境方式。它不加载Toolkit，不替代原生导出验收。

## Task 3：官方文件导出路径及原子交付

**Files:** Create `native/stl_export.h`；Modify `native/generic.cpp:4211` 和 export 分派；Test `tests/unit/test_stl_export.py`，在native测试增加可注入API适配器验证参数/清理。

**Interfaces:** `static J write_stl(ProMdl model, const std::wstring& destination, const StlExportOptions& options)`；`StlExportOptions` 初始字段 `chord_height_mm=0.05`、`angle_control=0.1`。结果为 `stl_export` 有界对象：method、requested参数、passed参数/原生长度单位、API码、facet_count、bytes、bounds、file_validation。

- [ ] 使用 `ProArrayAlloc` 创建**3个double的ProArray**，内容为原生长度单位的弦高、角控制、0；不能把普通C数组当成SDK所需ProArray。用匹配的 `ProArrayFree` 恰好释放一次。
- [ ] 调用 `ProIntfSliceFileWithOptionsMdlnameExport`，类型 `PRO_SLA_ASCII_FILE`，flags仅 `PRO_FACET_STEP_SIZE_OFF`，transf/comp_path为NULL。不要设置USE_CONFIG、FORCE_INTO_RANGE、DEFAULT或ADJUST来悄悄改变质量。单位沿用现有已知比例；本故障模型为mm，未知单位不猜值。
- [ ] 使用本作业专有暂存位置/短ASCII文件名，完成后由Task2校验并在同文件系统原子发布到最终 `.stl`；不覆盖其它作业/用户已有文件。核查SDK的31字符文件名限制、绝对路径与中文目录；如需改变Creo工作目录，必须在通道锁内保存/恢复，并在异常路径有明确证据，不更改用户配置文件。
- [ ] 任何SDK/IO/校验失败不报告成功文件，不自动重试另一容差或旧剖分路径；保留可定位的本作业暂存文件与阶段。SDK成功但验收失败要报告独立文件验收失败，不能伪装为PTC原始错误码。
- [ ] 参数分配成功后任何C++异常均能清理；SDK控制权内的崩溃不承诺RAII能恢复。出口既不保存源件也不推进revision。
- [ ] 先跑无Creo的参数、单位、flags、API错误与文件失败测试。官方路径如在Task5中通过同质量的全部本BUG模型，作为正式路径；否则执行Task4，不宣称根因已明。

## Task 4：仅在 Task3 不满足验收时验证逐面备选

**Files:** Modify `native/stl_export.h`；Create `native/stl_mesh_check.h`、`tests/native/test_stl_mesh_check.cpp`；扩展Task2的离线native驱动。

**Interfaces:** `MeshCheck validate_mesh_view(const Point3* vertices, int vertex_count, const Triangle3* facets, int facet_count, int surface_id)`；`Point3=std::array<double,3>`、`Triangle3=std::array<int,3>`，`MeshCheck` 含 `bool valid`、`std::string reason`、`int surface_id/facet_index` 和三索引。只借用数据，不拥有或释放SDK数组；有符号计数验证后才转换为size_t。面级资源分别归对应SDK guard管理。

- [ ] 写会失败的内存边界测试：负计数、非空计数配NULL、索引−1/等于vertex_count、NaN/Inf、三索引重复、预算累计溢出。非法索引必须在坐标解引用前识别，不用崩溃注入来测试普通边界。
- [ ] 仅遍历活动材料实体的实际面，沿用 `ProSolidBodiesCollect` / `ProSolidBodySurfaceVisit`，不能把历史quilt或空模板体当作导出实体。
- [ ] 单面分配input、设置已核对质量、获取tessellation；通过VerticesGet/FacetsGet取得各自拥有的ProArray，检查每个API返回码和数组大小。单面写完即释放两个数组、tessellation和input；错误路径每个资源恰好释放一次。不能对旧 `ProSurfaceTessellationData` 的嵌套借用字段逐个ProArrayFree。
- [ ] 片数用uint64累计并作乘法溢出检测；异常时拒绝整个导出，不通过跳过越界/缺失三角片制造成功文件。零面积面片的策略须显式统计并在闭合验收中检查。
- [ ] 文件流写入失败/flush/close失败均传播；调用前后诊断可区分哪一个面/阶段出错。每面预算仅约束已取得的数据，不能声称阻止SDK内部单面OOM。
- [ ] 同一闭合体的相邻面剖分必须额外验证无裂缝、漏面和翻面；若独立剖分不能保证共享边一致，不默认“焊点修复”后声称原精度不变。此分支未通过则保持BUG未修复并准备PTC最小复现资料。

## Task 5：受控实机矩阵与只读契约验收

**Files:** Create `tools/test_stl_export.py`（默认离线，仅显式live参数才连Creo）；Modify `docs/work-items/BUG-130.md`、能力/参考说明的STL边界。

- [ ] 获得当次明确授权后，记录HEAD/dirty、源码指纹、worker hash、Creo版本及两个进程身份。测试使用独立副本，不清既有保护、不重放旧失败任务。
- [ ] 先验证小件6270mm³，再验证旧14m球鼻艏，最后验证本故障 `bulb_bulged`；每模型使用相同mm单位、0.05mm/0.1质量、单次提交。任何新的AV立即停止该路线，保留证据，不继续无新假设重试。
- [ ] 将新旧14m模型放到同一受控会话比较；必要时对相同复杂曲面作1:100缩比并同比例缩放弦高，再单独改变弦高为0.2/1.0mm，区分尺度、相对精度和面复杂度。对照结果是检验假设，不是保证面片数量随参数单调。
- [ ] 默认质量原调用成功、STL非空且完整、坐标量级/包络与对应实体一致；独立检查闭合、法向、面片体积与原生体积及抽样到原生面的偏差。本提案对0.05mm弦高的初始网格验收目标是抽样偏差≤0.1mm、相对原生体积差≤0.1%，不是与SolidWorks的建模差；模型实际绝对精度或API能力不能支撑该检查时先记验证条件未满足，不事后放宽。其它显式质量用例在执行前另固定相应目标；文件语法通过、正体积或文件很大均不足够。
- [ ] 导出前后revision、源PRT SHA256、实际几何与查询状态保持；只读任务的 `saved_file_reloaded_and_verified=false` 不当作失败，也不为凑true保存源件。若创建了副本，其建模创建/保存任务须另有重载核验。
- [ ] 正常拒绝不进unknown；真实worker失联仍保留现有unknown/显式探测规则。恢复动作只输出指导，不自动调用restore_baseline/ack/重启或清锁。
- [ ] 保留STEP成功回归；记录失败/不支持/未测范围。Creo9/10及装配能力不由本机12.4零件通过外推。

## Task 6：显式质量选项（稳定路径通过后再接入）

**Files:** Modify `src/creo_mechdog/schema.py` 的 `ExportOp`、`server.py:creo_export_model` 薄包装、能力/参考文档和必要结果投影；Test `tests/unit/test_stl_export_options.py`。

**Interfaces:** 可选 `stl_options={"chord_height_mm":0.05,"angle_control":0.1}`；缺省保持原调用兼容。该对象仅STL允许；未知键、布尔值、NaN/Inf、弦高≤0、角控制不在[0,1]时提交前拒绝。

- [ ] 回归覆盖独立工具与execute_plan同一参数、旧输入缺省不被悄悄改写、非STL拒绝stl_options、单位换算、质量数值的compact/full可读性。
- [ ] 不加入未经验证的BBox自动容差公式。回执说清请求值/传入SDK值，不把API返回0当作已测量网格最大误差；资源策略与质量策略分开。
- [ ] 专项测试通过后运行 `tools/dev_check.py --work-item BUG-130`；后续匹配SDK构建和Task5实机矩阵通过后才更新能力/状态。只改变资源/质量设置而原故障路径仍崩溃，不算完整修复。

## 交付与完成条件

最小交付为Task1–3及Task5；Task4按明确定义的失败分支执行，Task6可以后续版本交付。必须证明故障模型在约定质量下可导出、源件不变、文件与几何验收通过，才能把STL功能修复记为完成；旧路径AV根因未定位仍照实保留。仅修日志/增加拒绝/提高容差时标部分缓解。保留 `.stp` 作为短期替代，不将外部剖分或裁剪NURBS采样冒充原生STL修复。

自审：覆盖了空/坏数组、截断/坏文件、质量/单位、文件名路径、资源清理、接缝、只读与恢复边界；未安排未授权的实机操作、进程处置、主干提交或发布。本轮没有运行产品测试/编译，所有任务均尚未执行。

## 官方与代码依据

- 本机 `protoolkit/includes/ProPart.h:10–20,105–155`：结构/参数及整件释放；`ProSurface.h:742–810`：逐面结果数组分别用ProArrayFree。
- 本机 `ProUtil.h:1388–1513`：文件式STL API、3元素ProArray、质量flags、参数范围、文件名限制；官方示例 `protk_appls/pt_examples/pt_dbase/TestInterface.c:620–670`，不得复制示例交互菜单作为MCP实现。
- [PTC ProPartTessellate](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/usascii/creo_toolkit/api/dita/3437.html)、[整件释放](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/usascii/creo_toolkit/api/dita/3438.html)、[官方3D导出说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/usascii/creo_toolkit/user_guide/Exporting_3D_Models.html)。在线数字页编号与本机SDK不同，应按函数名/标题核对，不照搬页号。
