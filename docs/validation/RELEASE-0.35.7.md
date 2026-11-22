# 发布记录 v0.35.7

日期：2026-11-22
版本：0.35.7（PATCH）
上一版本：0.35.6（`v0.35.6`，提交 `13aa9e163da7569c548949de8c8c3b9b8bf3615a`）。
本次发布提交：见 `v0.35.7` 标签指向（本记录随该提交冻结；实际提交号与 Release id 由发布后的 POSTCHECK 回填）。

## 范围

- [BUG-149](../work-items/BUG-149.md)：只读作业不再永久占用模型——全部不确定出口保留准入状态、从不写 `pending_job`；`creo_cancel_job` 对只读作业（含已终态的历史占用）以元数据方式释放并回执 `readonly_release`；`creo_reconcile_model` 增加 `readonly_pending`。
- 公开工具仍 111，无原生改动；`creo_cancel_job` 对只读作业新增 `readonly_release` 字段，可写作业语义不变。

## 验收

- 环境：Windows x64 build 26200、Python 3.12.10、MSVC 19.29、Creo 10.0.0.0 / release 42（实机部分）。源码为本次发布提交，`dirty=false`，受测指纹与 `run_id` 见 `build/unit_test_report.json`、`build/unit_test_run.json`。
- 单元测试（本轮 `tools/test_unit.py`，报告落在 `build/unit_test_report.json`，运行状态在 `build/unit_test_run.json`）：全量 unittest 通过，`tests_run=4389`、`failures=0`、`errors=0`、`skipped=6`（跳过项均为本机环境不具备：MSVC 独立 helper 2 项、归档作业缺失 2 项、符号链接权限 2 项）。
- 定向回归：`tests/unit/test_bug149_readonly_release.py` 13/13——只读作业在交付缺失、交付未确认、超时三种出口都不锁模型；同条件下可写作业仍锁模型；`ToolkitBusy` 只释放只读占用；终态只读占用可释放；owner 存活时拒绝释放；重复取消不重复声明；模型不再持有时不动记录；可写终态作业行为不变；inspect 诊断。
- 开发检查：`tools/dev_check.py --skip-unit --work-item BUG-149` Ruff 0 发现、0 文件待格式化，576 个 Python 与 69 个 C++ 文件，`success=true`。
- 原生构建：`bridge.py build` exit 0，产物 `build/creo_worker.exe`；本版未改动原生接口签名。
- 实机（Creo 10.0.0.0 / release 42，证据留在 `build/bug149/live_20261122T161657.json` 与 `build/bug149/requery_20261122T161806.json`）：
  - 现场为 0.35.6 补验遗留的真实残留：模型 `0ce7c04e57bb4dc08b149a1fe64542d2`（`t10a_13_111744`，`revision=1`，`part_file` 存在）与只读作业 `07e6f30d8c1c4bc6989ae2e9b5466f96`（`readonly=true`、`worker_started=true`、`runner_pid=null`、`termination={attempted:false, reason:no_runner_pid}`）。
  - 释放前只读 `mass_properties`：`toolkit_busy`「Model has a pending job」，`blocking_job_id=07e6f30d…`、`blocking_operation=pending_job`。
  - `creo_cancel_job("07e6f30d…")`：`cancelled=false`、`status=unknown_outcome`、`readonly_release.released=true`、`previous_model_status=unknown_outcome`→`ready`、`geometry_may_have_changed=false`、`revision=1` 未变。
  - 释放后模型记录：`status=ready`、`pending_job=null`；同一模型重查作业 `881b44fcb84a44e5884b2085be95bf83` `succeeded`、`stage=verified`、`readonly=true`、体积 `1150.0` mm³、`revision` 仍为 1。
  - 只读作业在编译预检阶段失败（`fed46374…`，`worker_started` 未起）：模型保持 `ready`、`pending_job=null`，新不变量在真机生效。
- 发布记录门禁：`tools/check_release_records.py --version 0.35.7` exit 0；`tools/package.py` 的发布记录门禁（含本轮 `run_id`/源码指纹证据）在写 ZIP、sidecar、stage 之前执行并通过。

## 种子库

- 名称：`MCP_CREO_MechDog-0.35.7-seed-library.zip`；sidecar `MCP_CREO_MechDog-0.35.7-seed-library.zip.sha256`。
- 内容：24 个文件、9 个种子；`compatible_server_version=0.35.7`。
- SHA256：`2c925e6138f64102666fe6c679520f8522f6dd7e97b3afbae4ba07f9e24f4da2`，两次构建摘要一致，与 `docs/seed_package.json` 一致。

## 源码包

- 名称：`MCP_CREO_MechDog-0.35.7-source.zip`；sidecar `MCP_CREO_MechDog-0.35.7-source.zip.sha256`（一行 `<64 位 SHA256>  文件名`）。
- 由本版发布提交的源码构建；源码包摘要见同名 sidecar（一行 `<64 位 SHA256>  文件名`），不写入包内文件。打包器拒绝放松的文件集、非空 stage 与既有输出。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-149](../work-items/BUG-149.md) | 0.35.7 | v0.35.7 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 无 |

发布说明、发布记录与 POSTCHECK 的本地相对链接核对（0.23.2 起，必须全部可解析；外链与纯锚点跳过，逃出包根的链接直接判失败）：本节三份文档的本地链接均指向包内存在的文件，`tools/package.py` 在写出 ZIP 前复核同一批链接。

## 发布后远端核对

- 发布后执行，当前未验证。核对方式：`tools\check_release_assets.py --tag v0.35.7`，把真实附件列表、API digest、本地实算 SHA256 与 sidecar 比对结果追加到 `main` 的统一 POSTCHECK 与本段。
- Release 地址（发布后）：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.7`。

## 相对上一正式包核对（上一版本：0.35.6）

| 项目 | 上一版 | 本版 | 结论 / 注册影响 |
| --- | --- | --- | --- |
| native/third_party 原字节（含 json.hpp、第三方许可） | v0.35.6 源码包 | 未改动 | 字节未变 |
| 回调指纹（sha256-repo-lf-v1） | v0.35.6 源码包 | 未改动 | 指纹不变 |
| loader / callback / worker DLL SHA256 | v0.35.6 源码包 | 本版未改原生，仅重编 | 需重新构建 worker，注册路径不变 |
| protk.dat / 注册表路径 | v0.35.6 | 未改动 | 无需重新注册，重启服务即可 |

## 未验

- 真实“客户端中途退出”的协议层时序；只读作业与其它模型作业并发占用通道的释放时序。
- Creo 12.4 与 Creo 9（本机仅 Creo 10.0.0.0 / release 42）。
- WorkBuddy 黑盒验收与外部反馈环境（Windows 10 / Python 3.13 / Creo 9 SDK）复跑。
