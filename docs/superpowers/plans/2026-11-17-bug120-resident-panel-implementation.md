# BUG-120：T1-C 后正式 MCP 面板建面实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. 按 D1—D8 实施；本文件替代旧计划中仍以 T1-A/B/C 为待执行工作的部分，不改写历史证据。

**Goal:** 让 AI 通过正式 MCP 在 Creo 10 按真实截面引用自动创建原生边界混合曲面，可靠确认结束、保存重载，再扩展至完整球鼻艏。

**Architecture:** 复用现有 stdio→bridge 单通道→generic_bridge→原生 worker→已注册 loader/payload。`surface_loft` 增加显式 `creation_route="resident_panel"`；新协议、引用解析和受控完成流程独立于普通实体 Blend。先交付第一方向纯曲线子集，导线/尖点随后扩展；不引入 UDF 或固定模型模板。

**Tech Stack:** Python 3.12/Pydantic/unittest；C++17、Creo C TOOLKIT、现有 MSVC 与不可变 DLL 部署；官方录制的命令片段。

**Spec:** [BUG-120 当前目标与约束](../../work-items/BUG-120.md)、[T1-C 原件复核](../../development/CREO10-T1C-REVIEW-2026-11-17.md)。旧[完整球鼻艏计划](2026-11-16-creo10-bulb-native-creation.md)的几何数据/实体化验收继续适用；接口与工程接入以本文为准。

## 0.27.0 发布基线与纳入方式

本计划基于已发布`0.27.0`，发布提交`fc1efaefa68cda1c0b4d46849f18933c35050b64`，发布后记录提交`f6da633`。已核对本地源码/版本说明/发布记录与[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.27.0)，不重新发布或改写这些冻结证据。新实现从该基线向前开发；目标为后续未发布版本，实施时再确定版本号。

| 已发布内容 | 本计划如何使用 | 新增工作/保留边界 |
| --- | --- | --- |
| BUG-122同worker准入身份 | D1直接复用`surface_loft_admission_identity()` | 仅新增tree/panel按路线分流；目标10第二次提交无空壳和黑盒仍需验，不把整卡说成完成 |
| panel未知结果的Python消费者 | D4/D5复用unknown、pending、revision、效果降级与compact保留 | 补原生生产者、会话级面板保护和端到端回归，不重复实现已发布分支 |
| BUG-131取消/看门狗/收尾 | D4接入现有`creo_cancel_job`、预算、stall回执和恢复入口 | 强制终止worker不等于Quit；新增面板等待的阶段预算/日志进展、跨模型保护，见D4.2—D4.4 |
| BUG-130逐面STL及参数域细化 | D7最终实体可选调用现有STL导出，作为单独只读回归 | 旧14m精度、ASCII性能、预算、装配及Creo9/10仍由BUG-130下版余项跟踪，不成为原生成型的前置条件 |
| BUG-132选择器、FEAT-069区域适配、DEV-090 G2 | D6覆盖共享计划/分派/构建的相关回归 | `coaxial:any`不放宽曲线唯一性；区域适配不等于原生选区；圆角G2不证明放样曲面的曲率连续性 |
| BUG-129坐标文档、BUG-106恢复裁定 | D2沿用现有坐标合同，D4/D6沿用已发布恢复边界 | 不新增隐式旋转，不偷偷引入`adopt_session_copy`来收养T1-C未存盘会话 |
| BUG-020导出诊断归档 | 可选导出保留既有artifacts/diagnostics及源件保护 | 已归档项不重开；新建面日志/回执按当前规则保留 |

0.27.0公开工具为109，本计划扩展既有工具参数/后端，默认仍为109，不因内部helper/profile另加工具。3810项单测和Creo12.4实机是**基线历史证据**，不能替代新代码、新回调和目标Creo10验收。0.27.0没有改回调指纹/DLL，现源码仍协议3/ABI1；D3的协议4/ABI2是本计划新工作，未来升级需准备新注册代际，不能套用0.27.0“无需重新注册”的结论。

## Global Constraints

