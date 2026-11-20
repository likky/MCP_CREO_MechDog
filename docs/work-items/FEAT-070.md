# FEAT-070：实体化重定义时重建失效主体参照

分类：**部分交付 0.34.0，剩余待验收**

类型：功能（建模能力补全）

优先级：P2

状态：部分交付 0.34.0，剩余待验收（已发布；`strategy=new` 与失败回滚通过；`strategy=existing` 稳定性、本轮 G1 复测及其他环境仍未验）

目标版本：0.34.0

来源与关联：[BUG-120](BUG-120.md) 任务 5（2026-11-20 结项章节）、`docs/BACKLOG.md` 2026-11-20 条目、证据 `jobs/4d9e1a78d34344dba22ecc98826d60d7/output/feature_250.xml`

分类依据：触发条件、当前行为与预期行为均已实机复现并定位到具体元素，属于“修改范围明确后填待开发”；唯一未定项是 Toolkit 侧对 body 元素的可写接口，需在实现前核实官方 SDK。

## 问题或目标

真实件 `ADOPT_A2ABB1FA`（model `a2abb1faebfd41daa8e234689e0d7393`）把 `边界混合 2` 接缝链改为相切后，quilt 142 接缝 G1 已达标（0.00749°，阈值 0.5°）且面组仍闭合，但下游 `BOW_BULB_SOLID`（feature 250，实体化）重新生成失败：

- Creo 故障排除器（`主体选项 → 右键 主体 2 → 错误内容`）报 `选择主体 > 主体 2 > 无效参考 / 主体不含几何。`；
- 元素树回读：`PRO_E_PATCH_QUILT=142` 有效，`PRO_E_BODY_USE=2`（`PRO_BODY_USE_SELECTED`）+ `PRO_E_BODY_SELECT=251` 带 `PRO_REF_INVALID`；
- 失败态下实体化仪表板 `确定` 灰显、`创建新主体` 灰显，移除主体条目后退化为红点 `选择项`，图形区无法拾取任何主体。

即：实体化必须写入一个“已存在且含几何”的目标主体，而该主体正是本特征生成、失败后不存在的对象，形成自锁，导致真实件无法保存为健康模型。

预期行为：提供一个受控入口，在实体化重定义时重建目标主体（写入有效主体参照，或先在模型中建立可用主体再挂接），使模型重新生成成功、无失败特征并可保存重载；不满足条件时明确失败并回滚，不留下半成品特征。

## 范围

包含：

- native 侧元素树处理：实体化（patch/solidify）特征的 body 相关元素（`PRO_E_BODY_USE` / `PRO_E_BODY_SELECT` 等）的读取、校验与重写；必要时调研并接入“创建/选择可用主体”的 Toolkit 接口。
- MCP 层入口：新增或扩展现有工具，接受 `model_id`、目标特征、目标面组与主体策略（重用已有主体 / 新建主体），走既有 revision 保护、单通道串行与 busy 拒绝。
- 失败路径：主体不可用时返回可诊断错误（phase、原始码、`feature_incomplete=true`），按既有规则回滚，不写入持久化终态以外的副作用。
- 保存重载校验：特征有效、几何/主体数量与体积断言、保存重载 `saved_file_reloaded_and_verified=true`。

不包含：

- Creo 界面自动化（点击/仪表板操作）不作为交付路径。
- 不自动重建其他失败特征，不改变 quilt 合并/缝合的既有实现。
- 不覆盖“仅点端相切”等既有负例规则，不扩大边界混合约束能力。
- 不在本条目内处理 WorkBuddy 黑盒验收。

## 验收标准

| 环境 / 用例 | 命令或操作 | 可判断的预期结果 |
| --- | --- | --- |
| Windows / Python | `tools/dev_check.py` 与针对性单测（元素树 body 元素构造、校验分支、回滚） | 无新增检查问题，新增回归全部通过 |
| 本机 Creo（release 42 会话）/ 匹配 SDK | 在 BUG-120 采用件等价场景：实体化重定义并重建主体 | 重新生成 0 失败，特征与主体有效；quilt 142 接缝 G1 保持 ≤0.5°；保存重载 `saved_file_reloaded_and_verified=true`，体积/主体数量与基线一致 |
| 本机 Creo / 失败路径 | 目标主体不可用或写入被拒 | 返回带 phase 与原始码的错误、`feature_incomplete=true`，模型回滚且无失败残留 |

