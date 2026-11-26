# MCP_CREO_MechDog 0.35.7 版本说明

版本类型：PATCH。承接 0.35.6。

上一版本：0.35.6（`v0.35.6`，提交 `13aa9e163da7569c548949de8c8c3b9b8bf3615a`）。

## 亮点

- **只读作业不再永久占用模型**：[BUG-149](../work-items/BUG-149.md) 修掉 0.35.6 补验两次撞到的死局——客户端在只读质量查询结束前退出后，作业停在 `unknown_outcome`（`termination.attempted=false`、`reason=no_runner_pid`），模型继续以它为 `pending_job`，此后所有请求被 `toolkit_busy`「Model has a pending job」拒绝；`creo_cancel_job` 因作业已终态只回「nothing was cancelled」，而恢复侧的 `ack_no_mutation`/`ack_failure`/`abandon_stalled_recovery`/`restore_baseline` 没有一条接受这种占用。根因是只读计划（准入仅限 `INSPECTION_ONLY_OPERATIONS`）在超时、看门狗停滞、`native_result.json` 缺失、交付未确认等分支被当成可写作业：模型被置 `unknown_outcome`，收尾无条件写 `pending_job`。
- **只读作业的新不变量**：`run_generic_job` 进入时取定 `readonly` 与 `admitted_status`（准入已证明 `ready`），所有不确定出口对只读作业保留准入状态、收尾从不写 `pending_job`，消息直接说明“作业结果未知、模型未变、可重新查询”；`ToolkitBusy` 分支中只读作业释放自己从未派发的占用。几何、`revision` 与已保存文件不受影响。
- **元数据式释放**：`creo_cancel_job` 用 `_job_readonly`（以 `job.json` 的入参标志为准，旧作业回落 `request.json`，读不到按可写处理）定级；只读作业 `geometry_may_have_changed=false`，并走新增的 `_release_readonly_reservation`——只改模型记录（清 `pending_job`；仅当状态是本类作业自己写下的 `unknown_outcome` 时才恢复 `ready`），前提是模型仍持有该作业且该作业记录的 runner/worker 均不再存活（`taskkill` 成功即作为停止证据，无需再探活）。对已经终态的历史占用同样生效，回执带 `readonly_release`；可写作业语义一字未改。
- **恢复侧有明确出口**：`creo_reconcile_model` 的 inspect 增加 `readonly_pending` 块，直接指出这是一次只读占用、其唯一出口是带该 `job_id` 调用 `creo_cancel_job`，不占用任何 native 工作。
- **实机闭环（本机 Creo 10.0.0.0 / release 42）**：现场就是 0.35.6 补验留下的真实残留——模型 `0ce7c04e…`（`t10a_13_111744`，`revision=1`）与只读作业 `07e6f30d…`（`readonly=true`、`worker_started=true`、`runner_pid=null`、`no_runner_pid`）。释放前提交只读 `mass_properties` 被 `toolkit_busy`「Model has a pending job」拒绝（`blocking_job_id=07e6f30d…`）；`creo_cancel_job` 回 `cancelled=false`、`status=unknown_outcome`、`readonly_release.released=true`、`previous_model_status=unknown_outcome`→`ready`、`revision=1` 未变；同一模型随后提交的只读查询作业 `881b44fc…` `succeeded`/`stage=verified`、体积 `1150.0` mm³、`revision` 仍为 1。另一次只读作业在编译预检阶段失败（`fed46374…`，`worker_started` 未起）后模型保持 `ready`、`pending_job=null`，即新不变量在真机生效。
- **回归保护**：新增 `tests/unit/test_bug149_readonly_release.py` 13 项——交付缺失、交付未确认、超时三种出口都不锁只读作业的模型；同条件下可写作业仍锁模型（防止把修复做成“所有作业都不锁”）；`ToolkitBusy` 只释放只读占用；终态只读占用可释放；owner 仍存活时拒绝释放；第二次取消不重复声明释放；模型不再持有该作业时不动记录；可写终态作业行为不变；inspect 的 `readonly_pending` 诊断。

## 变更总览

- Python：`src/creo_mechdog/generic_bridge.py`（`readonly`/`admitted_status` 一次取定、`_job_readonly`、`_release_readonly_reservation`、四个不确定出口与 `ToolkitBusy` 分支、`cancel_job` 只读语义）、`src/creo_mechdog/reconciliation.py`（`readonly_pending` 诊断与 `_pending_job_status` 扩展）、`server.py`（`creo_cancel_job` 与 `creo_reconcile_model` 的契约说明）。
- 原生：无改动（只读作业本就不写几何，修复全部在 Python 侧的作业记录与准入状态）。
- 测试：新增 `tests/unit/test_bug149_readonly_release.py` 13 项。
- 文档：`docs/work-items/BUG-149.md`、[BUG-131](../work-items/BUG-131.md) 的契约变更段、`docs/BACKLOG.md`、`docs/DEVELOPMENT.md`、0.35.0 反馈计划与 `docs/RELEASING.md` 版本约定同步；README 版本段只换版本与条目。

## 交付项

| 项 | 摘要 |
| --- | --- |
| [BUG-149](../work-items/BUG-149.md) | 只读作业在全部不确定出口保留准入状态、不写 `pending_job`；`creo_cancel_job` 元数据式释放历史占用并回执 `readonly_release`；inspect 报 `readonly_pending`；实机用真实残留闭环，新增 13 项单测。 |

## 已知限制（如实记录）

- 只读作业的**真实**“客户端中途退出”时序未在协议层抓取；实机复现的是它留在磁盘上的等价状态（终态只读作业 + 模型占用 + 无 runner pid）。
- 只读作业与其它模型作业同时占用通道时的释放时序未构造（单通道串行下并发 busy 立即拒绝，属已声明行为）。
- 本版无新增公开工具（仍 111），无接口删除或重命名，按 PATCH 递增；`creo_cancel_job` 对只读作业新增 `readonly_release` 回执字段，可写作业回执保持不变。

## 附件与摘要

Release 发布后见 `https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.7`。

四个附件（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）：

- `MCP_CREO_MechDog-0.35.7-source.zip`
- `MCP_CREO_MechDog-0.35.7-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.7-seed-library.zip`
- `MCP_CREO_MechDog-0.35.7-seed-library.zip.sha256`

- 种子包 SHA256：`2c925e6138f64102666fe6c679520f8522f6dd7e97b3afbae4ba07f9e24f4da2`（24 个文件、9 个种子，两次构建摘要一致，与 `docs/seed_package.json` 一致）。
- 源码包：由本版发布提交的源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。

## 未验

- Creo 12.4 与 Creo 9（本机环境为 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收。
- 外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）复跑。
