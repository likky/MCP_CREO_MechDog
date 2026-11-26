# MCP_CREO_MechDog 0.44.1 版本说明

2026-11-25 PATCH，公开工具数 111。上一版本：0.44.0（`v0.44.0`，提交 `08c88a77d87dd58dc0552536bfc10999874c3f8d`）。

装配平面配合现在验证约束回读和元件实际位姿。面距误差超过 0.001 mm、法向角误差超过 0.01°，或缺少验证所需的证据，作业会明确失败并触发检查点恢复。Creo 10 上原本返回成功的冲突配合现已被拒绝，重载确认原位姿、FIX 和 revision 恢复。合法配合和欠约束组通过保存重载。[BUG-036](../work-items/BUG-036.md)

本机 Windows x64、Python 3.12.10、Creo 10.0.0.0（release 42）和匹配 SDK 完成 23 个专项作业及 T09 六类回放。外部 Creo 9 原案、Creo 12.4、WorkBuddy 黑盒及全项目原生回归未运行。[验收与发布记录](../validation/RELEASE-0.44.1.md)

升级后重启 MCP 连接器以加载新版服务和原生执行器。

## 附件

- `MCP_CREO_MechDog-0.44.1-source.zip`
- `MCP_CREO_MechDog-0.44.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.44.1-seed-library.zip`
- `MCP_CREO_MechDog-0.44.1-seed-library.zip.sha256`

种子包 SHA256 为 `491a80535bec356b99610e5805c9006cb5bf1633f150cd91c99b61768f6a1474`。两份同名 sidecar 分别记录对应 ZIP 的 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.44.1)