- 长度毫米、角度度；标签沿用小写字母开头、字母数字下划线、最多28字符。
- 不改建模文本来掩盖创建缺陷；不固定模型名、几何ID、站位或截面数量组合。循环由输入长度驱动，上限是明确资源边界。
- 保留旧调用默认元素树路线及其全部已有输入；不静默回退、不替换为实体Blend/STEP。
- 单通道、busy立即拒绝、无队列/自动重试；成功只在保存重载核验后推进一次revision。
- 本次要求计划，不构成编译执行器、启动/连接Creo的授权。原生构建/实机按当次明确授权执行；不擅自终止进程、清锁/unknown或覆盖用户模型/已加载DLL。沿用已发布控制工具的worker终止语义不等于授权结束Creo/nmsd；实际强制取消/看门狗注入另按相应授权验证。
- 复用0.27.0已交付的BUG-122观测准入、panel未知结果Python保护及BUG-131作业控制；新增面板专属衔接和回归，不把这些基础分支重新列为未实现。
- T1-C源码只作参考，不能直接把其独立DLL、30秒等锁、共享request或success/committed字段搬进正式链路。
- 模板描述维护命令兼容性，不保存用户几何；能力只覆盖实测版本/语言/profile，不按release_numeric=42外推全部Creo10。

## Review Focus

1. Done入队成功但面板仍开：D3/D4必须保留unknown，不能扫描/保存/回滚猜结果。
2. 基准面编号、复合曲线、异主模型被当作曲线：D2须从源feature枚举验证，API返回0不足以放行。
3. 重复选择触发TOGGLE反选、旧宏串入下一任务：D3/D4必须验证一次性票据及本任务宏链结束。
4. 旧元素树不支持误拦新路线、旧普通Blend语义改变：D1/D6分别验证。
5. 近似bbox被当精确几何、旧quilt被当新产物、只测会话未测落盘：D5/D6必须有独立判据。

## 交付分两阶段

**A：第一方向正式可用。** `resident_panel` 接受2—8个MCP独立草图标签，每个恰好一条真实、非退化、非复合的开放曲线；无导线/点/边界条件/template。2截面straight，3—8截面smooth，沿用既有插值规则。曲线可以是线、弧、B样条；不沿用普通实体Blend的XY/Z固定框架限制。此阶段能交付一个完整、正确、已保存的原生曲面，不声称已修复完整球鼻艏。

**B：球鼻艏闭环。** 扩展末端单点和第二方向2/3条完整单曲线导线，覆盖7曲线+末点+3导线，再镜像、合并、封后端、实体化。每种新增引用/collector取得独立目标机证据后开放。A完成不能替代B。

**候选验收入口：** D6使用显式开发测试模式启动的隔离stdio会话，仍调用相同公开工具和正式submit/worker链。`tools/test_surface_loft_panel.py --live --candidate-profile ID`仅在本次授权范围内，为其子进程设置内部候选上下文，绑定本run、workspace、实际profile摘要及worker/loader/payload身份；普通服务默认不接受候选profile。公开工具不新增跳过验证参数，客户端JSON不能自行声明candidate。候选结果显式标记candidate、记录测试身份，不能作为已发布能力。

profile命令片段及参与执行的元数据在实测前冻结；认证结果单独存入`templates/panel/certifications/`，绑定实测代码/构建依赖摘要、profile摘要和环境，不修改已测命令或DLL。认证记录本身不参与产生其所绑定的运行代码摘要，但必须独立做分发完整性校验。D6通过后普通模式读取匹配认证，并做去掉候选模式的最终冒烟；代码/profile改变则旧认证失效，重新验收。

已完成输入：T1-A命令录制、T1-B按ID2/3/5截面及模型/视角/尺寸变化、T1-C原件关联/取消录制/非平面中截面作用。BUG-122 helper和Python unknown保护已随0.27.0进入基线，但新的panel原生后端尚未实现。D1—D8是开发任务简称，不新建第二套工作台账。

## 固定的实现决定

### 协议与真正完成

