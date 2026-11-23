# MCP_CREO_MechDog 0.36.1 版本说明

版本类型为 PATCH，公开工具数 111。本版只改验证工具链，不改建模链路与原生执行器。

上一版本：0.36.0（`v0.36.0`，提交 `bc2052e27cb34f03af2e9fcea259cf426bac7d5b`）。

- **自带 stdio 冒烟脚本**。`tools/test_mcp.py` 自 0.4.2 把 `creo_capabilities` 改为默认 compact 分页后未再更新，按文档运行必然在 `families.loft_seed.interpolation` 上 `KeyError` 失败，且不在任何门禁里。现在脚本只断言 compact 的家庭索引，再用 `detail="full", section="families"` 逐页取回完整条目后断言细节（当前 40 族 / 2 页，`loft_seed` 位于第 2 页）。[BUG-151](work-items/BUG-151.md)
- **契约单一来源**。能力契约期望集中到 `src/creo_mechdog/mcp_contract.py`，脚本只负责渲染问题清单；`tests/unit/test_mcp_contract.py` 用真实 `_capabilities_payload` 与真实分页器守住同一份期望，并覆盖 compact 出现细节字段、字段取值变化、翻页不完成三个漂移方向。变基到 0.36.0 时该护栏立即拦下 FEAT-074 新增的 compact `runtime_admission` 键，白名单同步后重新通过。
- **无会话验收模式**。`tools/test_mcp.py --protocol-only` 走真实 stdio，核对工具清单、loft 输入 schema、capabilities 契约与无效几何拒绝，不需要已连接的 Creo 会话。该脚本不进入 `dev_check` 的离线脚本清单：服务 lifespan 会启动后台协调器并触发更新检查。

本机环境为 Windows x64 / Python 3.12.14，无已连接 Creo 会话，未改动 `native/**`，因此本版没有实机建模证据，也不宣称建模行为变化。`creo_session_status` 与 `--create` 建模路径待有会话时补测，Creo 9/12 与 WorkBuddy 黑盒同样未验。详见[验收与发布记录](validation/RELEASE-0.36.1.md)。

## 附件

- `MCP_CREO_MechDog-0.36.1-source.zip`
- `MCP_CREO_MechDog-0.36.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.36.1-seed-library.zip`
- `MCP_CREO_MechDog-0.36.1-seed-library.zip.sha256`

种子包 SHA256 为 `c37d6c7dba91624f315761e24a86f0e806a8dafec9b44b94dd67fd47087ff630`。源码包摘要记录在同名 sidecar 中，两份 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.1)
