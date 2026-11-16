# MCP_CREO_MechDog 0.26.0

一句话：把 0.25.0 四份机械臂反馈里已经能取证的部分落到可复验的契约上——首壁方向能被断言和回执，边/面锚点能按单点与圆弧唯一解析，发布门禁开始要求交付快照与发布前后证据；区域选区与 G2 圆角只交付契约或查证结论，能力仍不开放。

- 类型：MINOR（新增可选参数与回执字段、新增区域签名模块；无破坏性改名）
- 日期：2026-11-16
- 公开工具：**108 个**（与 0.25.0 相同）
- 上一版本：0.25.0
- 主台账：[BACKLOG](BACKLOG.md) · 发布记录：[RELEASE-0.26.0](validation/RELEASE-0.26.0.md) · 工作卡：[DEV-091](work-items/DEV-091.md)

## 对外可见变化

### 1. 组合首壁的宽度方向断言与质心（BUG-129）

`sheetmetal_base_flange` 新增两个可选字段：

- `expected_width_direction_world`：世界坐标单位向量，声明调用方期望的宽度方向；
- `width_direction_tolerance_deg`：0–90 度，默认 1 度。

原生在建模后计算模型 v 轴对应的世界方向，与期望冲突时**拒绝**并写明“宽度沿 model v = world (...)”，不再静默落错方向。回执新增 `width_direction_frame`（固定 `model`）、`width_direction_world`、`width_direction_tolerance_deg`、`width_expected` 与 `center_of_mass_mm`（原生质量属性）。旧调用不传新字段时行为不变，YZ 的 `u=+Y / v=+Z` 语义不变。

### 2. 单点直边、圆边与装配几何选择器（FEAT-068）

- `geometry_selector` 的 `target="edge"` 现支持三种互斥形式：`endpoints_mm`（可带 `point_mm` 过滤）、单独的 `point_mm`（按有限线段距离匹配）、`center_mm` + `radius_mm`（可带 `axis` 与 `point_mm` 圆弧角度过滤）。
- 圆边按圆心/半径/轴匹配；同名多段圆弧（例如圆柱顶缘被拆成四段）用 `point_mm` 的起止角与圆弧坐标系向量过滤后才允许唯一命中，零命中/多命中仍拒绝。
- 面选择器的 `points_mm` 必须落在该面片的包围盒内，解决同轴圆柱或大平面被拆分后“多点同分”的歧义。
- 装配约束 `coincident`/`concentric` 接受 `geometry_selector`：`concentric` 必须给 `radius_mm`，引用在提交前归一化；原生解析后会重新读取选中元素的真实类型，要求平面或圆柱，假面 ID 不再被当成可用引用。
- 选择器与装配引用的错误信息区分“形式不合法”“零命中”“多命中”和“类型不符”。

### 3. 区域边界签名契约（FEAT-069，部分交付）

新增 `region_selection` 模块：解析 `[B-REGION]` 的 `signature_yz_mm`，按草图 frame `(1.5, v, -u)` 把局部坐标映射到全局 `(y, z)`，在候选区域中做无序、反向等价的唯一匹配；重复段、非有限值、零命中与多命中都拒绝，`region_index_hint` 不参与选择。

本版**没有**把它接入 `ExtrudeOp`：`ProExtrude.h` 中没有“选中已有区域”的接口，原生选区创建、切除方向/输出侧与保存重开一致性都未取证，因此区域切除能力保持不开放。

### 4. 发布门禁：交付快照与发布前后证据（DEV-083）

- 打包前必须有 `docs/releases/<version>.json` 交付范围快照；逐 ID 表的 ID 集合必须与快照完全相等，`交付版本` 列必须精确等于本版，`实际 Release` 列必须是 `v<version>`。
- 「差异说明」只解释状态类别差异，不再豁免主台账字面比对；已移入完成档案的 ID 只接受已交付/部分交付类状态；表外活动行也与工作卡交叉扫描。
- 冻结包的 `remote_verification` 必须为 `pending`，发布记录必须写“发布后执行，当前未验证”，包内不得出现远端已验措辞。
- `docs/distribution_evidence.json` 成为 TXT 的唯一白名单，逐文件校验字节数与 SHA256；未列入的 TXT 不入包。