共享协议升为4：`contract="blend-selection-v4-role-aware-mm"`；**loader ABI升为2**。当前ABI1没有`ProMacroLoad`，payload又不直接链接/注册Toolkit，故不能只改协议号。扩展`MechDogCallbackApi`，至少提供受控macro_load、真实feature/curve验证及结束观测实际使用的SDK接口；由注册loader填充，payload只通过vtable调用。

新请求绑定`job_id/request_id/nonce/model_name/profile_id`及不可变引用`{role,index,feature_id,curve_id}`。首版role仅`first_dir`；几何ID由worker从标签解析，客户端不提交宏或任意owner。nonce用系统CSPRNG生成，结果必须逐项匹配请求身份。

```text
prepared → recording → selection_recorded → done_queued
        → terminal_observed + outer_macro_drained + dashboard_closed
        → feature_verified → saved_reload_verified → committed
失败：确认可安全取消且模型/面板匹配才走cancel；否则unknown并保留保护。
```

`selection_recorded`只表示API记录，不冒充collector真实链数；`done_queued`只表示宏载入成功。`committed`由保存重载收尾确定，回调不能提前写它。[ProMacroLoad官方契约](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/italian/creo_toolkit/api/dita/3136.html)仅承诺载入；不以固定25/45秒睡眠或`ProMacroExecute`作为OK/Done完成栅栏。

### 命令身份与宏链结束

不用固定无参“下一个引用”命令模拟携带nonce。[uiCmdCmdActFn](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/portuguese_br/creo_toolkit/api/dita/4364.html)的action参数不提供该保证。

采用每请求不可复用的命令票据：Prepare为各select位置及Finalize/AfterTerminal/OuterDrain注册唯一安全命令名，command ID绑定不可变`request_id/nonce/role/index/action`。同一票据只消费一次；退休票据永不绑定新请求，迟到旧票据无副作用。

未查到可依赖的ActionRemove，不假设卸载能注销回调。初版设**每payload代际最多512个已注册命令**的资源预算；Prepare先为本请求N+3个命令预留全额。容量不足或部分注册失败在开面板前拒绝，已注册项保留墓碑，不能静默复用/无限注册或自动重载、重启。此为待实机验证的生命周期限制，不是截面几何限制；披露remaining_capacity及准备指引。

受控外层序列是`Open → Select[0..N-1] → Finalize → OuterDrain`；Finalize只在所有记录成功后排`Done → AfterTerminal`。取消路径排`Quit → yes → AfterTerminal`，其余选择/Finalize票据成为无副作用操作，最后仍须到达外层OuterDrain。要求AfterTerminal与OuterDrain均来自本请求，且没有本请求的原生Done/Quit仍待执行，才允许下一请求。票据不能隔离迟到的原生Done/Quit，宏链排空和面板关闭仍是独立条件。

## 文件与职责

| 部分 | 修改/新增位置 |
| --- | --- |
| 路线与能力 | `src/creo_mechdog/surface_ops.py`、`capabilities.py`，`server.py`、`bridge.py`、`generic_bridge.py`、`native/worker.cpp` |
| 引用与状态纯逻辑 | 新`native/panel_selection_request.h`、`panel_selection_state.h`、`panel_references.h/.cpp` |
| 驻留实现与ABI | `native/blend_sync.cpp`、`blend_loader.cpp`、`callback_api.h`、`callback_identity.h`、`callback_runtime.h`；新`native/panel_callback.h`；`src/creo_mechdog/blend_callback.py` |
| 原生后端 | 新`native/surface_loft_panel.h/.cpp`，`native/generic.cpp`最小适配/分派/异常收尾 |
| 结果与几何 | `native/quilt_query.h`、`src/creo_mechdog/operation_results.py`、`compact_sections.py`、`job_projection.py`及必要terminal_effect接线 |
| 作业控制/会话保护 | `generic_bridge.py::cancel_job/_run_worker_with_watchdog/_watch_worker_log`、`bridge.py::admission_holder/toolkit_lock`、`native_stage.py`、`reconciliation.py`；新`panel_wait.py`、`panel_session_guard.py` |
| 版本化UI profile | 新`templates/panel/manifest.json`、命令片段及`certifications/`；新`src/creo_mechdog/panel_profiles.py` |
| 构建/分发身份 | `bridge.py`依赖与编译、`server.py`源码身份、`src/creo_mechdog/reconciliation.py`、`release_integrity.py`、`tools/package.py` |
| 验收驱动 | 新`tools/test_surface_loft_panel.py`、`tools/test_creo10_bulb.py`，`tests/unit/test_*panel*.py`、`tests/native/test_panel_*.cpp` |

