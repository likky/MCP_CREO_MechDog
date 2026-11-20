# MCP_CREO_MechDog 0.33.0

一句话：把 0.31.1 反馈里挡路的三处实机问题收进产品——面板作业不再因为会话没有“当前模型”而在开对话框前 -8 失败，元素树提取失败时可以选择保留特征并如实报告，装配约束的报错按实际类型说平面还是圆柱面；同时把面板回执的可信边界和发布记录门禁的盲点补上。

- 类型：MINOR（新增可选入参 `accept_unverified_completion`，新增回执与诊断字段）
- 日期：2026-11-20
- 公开工具：**109 个**（不变；能力通过既有工具的参数与回执扩展）
- 上一版本：0.32.0（`v0.32.0`，提交 `539a6b0145d84a9c15e538df6601d9538ecfd035`）
- 主台账：[BACKLOG](BACKLOG.md) · 发布记录：[RELEASE-0.33.0](validation/RELEASE-0.33.0.md) · 工作卡：[BUG-134](work-items/BUG-134.md) · [BUG-135](work-items/BUG-135.md) · [BUG-136](work-items/BUG-136.md) · [DEV-095](work-items/DEV-095.md) · [DEV-096](work-items/DEV-096.md)

## 对外可见变化

### 1. resident_panel 不再因 -8 在开面板前失败（BUG-134）

- worker 经 `ProEngineerConnect` 异步连接时没有用户当前激活上下文，`ProMdlCurrentGet` 恒为 `PRO_TK_BAD_CONTEXT`（-8）。开面板前改为优先使用 `ProMdlInit` 解析出的 board，board 为空才回退 `ProMdlCurrentGet`，两者都失败才报 `PANEL_MODEL_UNAVAILABLE`。
- 新增 `ProMdlMdlnameGet` 校验目标模型，避免面板落到别的模型；开面板前执行 `ProMdlDisplay` → `ProMdlWindowGet` → `ProWindowCurrentSet`，并把 `model_source`、`current_model_code`、`display_code`、`window_query_code`、`window`、`current_window_code` 写进 `panel_preopen`，失败时回执带实际码值。
- 面板提交回执的面板块新增 `model_name`，与作业目标模型一致；`creo_surface_loft` 的说明改为指向 `creo_capabilities` 的 runtime 分区（前置条件与失败码都在那里）。
- 本版**不新增**“显示/激活模型”公开工具，公开工具数不变。

### 2. element_tree 提取失败时的可控旁路（BUG-135）

- `creo_surface_loft` 新增可选参数 `accept_unverified_completion`（默认 `false`，经 `exclude_none` 序列化，旧计划字节不变）。仅当调用方显式接受、且没有 `boundary_conditions`、没有 `template` 时，`ProFeatureElemtreeExtract` 返回 -18 才不再立即回滚。
- 提取失败后会追加三次补全尝试并全部写入回执：`ProFeatureElemtreeCreate`（`extract_create_code`）、用创建树 `ProFeatureWithoptionsRedefine`（`accept_redefine_code`/`accept_redefine_element_errors`）、`ProSolidRegenerate` + `ProFeatureIsIncomplete` 复核（`accept_regenerate_code`/`feature_incomplete_after_regenerate`）。
- 接受时回执标注 `completion_verified_by="geometry"` 与 `completion_unverified_reason="element_tree_extract_unsupported"`，仍继续检查状态、quilt、面积与开闭；三次补全后特征仍不完整时以 `SURFACE_LOFT_ACCEPT_INCOMPLETE` 失败并回滚，不把空特征当成功。
- panel 路线、带边界条件或带模板的计划携带该参数会在准入阶段被拒，并指出不允许的树消费者。

### 3. 装配约束报错按实际类型（BUG-136）

- `mate`/`mate_offset`/`align`/`align_offset` 要求真实平面（`PRO_SRF_PLANE`），`insert` 要求真实圆柱（`PRO_SRF_CYL`），`csys` 跳过该检查；文案写出实际约束名与实际表面类型，不再把 `mate_offset` 当圆柱面要求。