### 5. G2 圆角查证（DEV-090，不开放）

静态复查发现 `ProRoundConicType` 声明了 `PRO_ROUND_CURV_CONTINUOUS=3`，但同头文件元素表没有定义该值所需的子元素，也没有说明实体边是否接受。本版只修正结论措辞并登记候选路线，不改 schema、不开放能力；需先做单变量实机对照。

## 行为变化与升级注意

1. 新增字段均为可选；不传 `expected_width_direction_world` 时首壁行为与 0.25.0 一致。
2. 圆边选择器此前只接受 `center_mm`/`radius_mm`/`axis`；本版新增 `point_mm` 角度过滤，并继续拒绝 `circular` 与 `endpoints_mm` 混用。
3. 面选择器新增“点必须落在面片包围盒内”的约束；依赖旧行为跨面片匹配的调用可能从“多命中”变为更早、更明确的拒绝。
4. `coincident`/`concentric` 的 `geometry_selector` 在原生解析后会复核真实平面/圆柱类型；把边选择器传给面类关系会在提交前被拒。
5. 本版修改 `native/base_flange.cpp`、`native/geometry_selectors.cpp`、`native/advanced.cpp`、`native/generic.cpp`，升级后必须重编译 worker（`bridge.py build`）。
6. 种子库 `compatible_server_version=0.26.0`，与 0.25.x 的种子包不通用。

## 验证

- 离线：`tools/dev_check.py` 全量单测通过、lint 与格式检查 0 问题；`bridge.py build` 退出码 0。
- 实机：Creo 12.4.0.0（`auto_start_creo=false`，人工启动），一次性驱动只新建模型，逐项回执见 [实机验收](development/LIVE-ACCEPTANCE-0250-2026-11-16.md)：
  - M1：YZ 140×290、厚 1.5、翻边 60，实测 `width_direction_world=[0,0,1]`、bbox `[-60,0,0]–[1.5,140,290]`、质心 `(-8.522, 90.538, 145.0)`；期望 `[1,0,0]` 被拒并写明实际方向；保存重载通过。
  - A0：单点直边 id 137（体积 86579.917→86475.817 mm³）与圆边 id 55（R10，四段圆弧中唯一命中）圆角成功，保存重载通过。
  - A1：底座/销的平面与圆柱由选择器解析，`coincident`+`concentric` 成功，销 z=10.0，保存重载通过。
- 发布资料：`tools/check_release_records.py --version 0.26.0`、`tools/check_backlog_counts.py` 与 `tools/package.py` 的四附件/发布记录门禁均通过。

## 仍未验（本版不声称）

- A2：61 条 `[B-MATE]` 完整约束集；本机没有增强版 TXT 与测试机 `creo_plans_v0250`，未解析、未实机。
- Arm2 完整装配逐条对照：本版只验证独立 YZ 首壁，未重建完整件，也未核对 9.57 mm 偏移。
- A0 剩余：`Hom n7/n8` 角度倒角的参考面证据与 61 条边锚点批量运行。
- G1：原生“选中已有区域”的接口未找到，区域切除不开放。
- G2：`PRO_ROUND_CURV_CONTINUOUS` 的单变量实机对照未做。
- Creo 10 / Creo 9 实机与 WorkBuddy 黑盒未重测。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.26.0-source.zip`
- `MCP_CREO_MechDog-0.26.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.26.0-seed-library.zip`
- `MCP_CREO_MechDog-0.26.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 见[发布记录](validation/RELEASE-0.26.0.md)与 `docs/seed_package.json`。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.26.0>
- 发布后核对：发布后执行，当前未验证；`docs/releases/0.26.0.json` 的 `remote_verification` 在打包时为 `pending`，远端列表、标签指向与附件摘要只追加到 `main` 的 [POSTCHECK](development/RELEASE-POSTCHECK-2026-11-07.md)。

## 升级

1. 覆盖源码后运行 `python bridge.py build` 重编译 worker（本版含原生修改）。
2. 种子库换成本版 `seed-library.zip`（`compatible_server_version=0.26.0`）。
3. 若客户端用面选择器跨面片匹配，请先确认点位落在目标面片包围盒内。