worker后端沿用当前generic.cpp的包含/分派组织，不在本卡进行全库编译单元迁移；payload仍是真正单独编译的DLL。新增include、host API和profile都进入各自实际构建指纹及源码清单，不能仅靠全native目录哈希掩盖callback漏依赖。

### D1：公开路线契约与按路线准入

**接口：** `SurfaceLoftOp.creation_route: Literal["element_tree","resident_panel"] | None = None`；省略/None不序列化。公开`creo_surface_loft`透传同字段。build-info独立`features.surface_loft_panel`，compiled状态与certified profile/runtime readiness分开。

- [ ] 先加`test_surface_loft_panel_schema.py`：旧payload不变；panel2/8标签通过；1/9、裸ID/edge/point、guide、非空边界条件、template和未知route在job前拒绝。旧树2—32及已有输入不缩减。
- [ ] 修改schema/薄工具包装及native分派入口。panel后端未完成时自报available=false，缺声明/未验证profile明确拒绝，不落回树路线。
- [ ] 修改准入：树路线才查询旧树SDK/Extract观测；panel单独查新worker声明。补“树不可用但panel已验证可用”和“树可用但panel未就绪拒绝”。复用`surface_loft_admission_identity()`，不重写BUG-122。
- [ ] 能力披露分`routes.element_tree`与`routes.resident_panel`；旧顶层字段含义有兼容测试，不能因为默认树不可用隐藏已支持的新路线，也不能把compiled当runtime ready。
- [ ] 实现`panel_profiles`的候选/已认证准入：仅开发driver内部上下文可放行指定候选，环境/任一摘要不符拒绝；普通客户端、伪造公开参数、未启用测试模式均拒绝。保留同一正式MCP调用链供D6端到端测试，避免“必须验收后才能调用、又必须调用才能验收”的循环。
- [ ] Run：新增schema/route-admission测试，加现有`test_surface_loft_schema`、`test_surface_loft_kernel_admission`、`test_surface_loft_runtime_observation`。必须证明拒绝不建job、不取通道。

**产物：** 用户可明确选择新路线，当前未实现的后端仍安全关闭。

### D2：真实曲线引用解析与复核

**接口：** `PanelCurveRef{label, owner_name, feature_id, curve_id, curve_type, length_mm}`；`resolve_panel_sections(model, sections, aliases) -> vector<PanelCurveRef>`；`validate_panel_curve(model, ref) -> validation receipt`。定义放`panel_references.h`，返回实际观测及API错误，不复制输入冒充回读。

- [ ] 加`test_panel_reference_validation.py`/纯原生测试：基准面ID40反例、同ID不同owner、feature下零条/多条曲线、复合/闭合/零长度、类型查询失败、模型切换必须拒绝。
- [ ] 从MCP标签定位源feature，按PRO_CURVE实际枚举并检查所属关系、非复合类型、开放性和有限正长度；不用`ProModelitemInit(PRO_CURVE)`返回0替代存在/类型验证。
- [ ] 建立不可变引用表；callback每次选择前复核当前模型与源feature成员关系；验证失败锁定且不发送Done。选择句柄和Toolkit数组按原API所有权释放。
- [ ] 记录每条真实feature/curve及几何摘要；结果核对父依赖集合，明确它不表示collector顺序。
- [ ] Run：引用错误/模型切换/SDK失败资源释放用例；获准后再在目标10验证实际枚举与原基准面反例。

