# 发布记录 v0.36.1

日期为 2026-11-23，版本类型为 PATCH。

上一版本：0.36.0（`v0.36.0`，提交 `bc2052e27cb34f03af2e9fcea259cf426bac7d5b`）。

## 验收范围

本版只改验证工具链：重写 `tools/test_mcp.py` 的 `creo_capabilities` 断言、新增 `src/creo_mechdog/mcp_contract.py`、新增 `tests/unit/test_mcp_contract.py`。未改 `native/**`，未改任何 MCP 工具的签名、参数或返回契约，公开工具仍 111 个。因此本版没有新的 Creo 实机建模证据，Creo 10 的建模与恢复结论沿用 0.36.0，未在 Creo 9/12 复验。

环境：Windows x64 / Python 3.12.14 / 无已连接 Creo 会话。执行环境禁止 `reg.exe`，`vcvars64.bat` 因此无法从注册表发现 Windows SDK；原生夹具编译改用显式 `INCLUDE` / `LIB`（`src/creo_mechdog/build_support.py` 的 `COMPILER_ENV_KEYS` 约定的同一组键）指向 MSVC 14.44.35207 与 Windows SDK 10.0.26100.0，编译与执行均通过。该限制只影响本机夹具编译，不影响发布的源码包。

## 修复内容

被修的问题：`tools/test_mcp.py` 自 `0e92ab7` 后未随 `creo_capabilities` 0.4.2 的 compact 分页契约更新，按文档运行必然在 `families.loft_seed.interpolation` 上 `KeyError`，exit 1，且不在全量单测或 `dev_check` 的任何一项里。修复前原始输出见 `build/bug151_repro_before.txt`（3.2 s 复现，与是否连接 Creo 无关）。

修复：脚本改为 compact 只断言家庭索引，再用 `detail="full", section="families", limit=50` 逐页取回完整条目后断言细节（当前 40 族 / 2 页，`loft_seed` 位于第 2 页）；契约期望集中到 `src/creo_mechdog/mcp_contract.py`，脚本与单测共用同一来源；新增 `--protocol-only` 供无 Creo 会话时验收协议面。设计与取舍见 [BUG-151](../work-items/BUG-151.md) 和[修复计划](../superpowers/plans/2026-11-23-bug151-test-mcp-capabilities-drift.md)。

护栏的首次实战：变基到 0.36.0 后，FEAT-074 给 `surface_loft` / `loft` / `loft_seed` 的 compact 条目新增了 `runtime_admission`，`tests/unit/test_mcp_contract.py` 立刻报出 `compact family loft must stay an index ... found ['runtime_admission']`；把该键并入索引白名单后重新通过。契约漂移由此从"跑脚本才失败"变为"单测里失败"。

## 单测证据

发布候选在 0.36.1 工作树上跑 `tools/test_unit.py`，全量 unittest 通过，0 失败、0 错误。下列数字取自本轮 `build/unit_test_report.json`，该报告不随源码包分发。

本轮 `run_id=f08e18e7e2a0488590cdbab38f0c7318`，执行 4,403 项，0 失败、0 错误、0 跳过，耗时 1,080.7 s，报告 `version=0.36.1`、`status=completed`、`success=true`。受测提交 `2396e1b0f0c91743c4d3454e921dd9a5c23ec336`（分支 `codex/bug151-test-mcp-contract`；运行时本版文档与 `version.py` 尚未提交，故 `dirty=true`），源码指纹 `34b7174012c17d2c0aac901cc9cc3cfd3a2ebe3053a49162da04e3fcfa23aa5b`，统计 664 个受 Git 跟踪的 `.py` 与原生头/源文件。指纹只取这些文件，提交本版文档与版本号不改动其中任何字节，指纹在提交后保持不变。

首次与第二次全量运行各有 8 项与 4 项失败，均为本机环境与本文件缺失，不是产品缺陷：6 项 `SeedPackagingGateTests` 因本文件尚未创建而报 `broken local link`；2 项原生夹具因执行环境禁止 `reg.exe`、`vcvars64.bat` 取不到 Windows SDK，编译报 `crtdbg.h` 缺失。补齐本文件并显式提供 `INCLUDE` / `LIB` 后，本轮 4,403 项全绿。

## 冒烟脚本结果

`tools/test_mcp.py --protocol-only` 在当前工作树退出码为 0：工具清单、`creo_new_loft_part` 输入 schema、capabilities 契约与无效几何拒绝均通过，未连接 Creo。完整模式（含 `creo_session_status` 与 `--create` 建模）需要已连接的会话，本版未执行，仍记为待补。

## 附件

- `MCP_CREO_MechDog-0.36.1-source.zip`
- `MCP_CREO_MechDog-0.36.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.36.1-seed-library.zip`
- `MCP_CREO_MechDog-0.36.1-seed-library.zip.sha256`

种子包 SHA256 为 `c37d6c7dba91624f315761e24a86f0e806a8dafec9b44b94dd67fd47087ff630`，包含 24 个文件、9 个种子，两次独立构建摘要一致。两个同名 sidecar 分别记录各自 ZIP 的实际摘要，源码包摘要只在 sidecar 中登记。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-151](../work-items/BUG-151.md) | 0.36.1 | v0.36.1 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 脚本协议面已验收；`--create` 建模与 `creo_session_status` 路径需已连接会话，仍待补 |

## 远端核对

已发布并核对。Release id `455098850`，附注标签对象 `094ac5878ae2eb4d61f51562c0fa7f63c5cec92d` 指向 `a9bf80d`，`tools/check_release_assets.py --tag v0.36.1` 退出 0，四个附件重算摘要与 sidecar 一致。附件字节、摘要与环境侧发布通道见 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.1) 和[发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。

Creo 9/12、外部模型、WorkBuddy 黑盒均未纳入本版实机。台账与本版相关的一行见 [docs/BACKLOG.md](../BACKLOG.md)。
