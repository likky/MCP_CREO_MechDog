# MCP_CREO_MechDog 0.45.2 版本说明

2026-11-26 PATCH，公开工具数 111。上一版本：0.45.1（`v0.45.1`，提交 `0177e227dd42587541e3e01628647deda53e4dea`）。

- 服务、任务桥接和 Creo 启动实现移入 `src/creo_mechdog/`。新安装用项目虚拟环境的 Python 执行 `-m creo_mechdog`，根 `server.py` 仍可供已有 MCP 客户端启动。
- AI Agent 可以沿用现有提示词、工具名、输入参数和作业轮询方式。两个入口共用同一安装目录下的模型与任务。入口路径校验和直接导入 Python 内部模块的脚本迁移见 [Agent 迁移说明](MIGRATION.md#自动化脚本的兼容性)。
- DEV-002 第五批在 Windows x64 / Python 3.12.10 验证了两个入口的离线 stdio、111 个工具的 schema、独立解包安装和 36 项专项回归。本版验收范围为 Python、离线传输和安装分发。Creo 实机建模、保存重载和 WorkBuddy 黑盒留待专项验证。 [工作卡](work-items/DEV-002.md) · [发布记录](validation/RELEASE-0.45.2.md)

## 附件

- `MCP_CREO_MechDog-0.45.2-source.zip`
- `MCP_CREO_MechDog-0.45.2-source.zip.sha256`
- `MCP_CREO_MechDog-0.45.2-seed-library.zip`
- `MCP_CREO_MechDog-0.45.2-seed-library.zip.sha256`

种子包 SHA256 为 `ae0c8928d9febbd001524bc821d709a499d4235452bac64bea365e1304c336fc`。两份同名 sidecar 分别记录各自 ZIP 的摘要。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.45.2)