**产物：** 传错对象会在选择前得到具体拒绝，API假成功不再推进完成流程。

### D3：协议4、ABI2、一次性票据与受控Done

**接口：** 纯逻辑`PanelSelectionState.prepare/record/finalize/observe/release`；事件显式带票据身份和slot。SDK适配在`panel_callback.h`，由`blend_sync.cpp`调用，普通Blend仍保持原OVERRIDE行为。

- [ ] 先加`test_panel_selection_protocol.py`及`tests/native/test_panel_selection_state.cpp`：重复票据不再注入；跳序/错nonce/错模型/旧票据不推进；active/locked时新Prepare拒绝；512容量边界及部分注册失败不启动UI。
- [ ] ABI2增加macro_load及D2/结束观测实际需要的SDK函数指针，更新loader/payload身份、不可变部署及实际依赖。协议3/ABI1混用明确not_ready；不自动卸载或改安全策略。
- [ ] 在同一collector中首次OVERRIDE、随后TOGGLE；每位置最多调用一次。C++异常不得跨Toolkit回调边界；失败粘住状态，不靠改request_id复位。
- [ ] Finalize仅排受限Done+AfterTerminal；返回0记done_queued，返回非0不能记committed。所有标记按job+nonce单独存放，校验类型，检查写盘和原子替换结果；不删除旧文件后忽略rename错误。
- [ ] Run：协议/ABI/部署/旧Blend callback回归；获准后核对目标SDK声明并构建，实测Prepare上下文注册、名称长度、容量。记录单调event_seq验证`Done或Quit/yes → AfterTerminal → OuterDrain`，分别覆盖正常Done、Done被拒、选取失败后的受控取消；T1-C仅证明某些Done先于tail，不替代这条两层全序。反序或缺事件保持unknown，未证实配置不发布为可用profile。

**产物：** 不串单、不重复反选，选取失败不触发Done，旧普通Blend行为保留。

### D4：可靠结束、取消与原生事务保护

**接口：** `run_surface_loft_panel(PanelRequest, PanelRuntime) -> PanelOutcome`；`PanelExitObservation{method, supported, closed, reason, evidence}`。worker在开UI后只等本请求文件事件，结束未确认前不发异步扫描/重生成/保存等调用。

- [ ] 先加`test_surface_loft_panel_state.py`：只有done_queued、尾命令到达但面板仍开、超时、marker为空/类型错/旧nonce、取消仍有确认框，均不得成功或自动回滚。
- [ ] 实现同步AfterTerminal/OuterDrain回调，分别记录原生终结序列与外层宏链的耗尽。尾命令不独自证明Done有效。
- [ ] 只允许在外层Finalize/OuterDrain之前由驻留回调决定受控取消；要求AfterTerminal的event_seq严格早于OuterDrain。OuterDrain先到或之后才发现需要取消时，不追加一段宏再复用旧屏障，直接unknown。没有已知的Toolkit队列长度查询；“本任务宏耗尽”来自已实测模板全序与最后票据，不能编造队列查询回执。
- [ ] 实现并在目标10验证退出观测适配：首选核对`ProCmdCmdIdFind`+`ProCmdBracketFuncAdd`对原生边界混合命令的事件时序，配合本profile面板控件状态和唯一新增完整特征；必须分别观察打开、Done、Quit、Done被拒。若bracket只覆盖入口回调或控件状态不可可靠读取，observer返回unsupported，路线保持未开放，不能换成固定睡眠/顶层窗口数量/试发异步查询猜退出。
- [ ] 已验证当前模型/面板匹配时，失败可排独立Quit+yes受控取消；其余外层票据无副作用，仍等最后OuterDrain。Done已排队后不承诺抢占取消。不在本卡扩大`creo_cancel_job`既有强制终止契约。
- [ ] 新建目标特征唯一、有效、非incomplete且新quilt关联正确才进入几何核验；Done失败但尾命令执行不得误判。
- [ ] 未确认时native返回`success=false, panel_execution_unconfirmed=true, rollback_succeeded=false`。在`generic.cpp`普通catch/检查点重载/新件erase前处理该状态，跳过与活动面板冲突的清理；结果投递与退出确认分开。复用现有Python unknown/pending/revision/compact保护并补原生生产者回归，不只mock消费者。
- [ ] Run：状态机/异常收尾/单通道/unknown分页回归；获准后验证普通Done、已知失败后的取消、取消后合法请求及面板结束时序。实机故障注入另需授权，不用杀进程或清保护构造通过。

