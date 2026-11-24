# MCP_CREO_MechDog 0.43.2 版本说明

2026-11-24 发布范围为 PATCH，公开工具数 111。BUG-175 让普通启动与显式强制启动的单测共用可控时钟和模拟等待。测试分别确认陈旧会话诊断和强制启动一次后就绪，并隔离 Toolkit 锁和运行目录。[BUG-175](work-items/BUG-175.md)

上一版本：0.43.1（`v0.43.1`，提交 `f8a07c0513a0abbf7b1e30ca454cb9a1ed4215a0`）。

在 v0.43.0 解包副本中，把首次模拟探测延迟 1.1 秒即可复现强制启动场景的误超时。补修的解包验证连续通过 120 次，注入相同延迟后通过 3 次。[反馈原件及其摘要](validation/feedback-0.43.0-2026-11-24/SOURCE_MANIFEST.json)

本补丁涉及离线测试夹具与发布元数据。Creo 9/10/12 原生安装、连接、建模和几何重载，以及报告方的外部环境复测均未执行。[验收与发布记录](validation/RELEASE-0.43.2.md)

## 附件

- `MCP_CREO_MechDog-0.43.2-source.zip`
- `MCP_CREO_MechDog-0.43.2-source.zip.sha256`
- `MCP_CREO_MechDog-0.43.2-seed-library.zip`
- `MCP_CREO_MechDog-0.43.2-seed-library.zip.sha256`

种子包 SHA256 为 `fece0e88c0c55828f9776944ad2196215e43077fcd1b3c7e62103e9d16891c52`。源码包摘要记录在同名 sidecar 中。两份同名 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.43.2)
