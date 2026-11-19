# MCP_CREO_MechDog 0.30.0

一句话：把装配位姿的容差与矩阵约定在 Python 和原生两层统一起来，并让约束失败能定位到具体条目——显式 `rotation_tolerance` 不再被原生固定值拒绝，列向量矩阵写法可显式声明且只转置一次，约束整组替换的边界和失败阶段都写进回执与文档。

- 类型：MINOR（新增可选入参 `rotation_convention`、新增回执与诊断字段；`rotation_tolerance` 上限收紧属输入契约变化，见下）
- 日期：2026-11-19
- 公开工具：**109 个**（不变；能力通过既有装配工具的表达扩展）
- 上一版本：0.29.0
- 主台账：[BACKLOG](BACKLOG.md) · 发布记录：[RELEASE-0.30.0](validation/RELEASE-0.30.0.md) · 工作卡：[DEV-092](work-items/DEV-092.md) · [BUG-133](work-items/BUG-133.md) · [FEAT-012](work-items/FEAT-012.md)

## 对外可见变化

### 1. 显式位姿容差在两层生效（BUG-133）

- 此前 Python 允许 `rotation_tolerance`（只要求正有限），原生 `assembly_rigid_transform` 固定用 `1e-6`：六位小数的 28° 矩阵配 `rotation_tolerance=1e-5` 能过 Python、仍被原生拒绝，回执数字也未说明实际门槛。
- 现在创建（`assemble_component`）、重定位（`component_placement`）与失败回显读取同一个有效容差；省略或 null 仍取公开默认 `1e-6`。
- 上限冻结为 **`1e-3`**：准入同时要求 `max |R*Rᵀ−I| ≤ t` 与 `|det−1| ≤ t`，反射的 `|det−1| = 2`、缩放基偏差远超 `1e-3`，因此上限内不会放进非刚体变换；此前 `1e-3` 以上的调用现在被明确拒绝（不再静默接受）。
- 只对显式 `rotation_matrix` 生效：Euler 输入带 `rotation_tolerance` 直接拒绝。
- 原生错误文本改用 `%.9g`（原来 `std::to_string` 只有六位小数），`1.129488e-06` 这类残差不再被显示成 `0.000001`。

### 2. 显式矩阵约定（FEAT-012）

- 新增可选 `rotation_convention: "row" | "column"`，缺省等价 `row`。`column` 表示 `p_parent(column) = R * p_local(column) + T`，原生入口只转置一次。
- 准入始终测**规范行矩阵**：列输入先转置再判定。六位小数样例的自身行残差 `9.62666e-7`、转置后 `1.023309e-6`，两层都按后者给结论，避免“按原始数组判定、按转置写入”的不一致。
- 请求数组与约定原样保留，不做修复；成功回执新增 `input_rotation_convention` 与 `rotation_tolerance`，原有 `rotation_convention` 仍描述解算得到的行向量变换。

### 3. 约束整组替换与阶段化诊断（DEV-092/T4）

- 文档与字段说明明确：`component_constraints` 每次是**该组件的一整组替换**（`ProAsmcompConstraintsSet`），旧约束不追加、旧 FIX 放置会被替换；`max_length=20` 只属单个组件，`assemble_component` 的初始约束数组没有该上限，22 条跨组件不是整组上限。
- 约束失败新增 `failed_constraint_index`（0 基）、`failed_constraint_type`、`constraint_stage`（`type`/`offset`/`self_reference`/`allocation`/`reference`/`surface_type`/`side`/`offset_write`）与 `constraint_reason`；整组求解失败时索引为空、阶段 `solve`、原因 `solver_failed`，原始 Toolkit 码照旧保留。
- 参考语法新增“装配位姿矩阵与约束组”一节，列出 `parallel`/轴点 `distance` 仍是 named gap，`align` 不能等价替代平行约束。

## 行为变化与升级注意

1. `rotation_tolerance` 超过 `1e-3` 现在是输入错误。若旧调用依赖更大的值，请改用精确正交矩阵或从角度重建。
2. `rotation_convention` 只能与显式 `rotation_matrix` 同时使用；Euler 输入带该字段会被拒绝，避免无效字段静默生效。
3. 本版**有原生改动**（`native/assembly_pose.h`、`advanced.cpp`、`generic.cpp`）：升级后需重新编译 worker（`bridge.py build`），而不是沿用 0.29.0 的构建。
4. 种子库 `compatible_server_version=0.30.0`，与 0.29.x 的种子包不通用。

## 验证

- 离线：修改前先补失败回归（原生 harness 因固定 `1e-6` 断言失败、Python 专项 2 failures + 1 error），修复后 C++ harness `success=true`、装配相关专项单测通过；合并 `origin/main` 0.29.0 后 `bridge.py build` exit 0，`tools/dev_check.py --work-item DEV-092` 全量单测 **4065 项通过（0 跳过）**、lint 0、未格式化 0。
- 证据：`docs/validation/feedback-creo13-assembly-2026-11-19/IMPLEMENTATION-2026-11-19.md`。
- 发布资料：`tools/check_release_records.py --version 0.30.0` 与 `tools/package.py` 的四附件/发布记录门禁。

## 仍未验（本版不声称）

- Creo 实机：新建/重定位放置、原生测量、约束求解与保存重载、revision、失败回滚。
- Creo 内核是否接受放宽到 `1e-5` 的六位小数矩阵——两层门槛一致只说明契约一致。
- 逐实例 `bbox_world_mm` 与逐面面积字段（T3 仅完成 SDK 语义查证）。
- 22 条原样回放、`keep_fixed`/`append`、`parallel`/轴点 `distance` 正向依据（T5 缺原始输入）。
- WorkBuddy 黑盒验收。
- Creo 9/10 运行期与其他版本；本机 Creo 12.4 结果不外推。

## 源码包与校验

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.30.0-source.zip`
- `MCP_CREO_MechDog-0.30.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.30.0-seed-library.zip`
- `MCP_CREO_MechDog-0.30.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包：24 个文件、9 个种子，SHA256 `e210ee229590a474c5fc22c5d81a0d39448f09055b55011671e6eac7177c2c13`，与 `docs/seed_package.json` 一致。
- Release：发布后登记；当前 `docs/releases/0.30.0.json` 的 `remote_verification` 为 `pending`。
