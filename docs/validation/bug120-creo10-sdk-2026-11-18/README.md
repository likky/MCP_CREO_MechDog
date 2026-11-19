# BUG-120 / T1：Creo 10 SDK 编译对照（2026-11-18）

## 这是什么

目标机运行 Creo 10，本仓库此前只在 Creo 12.4 的 SDK 上编译。这份证据回答一个问题：
**新写的 D2/D3 原生代码依赖的 Pro* 声明，在 Creo 10 的 TOOLKIT 头文件里是否存在、签名是否一致。**

## 怎么产生的

1. 从目标机拷来 Creo 10 的 `Common Files\protoolkit\includes` 到 `build\creo10_sdk\includes`（只拷头文件，未拷 DLL/库/License）。
2. 运行：

```
.\.venv\Scripts\python.exe tools\check_creo10_compile.py --sdk build\creo10_sdk --full
```

脚本在 `build\creo10_check\native` 沙箱副本里用该 SDK 重新生成 `constants.inc`，不触碰本机 `native/constants.inc`，随后编译四个单元。

## 结果（`report.json`）

- 头文件集合：415 个 `*.h`（本机 Creo 12.4 为 430；Creo 10 缺少 `Probbl.h`、`ProCmpst*.h` 等，与仓库既有记录一致）
- 20 个必需函数全部存在：`ProMacroLoad`、`ProCmdCmdIdFind`、`ProCmdBracketFuncAdd`、`ProFeatureGeomitemVisit`、`ProCurveInit`、`ProCurveTypeGet`、`ProCurveLengthEval`、`ProFeatureInit`、`ProSelection*`、`ProCmdActionAdd`、`ProToolkitDllIdGet` 等
- 6 个必需枚举全部存在：`PRO_SELECT_OVERRIDE`、`PRO_SELECT_TOGGLE`、`PRO_ENT_CMP_CRV`、`uiProeAsynch`、`PRO_VALUE_TYPE_WSTRING`、`PRO_TK_NO_ERROR`
- 编译单元（全部 exit 0）：
  - `api_probe.cpp` 2.1 s（取每个 API 地址，签名不符即报错）
  - `blend_sync.cpp` 5.0 s（ABI2 payload：D3 collector/Done/marker）
  - `blend_loader.cpp` 4.0 s（ABI1+ABI2 装载）
  - `worker.cpp` 21.7 s（生产编译单元，含 D2 引用解析与 D3 状态机）

## 这份证据不能说明什么

- 不能说明面板能打开、曲线能枚举、Done 能关闭对话框；
- 不能说明 `PRO_SELECT_TOGGLE` 在真实边界混合对话框中的效果；
- 不能说明 `AfterTerminal`/`OuterDrain` 的真实时序；
- 不构成实机验证：上述全部属于 D6，需要在目标机上运行 Creo 并有人操作界面。

按仓库规则，本文只支持这一句结论：**Creo 10 的 TOOLKIT 头文件以相同签名声明了这些 API，且新代码在该 SDK 下可编译。**