原生范围不适用时写明原因。按当前项目规则，不要求 Creo 10 独立复测或双版本验收；其他环境收到具体反馈后再跟进，证据始终标明实际环境。禁止只写“能运行”或引用历史成功数代替本次验收。

## 实现与证据

源码身份：分支 `codex/feedback-0311-0320-feat070`，基于 main `95852899d893f590c6ef37a3724ac669ca7c845e`，`dirty=true`（未提交）。本机 **Creo 10.0.0.0 / release 42** 实机验收（2026-11-19 常设授权）。

变更文件：
- `native/generic.cpp`：新增 `generic_redefine_solidify_body`（及 `feat070_*` 辅助），读取/校验实体化（patch/solidify）特征的 `PRO_E_BODY_USE`/`PRO_E_BODY_SELECT`，按 `strategy`（`existing`/`new`）重写主体参照；调用 `ProFeatureWithoptionsRedefine` 时分配 `rd_opts=[PRO_FEAT_CR_NO_OPTS]` 与真实 `ProErrorlist`（修复空指针导致 worker 崩溃 + Creo 模态对话框阻塞消息循环的问题），失败回滚。
- `src/creo_mechdog/schema.py`：新增 `RedefineSolidifyBodyOp`。
- `src/creo_mechdog/capabilities.py` 与 `server.py`：新增公开工具 `creo_redefine_solidify_body`（公开工具 109→110）。
- 23 项单测；工具数契约测试 109→110。`.\.venv\Scripts\python.exe bridge.py build` exit 0 → `build\creo_worker.exe`。

实机（本机 Creo 10.0.0.0 / `release_numeric=42`，采用件等价场景）：
- **`strategy=new` 成功**：模型 `51abe8c9c4264ee5b63df878aa2b861a`，作业 `973e4318b1f540dd9bf66541c4815174`；`status=succeeded`、`stage=verified`、`saved_file_reloaded_and_verified=true`；回执 `old_body` use=2(selected) ref_id=251 → `new_body` use=0(new)，`redefine_code=0`、`regenerate_code=0`、`feature_incomplete=false`；`body_counts_before objects=2 → after objects=3`（新主体实体化）；`volume_before = volume_after = 55087038135.823044 mm³`，与 BUG-120 基线完全一致；`native.log` 跑到 `BUILD_SUCCESS=1`/`DISCONNECT=0`/`result_delivery_complete`，无崩溃、无模态。该路径打破 BUG-120 的自锁（`BOW_BULB_SOLID` feature 250 在失败态把主体 251 选作自身参照，`PRO_REF_INVALID`，GUI 也无法重建；`strategy=new` 不依赖预存主体 251）。
- **失败路径**：模型 `1c1099e76241489c86db3313e2f8aef1`，作业 `f05c076d9b564c4f903f3d2371142fd6`，瞄准非实体化特征 1（基准 RIGHT）→ `status=failed`、`phase="locate_body_branch"`、`feature_incomplete=true`、`effect_status="rolled_back"`，消息 `FEAT070_NO_BODY_BRANCH: ... query_code=-4`；无崩溃、模型干净。

已知限制（如实记录，不掩盖）：`strategy=existing` 在该几何上触发 Creo 10 / release 42 内核 `dig_err`——经 `resolve({"kind":"body"})` 取默认主体再 `ProSelectionToReference` 时 Creo 内部回溯弹出模态对话框，worker 阻塞，看门狗在 `native_timeout_seconds=180` 后结束进程。`strategy=new` 是可靠的自锁解除路径；`strategy=existing` 的该几何不稳定记入本卡与发布记录，待后续抑制 UI 或换用其他主体解析方式时再跟进。

未测范围：Creo 12.4 / Creo 9、真实船体非圆剖面、WorkBuddy 黑盒；quilt 142 接缝 G1（本轮未重新测量，沿用 BUG-120 任务 5 记录的 0.00749°≤0.5°）。