**D4.2 — 接入0.27.0强制取消，保留语义差异。**

- [ ] 复用`generic_bridge.cancel_job`和`test_job_control.py`：worker前取消为cancelled/no geometry；worker后强制终止为unknown/geometry_may_have_changed，不能改写成面板已Quit或回滚。
- [ ] 在面板候选/正常请求中分别测“Done尚未排队”“Done已排队”“公开cancel与正常终态竞态”；强制取消后即使驻留DLL继续写入迟到的完成marker，也不能把已记录unknown改成succeeded、推进revision或自动release。
- [ ] 面板内部受控Quit+yes只在D4规定的可信上下文和顺序内执行；不从cancel工具开第二条Toolkit连接补发Quit。保留0.27.0终态取消无操作、终止失败继续running等合同。

**D4.3 — 面板等待与看门狗衔接。**

- [ ] 区分实际监视来源：`_watch_worker_log`检查`worker.log`字节增长，`native_stage.py`读`native.log`作进度投影；只写callback sidecar或native.log不会刷新现有watchdog。
- [ ] worker文件轮询只接受本job/nonce/profile且序号递增的真实阶段/选取事件，把有界摘要及时flush到worker.log与native.log，compact保留stage/wait reason/last_progress；重复marker、旧nonce、读文件成功、循环心跳都不算新进展。
- [ ] 新`panel_wait.py`实现阶段预算判定：在可信panel等待阶段采用受限的phase deadline，始终不晚于原job总deadline；原runner先计算上界，客户端或sidecar不能自行无限续期。预期无新日志的等待窗口由已验证profile及明确预算限定，不全局关闭watchdog，也不靠无条件打印续命。
- [ ] 将该判定实际接入`_run_worker_with_watchdog`/`_watch_worker_log`，传入受信job请求与总deadline：可信panel等待期按独立phase deadline判断，普通阶段继续0.27.0日志停滞合同。不能只写helper和阶段日志而保留watcher无条件按静默杀进程。用缩短的假时钟预算证明合法等待可跨原stall阈值、仍在phase deadline内；超过phase/job deadline则沿既有终止/unknown与会话guard收尾。
- [ ] phase deadline、失联或job总预算到期均为unknown，保留stall/timeout及终止证据和D4.4保护；不能根据worker结束判断UI已关闭。
- [ ] 新`test_panel_wait_watchdog.py`用假时钟/进程模拟覆盖：合法有界静默等待、预算后真停滞、重复/旧marker不续期、总预算不被延长、日志双通道及强制取消。真实终止/注入只在获准临时模型上执行。

**D4.4 — 跨模型持久会话保护。**

- [ ] 新`panel_session_guard.py`提供`reserve/inspect/require_clear/retire`。在可能启动UI的worker前持久登记guard，绑定job/nonce/profile及会话/回调身份，后续原生证据落本job目录；所有普通Toolkit入口在`bridge`层检查，不限于同model的pending_job。
- [ ] 现有`admission_holder`会清理终态/死亡runner的普通claim，`cancel_job`成功终止也会清claim。保留这些旧合同，但**不得用它们清面板guard**；取消、watchdog、超时、stdio重启和callback代际改变后，UI未确证退出仍拦住其他model_id的建模及普通live查询。纯本地作业/日志查询仍可用。
- [ ] 原owner的可信结束证明或显式恢复流程才可退役guard：扩展现有reconciliation inspect/apply证据，使token绑定guard/session/nonce，确认面板退出或旧Creo会话确已结束后才允许后续恢复；普通ack_failure/abandon_new、PID死亡、健康状态缓存或迟到旧marker不能自动解除。退役UI保护不等于接受几何变化，模型unknown仍独立处理。
- [ ] 原生未启动UI且有可信no-effect证据时可正常退役预留；证据缺失按未确认处理。恢复只使用既有串行Toolkit通道及明确的恢复上下文，不自动连接/重启/清锁。
- [ ] 新`test_panel_session_guard.py`覆盖：worker被取消后另一模型submit被拒；stdio重启仍保护；旧代sidecar不解除；普通claim可清但panel guard不清；同job可信结束可退役；恢复token过期/会话变化拒绝；普通非panel任务保持0.27.0行为。