### 4. 面板回执的可信度披露（DEV-095）

- 面板块带 `model_name`；`creo_session_status` 探针把 `release_numeric` 写入 `build/toolkit_health.json` 的 `host_release`（含 `worker_sha256` 与观测时间），后续健康度整文件重写时保留；“无记录 host release”的准入文案改为提示先读一次 `creo_session_status`。
- 认证记录的 `environment.payload_sha256` 与部署记录 `build/blend_callback_setup.json` 的 `dll_sha256` 不一致或不可读时，`unverified_bindings` 追加 `"payload_sha256"`；**只披露不拒绝**，作业照常执行，回执与 `panel_receipt.profile` 都能读到该披露。

### 5. 发布记录门禁交叉核对上一版本（DEV-096）

- `previous_release_commit` 不再只查 40-hex 形状：`RELEASE-<ver>.md` 中“上一版本”行写的提交号必须与交付快照一致；存在 `.git` 时还会用 `git rev-parse v<previous>^{commit}` 核对标签实际指向。

## 行为变化与升级注意

1. `accept_unverified_completion` 是可选参数，缺省行为与 0.32.0 一致；它只改变“提取失败后是立即回滚还是保留并检查”，不会让 Creo 补全它自己拒绝的几何。
2. 本版**有原生改动**（`native/panel_run.h`、`native/surface_loft.cpp`、`native/advanced.cpp`）：升级后需重新编译 worker（`bridge.py build`），不能沿用上一版本的构建。
3. 种子库 `compatible_server_version=0.33.0`，与 0.32.x 的种子包不通用。
4. `unverified_bindings` 是披露而非拒绝：出现 `payload_sha256` 时面板作业仍可成功，请结合认证记录判断证据边界。

## 验证

- 离线：`python bridge.py build` exit 0；全量单测通过（6 项跳过）；`ruff check` 与 `ruff format --check` 通过。
- 实机（本机 **Creo 10.0.0.0 / `release_numeric=42`**；此前文档写的 12.4 有误，Creo 12.4 本机未安装、未复测）：
  - 面板：作业 `7bb73fa98a764818843e85c2e9220b3a`（`acc_panel_20261120g`）`succeeded`，rev 1，`saved_file_reloaded_and_verified=true`；`blend_model_display`/`blend_window_get`/`blend_window_current_set`/`blend_window_activate`/`ProMdlCurrentGet` 全为 0，无 -8；quilt 60 / feature 54、单面、面积 1052.4223235864151 mm²、`geometry_check.verified=true`。
  - 元素树旁路：作业 `21535fea4d0f408bb74c2a0ccc08a99d` 在 Creo 10 上以 `SURFACE_LOFT_ACCEPT_INCOMPLETE` 失败（`extract_code=-18`、`accept_redefine_code=-1`、`feature_incomplete_after_regenerate=true`、quilt 0），新模型清理 `absence_verified=true`；该宿主只能走 resident_panel 路线。
  - 装配：`tools\test_t09_assembly_replay.py --live` 报告 `build/t09_assembly_replay_20261120.json` 六类约束全部通过（`mate_offset` 偏移 25→40 mm 被观察到）；圆柱面 `mate_offset` 被拒（`7e748410…`）、平面 `insert` 仍要求圆柱（`d7ddf3cb…`）、`csys` 成功且保存重载 true（`54ab2895…`）。
  - 可信度披露：`host_release.release_numeric=42` 在健康度重写后保留；面板准入 `unverified_bindings=["payload_sha256"]`（认证 `3c80bf15…`，部署 `41ad8198…`），作业仍 `succeeded`。
- 未验：Creo 12.4 与 Creo 9、`PANEL_MODEL_UNAVAILABLE` 失败构造、认证 payload 与运行中 DLL 的实时绑定证明、Arm7 原模型 60 条配合全量、WorkBuddy 黑盒。
