# MCP_CREO_MechDog 0.25.0

一句话：把机械臂反馈里"选不准边、配不准面、改不了尺寸、建不出带折弯的首壁"逐条落到可验收的操作上——新增一个钣金组合能力、两类几何选择器与符号定位尺寸，装配约束的偏移开始真的生效，倒角多了角度模式，阵列多了方向模式，计划也可以从本地 JSON 文件提交。

- 类型：MINOR（新增公开工具与计划操作/参数，无破坏性改名）
- 日期：2026-11-15
- 公开工具：**108 个**（0.24.0 为 107），新增 `creo_sheetmetal_base_flange`
- 主台账：[BACKLOG](../BACKLOG.md) · 发布记录：[RELEASE-0.25.0](../validation/RELEASE-0.25.0.md) · 工作卡：[DEV-090](../work-items/DEV-090.md)

## 对外可见变化

### 1. 组合式开口折线首壁：`sheetmetal_base_flange`

新增计划操作 `sheetmetal_base_flange`（MCP 工具 `creo_sheetmetal_base_flange`）：输入两段长度、90° 折角、板厚、宽度、内半径、`k_factor` 与 `origin`，内部先建 native 矩形平面壁，再在其自由端加 90° 法兰。

它是**组合能力**，不是单特征基体法兰：

- 回执 `composed_features` 逐项列出两个真实特征与其特征 ID，`single_feature=false`；
- 体积按"单侧加厚 + 内半径四分之一圆环折弯"给出上界，实测超出 1 mm³ 或 0.5% 即失败；
- 包络为 `first_leg × width × (second_leg + thickness)`，`second_leg_mm` 自板外表面起算。

与反馈参照件（SolidWorks `SMBaseFlange`，792.323 mm³）仍有约 22 mm³ 差异，根因是中面加厚与单侧加厚的角部差别。本版**不声称等价**，也不承诺复刻该体积口径。

### 2. 几何选择器：按坐标唯一定位边和面

`round`/`chamfer`/`sheetmetal_flange` 接受 `{kind:'geometry_selector', ...}`：`target` 为 `edge` 或 `surface`，必填 `tolerance_mm`，边按无向端点匹配并可用 `point_mm` 过滤，面按 `points_mm`/`axis`/`radius_mm`/`center_mm` 联合匹配。

- 必须**唯一命中**；零命中或多命中都在提交前拒绝，并给出候选数与命中 ID。
- 未知字段、零/多匹配、布尔或非有限数值、非单位轴一律拒绝。
- `coordinate_space="assembly"` 只在装配侧 `assembly_reference` + `assembly_component` 上有效：原生读取该组件的放置矩阵并求逆，把装配坐标换到组件自身帧后再匹配；移动组件的窗口被显式清空。

### 3. 按特征与符号定位尺寸

`DimensionValue` 支持 `{feature, symbol, value, ...guards}` 二选一替代 `{id}`：只在目标特征自身的尺寸里按符号匹配，0 或多命中都拒绝并给出特征 ID 与候选维度 ID，不回退到全模型第一个同名符号。混用两种写法、缺项、布尔/负 id、空符号在校验层拒绝。

### 4. 装配约束：偏移真的生效，关系词可读

- `mate`/`align`/`insert`/`csys` 带非零 `offset` 现在被拒绝（此前该值写入但内核按零偏移求解）；带符号偏移继续用 `mate_offset`/`align_offset`。
- 新增 `coincident`（映射 `mate`，要求面类引用）与 `concentric`（映射 `insert`，只接受 `{kind:'surface',id:N}`）；`parallel`/`distance` 虽有 SDK 声明，但本机未做写入/求解验证，仍在准入期拒绝并说明原因。

### 5. 距离+角度倒角

`chamfer` 新增 `chamfer_type="distance_angle"`，追加 `angle_deg`（0–180，不含端点）与 `angle_reference`（面引用或 `target="surface"` 的几何选择器）。实测确认：腿距量在 `angle_reference` 指定的面上，`PRO_E_RNDCH_LEG1` 是线性腿距、`LEG2` 是角度（度）；换参考面即换测距面，无需额外 flip 字段。

### 6. 方向线性阵列：`linear_pattern`

新操作 `linear_pattern`：`direction`（模型坐标单位向量）、`spacing`（正毫米）、`count≥2`、`flip` 只反方向。原生把方向绑定到模型上平行的第一条直边（没有直边时绑定法向平行的第一个平面），绑不到时拒绝并给出候选数，不创建替代基准轴。

### 7. `plan_file`：从受控本地 JSON 提交计划