**产物：** 确认结束才继续；不确定时保留模型和保护，不假报成功或安全回滚。

### D5：真实几何、保存重载和结果回执

**接口：** 新结果携带`creation_route/profile/selection_intent/selection_record/exit_observation/feature_id/quilt_id/geometry_check/saved_file_reloaded_and_verified`；不伪造create/extract成功码。compact保留阶段、失败原因、实际标量及其状态，详细样点写附件。

- [ ] 加`test_surface_loft_panel_receipt.py`：模型已有quilt不能当新产物；错feature关联、空/多面组、零面积、已记录引用但未进入产物必须失败；近似bbox不计作精确边界。
- [ ] 源曲线/控制数据从原生对象回读，与输入重建位移≤0.001模型mm（仅为引用解析/输入映射验收，不是曲面全域精度）；对每条源曲线端点/节点区间抽样，检查结果面到网络的距离≤0.01模型mm。投影后验证有效裁剪域；标记抽样方法/数量/失败，不宣称全域误差上界。
- [ ] bbox增加来源与近似性说明；`ProSurfaceDataGet.xyz_min/max`不得当严格0.01mm极值验收。平面线例独立使用真实边界端点、边长与面积；不改容差掩盖失败。
- [ ] 在现有锁内保存、关闭/重载核验，并复查目标feature/quilt和关键几何；只有全部通过才提交、推进一次revision和release。取消/普通失败仅在UI退出和恢复确证后报rolled_back。
- [ ] Run：结果、几何未知值、预算/分页、保存失败和revision回归。确认panel成功不会写成旧树`kernel_completion=supported`。

**产物：** 用户拿到可重开的正确曲面和可信回执，失败原因在compact中可见。

### D6：第一阶段正式MCP验收

**Files:** `tools/test_surface_loft_panel.py`默认只离线校验，显式live且获本轮授权才连接；profile清单记录目标机环境/源录制/摘要和本实现证据。

- [ ] 新建独立临时模型，按实际公开工具创建2—8截面各例；平面案例面积800±0.01mm²、周长120±0.01mm、边界端点符合预期、单开放quilt、无材料增加、保存重载true。
- [ ] 重建T1-C三截面非平面例，创建次序与空间次序不同；中间3mm、面积约810.7517mm²作为外部参照，并按源网络实测。**本次正式工具必须保存重载**，不借用T1-C只在会话里的结果。
- [ ] 改模型名、真实几何ID、视角、尺寸/平移仍成立；输入在真实源feature中解析，不按旧编号/像素/父数组顺序选取。
- [ ] 检查前置拒绝、重复/迟到票据、Done未完成、正常取消和后续请求、unknown/pending/revision。内部故障用离线模拟；需要真实注入时单独获准。
- [ ] 普通实体Blend、默认树路线、旧schema/模板及相关12.4能力做适用回归；不要求恢复全项目双版本门槛。记录版本/源码提交dirty/源码及worker/loader/profile摘要、job/model/revision与模型SHA。
- [ ] 增加0.27.0接入回归：109工具清单、BUG-122按同worker记录后第二次树请求不建空壳、新panel不受树-18误拦；BUG-131取消/看门狗与D4.4跨模型保护；FEAT-069既有适配回执、BUG-132默认唯一性/coaxial边界、DEV-090已有圆角参数不回退。共享代码改到哪里就验证哪里，不把Arm7/装配根因/原生选区等独立余项变成BUG-120前置。
- [ ] 使用上述候选上下文完成正式调用链验收；原生构建、开发检查、实际几何/保存重载全通过后写独立认证记录。去掉候选模式，以同一profile/执行代码重新跑平面和非平面保存重载冒烟，再将A子集作为正式可用能力交付。编译通过、原探针通过和静态ready均不能代替此步。

