# DEV-092：用户提供的 Creo SDK 头文件参考

2026-11-19 用户明确要求将下载目录中的 SDK 头文件放到项目，供另一 AI agent 处理本次装配反馈。该要求是 AGENTS 中一般 SDK 不入库规则的本次指定例外。

- 原始来源：`C:/Users/Administrator/Downloads/Creo13.4.0.0/includes.zip`。
- `includes.zip`：原包，1,192,827 字节；SHA256 `83bc7864d19c75ac721479ac5f6f0e998ad9e3dfe43158f511884033f18c9657`。
- `includes/`：433 个原始 `.h`，共 7,522,183 字节；与 ZIP 内容逐字节相同，未格式化或改行尾。
- [manifest.json](manifest.json)：归档校验值、逐头文件长度和 SHA256。
- “Creo 13.4.0.0”来自用户提供的目录名称，未独立认证版本；本次未据此编译执行器或验证运行期兼容。

这是独立参考资料，保留各文件原始 PTC 版权/许可声明，不适用项目 MIT 许可。该目录不进入项目公开源码打包白名单；Git archive 通过 `export-ignore` 排除。不要将它加入生产 include 路径，也不要据此替换本机实际配置的 SDK 或复制/生成 `native/constants.inc`。

可直接离线检索：

```powershell
rg -n -C 12 'ProAsmcompConstraintsSet|ProAsmcompConstraintsWithComppathGet' references/creo13.4.0.0-sdk/includes/ProAsmcomp.h
rg -n -C 12 'ProSolidOutlineCompute' references/creo13.4.0.0-sdk/includes/ProSolid.h
rg -n -C 12 'ProSurfaceAreaEval' references/creo13.4.0.0-sdk/includes/ProSurface.h
```

执行入口：[另一 AI agent 接手任务](../../docs/development/DEV-092-AGENT-HANDOFF.md)；主计划：[DEV-092 装配反馈处理计划](../../docs/superpowers/plans/2026-11-19-dev092-creo13-assembly.md)。