`creo_execute_plan` 新增 `plan_file`：必须是绝对本地普通文件（拒绝 UNC/设备/相对路径与目录），上限 16 MiB，UTF-8/可选 BOM，拒绝重复键与非有限数字；只读一次并回显 `{path, resolved_path, bytes, sha256}`。与 `operations` 互斥，解析出的数组仍走完全相同的门禁、revision、busy、事务与断言，执行时不再重读文件；不递归加载 include，也不执行文本中的命令。

## 行为变化与升级注意

1. `mate`/`align`/`insert`/`csys` 上的非零 `offset` 从"写入但被忽略"变为**拒绝**；需要偏移请改 `mate_offset`/`align_offset`。
2. `sheetmetal_base_flange` 的体积上界按上述折弯模型计算，与 SolidWorks 主壁口径不同，别拿参照体积当期望值。
3. `sheetmetal_base_flange`、`linear_pattern`、倒角角度模式与选择器都新增了原生代码；本版改了 `native/advanced.cpp`、`native/generic.cpp`、`native/base_flange.cpp`（新增）、`native/geometry_selectors.cpp`（新增）、`native/linear_pattern.cpp`（新增）、`native/sketch_coordinates.cpp`，升级后必须重编译 worker（`bridge.py build`）。
4. `plan_file` 的路径必须能被本机执行器直接读到；只支持单文件 JSON 数组。

## 验证

- 离线：`tools/dev_check.py --work-item DEV-090` 为 `success=true`（全量 3655 项单测通过、`lint_findings=0`、`unformatted_files=0`）；`bridge.py build` 退出码 0。
- 合并说明：本版基于已发布的 0.24.1 合入，因此同样包含其启动参数、无图形会话容错、worker 启动回退与 toolkit 提示（BUG-125—128）；该批验收沿用 [0.24.1 记录](../validation/RELEASE-0.24.1.md)，本版未重复实机。
- Creo 12.4.0.0（`release_numeric=44`）实机，逐项回执写在 [DEV-090](../work-items/DEV-090.md)：
  - 组合首壁：job `f85ddda1…`，体积 770.185802 mm³ / 上界 770.185796 mm³，包络 `u 0…8 / v 0…20 / n −12…2`，`composed_features` = 平面壁 49 + 法兰 104，`saved_file_reloaded_and_verified=true`。
  - 几何选择器：边与面各一例成功、远端点点例被拒；装配坐标面选择器成功，偏离平面 40 mm 与移动组件使用装配坐标均被拒。
  - 符号定位尺寸：`{feature:49,symbol:"d9"}` 重载后 value=12.0；错误符号被拒。
  - 装配约束：`mate_offset=5` 间隙 5.0 mm、残差 0.0，基座移动后销随动。
  - 角度倒角：参考顶面法向夹角 70.0°、去除体积 618.18 mm³ 与解析值一致；换参考面后腿长方向随之改变；两例均保存重载通过。
  - 方向线阵：`member_count=2`、实例圆心实测间距 42 mm，`flip` 反转方向；斜向无平行参考被拒。
- 降级说明：T7 草图坐标拒绝诊断的措辞改动只有编译与单元证据，没有实机样本；`arc_by_endpoints` 与两阶段形状误差未做。

## 仍未验（本版不声称）

- T6c 区域切除（缺 B-REGION 稳定签名）、T7 弧端点与两阶段形状误差。
- `parallel`/`distance` 配合词，多约束同时求解、驱动尺寸变化后的随动。
- 装配的保存重载一致性（装配任务不提供 `saved_file_reloaded_and_verified`）。
- 组合首壁与反馈参照件 792.323 mm³ 的等价性。
- Creo 10 / Creo 9 实机，WorkBuddy 黑盒验收。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.25.0-source.zip`
- `MCP_CREO_MechDog-0.25.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.25.0-seed-library.zip`
- `MCP_CREO_MechDog-0.25.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 见[发布记录](../validation/RELEASE-0.25.0.md)与 `docs/seed_package.json`。
- Release：<https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.25.0>
- 发布后核对：`python tools/check_release_assets.py --tag v0.25.0`，四附件与两个 sidecar 逐一致，结果写回[发布记录](../validation/RELEASE-0.25.0.md)与[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md)。

## 升级

1. 覆盖源码后运行 `python bridge.py build` 重编译 worker（本版含原生新增与修改）。
2. 种子库换成本版 `seed-library.zip`（`compatible_server_version=0.25.0`，与 0.24.x 的种子库不通用）。
3. 客户端若带 `mate`/`align`/`insert`/`csys` 的非零 `offset`，升级前改成 `mate_offset`/`align_offset`。