**产物：** 第一方向曲线已通过正式MCP端到端验收，可独立交付。

### D7：导线、末端点与真实球鼻艏

- [ ] 由开发agent在获准目标10录制第二方向collector激活和末点选取；保持原件，不猜控件名。扩展schema/profile/票据role与上限；每方向首条replace、后续toggle分别验证。
- [ ] 依次验证：两截面+2导线、+3导线、末端单点收敛；再做7曲线无点无导线→加点→加3条完整导线。每步检查网络、唯一产物及保存重载。
- [ ] 沿用已准备的v2输入及100mm/m缩比；保留已知约0.004305模型mm交点差，拒绝自动吸附/放宽阈值。必要输入适配单独给出来源和位移证据。
- [ ] 镜像/合并/后盖/实体化后验1个有效闭合实体、零开放边、正体积、对称及截面位置，保存重载一致；体积相近不能替代形状/网络核验。
- [ ] 相应子集通过才扩展公开能力。只有完整球鼻艏通过才关闭BUG-120成型修复，STL BUG-130不在本任务内。
- [ ] 可选交叉回归：原生实体成功提交后，以独立只读导出作业调用0.27.0现有STL路径，保留参数、闭合/绕序/抽样偏差及诊断，核对源SHA/revision不变。Creo12.4既有0.0899mm只是历史参照，不能外推本次新件或Creo10；旧14m的0.1115mm、ASCII优化、预算和装配/其它版本继续留BUG-130，导出失败不抹去已完成的原生成型验收。

**产物：** 目标Creo10环境中的完整原生球鼻艏。

### D8：文档、黑盒验收与发布

- [ ] 更新能力/语法/README/工作卡与BACKLOG，明确A/B已通过范围、profile环境、资源预算、回调准备及未测项。
- [ ] 在`release_integrity.py`新增panel库/认证清单的严格读取与`panel_profile_library_files()`，由`validate_release_inputs`及`tools/package.py::source_files()`实际调用；现有`template_library_files()`只收录elemtree，不能假定panel目录自动入包。新增/遗漏/路径逃逸/坏摘要/过期认证均有打包负例；不发行models/jobs/build/SDK/常量表。
- [ ] WorkBuddy只用公开MCP黑盒创建、查询、测量、保存重载与revision检查；不要求读源码、编译、跑本地脚本或GUI研发取样。内部机制结果另记。
- [ ] 开发分支验证/审查完成不擅自合main；用户要求交付到main时按RELEASING同步新版本、正式Release/附件/SHA和远端核对，不复用已发布版本。
- [ ] 以0.27.0为上一正式版本核对新增参数/回执及实际工具数；源码、注册影响和目标机证据按本次新改动记录。不能沿用0.27.0回调未变/无需重注册的升级说明。发布新版本，不改写v0.27.0标签、附件、冻结发布记录或历史未测范围。

**产物：** 能复测、限制明确的正式版本；源码实现、开发者实机和WorkBuddy证据分别记录。

## 执行顺序与并行

`D1 ∥ D2 → D3 → D4 → D5 → D6 → D7 → D8`。D1/D2可并行开发，纯协议测试可并行写；UI/Toolkit实机始终由一位执行者串行操作。D3的命令注册/资源预算和D4的可靠退出观测是当前主要技术风险，均有明确停止开放条件。

本文件是具体实现计划，尚未实施D1—D8，也不是实机授权。实现时先核对当前未提交改动和已完成保护，使用既有`codex/`开发分支，只提交本任务改动；不把其他工作混入交付。
