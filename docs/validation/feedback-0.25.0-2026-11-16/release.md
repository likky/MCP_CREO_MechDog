# MCP_CREO_MechDog 0.25.0 升级验证与问题反馈

- 目标仓库：<https://github.com/wudahua/MCP_CREO_MechDog>
- 升级链：`0.24.1` → `0.25.0`（MINOR）
- 本机环境：Windows x64 / Creo Parametric 10.0.0.0 + `protoolkit` / MSVC 2022 BuildTools 14.44.35207 / Windows SDK 10.0.26100.0 / Python `.venv`
- 验证日期：2026-11-15
- 反馈文档定位：`日期 + CREO10.0.0.0 + 最新版本号 + 核心问题`

---

## 0. 结论先行

**升级本身成功且质量正面**：官方原包在 Creo 10 SDK 上**零补丁编译通过（连续第八版）**，四附件 SHA256 **四方一致 `ALL_OK=true`**（0.24.1 的正文摘要缺口在本版闭环），包一致性 `1876/1876 / real_diff=[]`，回调注册核心四项 `SAME`，四项官方门禁全部 `exit 0`，干净单测子集 41 模块 `Ran 576 tests OK`。

**但交付链仍有 3 项新问题 + 2 项历史未闭环**。最重的一条是：发布记录门禁**连续第四版不校验「逐 ID 表是否列全本版交付 ID」**，本版还新增两类列级盲区（「交付版本」「实际 Release」两列完全不校验），并有篡改 `--source-zip` 的硬证据。

| 编号 | 等级 | 一句话 | 状态 |
| --- | --- | --- | --- |
| P1-1 | 高 | 把逐 ID 表唯一交付行换成合法非交付 ID 仍判 `current`；`交付版本`/`实际 Release` 列任意改不报；连续第四版 | **未闭环且加剧** |
| P2-4 | 中 | 发布记录/版本说明/Release 正文把「上一正式包」写成 `0.24.0`，实际直接前版是 `0.24.1`，同文档又写明从 `0.24.1` 合入 | 本版新增 |
| P3-5 | 低/观察 | 包内发布记录预写「发布后核对 `→ exit 0`」，tag 处 POSTCHECK 尚无该结果；门禁词表不覆盖此类准备态措辞 | 本版新增 |
| P2-1 | 中 | `tools/package.py` 的 docs 白名单仍为 `.md/.json`，`.txt` 校验清单不随包 | 历史未闭环（逐字节相同） |
| P3-3 | 低 | `RELEASE-0.24.0.md` 仍写「单测 3494 → 3548 全量通过」，掩盖 3567 通过 / 3 失败 | 历史未闭环 |

**已闭环（正面，请作者知悉）**：P3-4（0.24.1 发布记录错误的 POSTCHECK 引用已消失）、P2-3 当前版（0.25.0 正文列出四附件字节数与 SHA256，包内只写「见同名 sidecar」）、四附件四方校验、0.24.1 反馈归档（`docs/validation/feedback-0.24.1-2026-11-15/`）。

> **实机验证边界**：本次「更新」请求未含当次实机确认，按仓库 `AGENTS.md`（2026-11-09）「按次生效」规则，本轮**未建立 Toolkit 连接、未启动/关闭 Creo、未做故障注入**。所有新增能力（钣金组合首壁、几何选择器、`plan_file`、`linear_pattern`、角度倒角、装配约束）只到**安装 / 编译 / 文件 / 静态验证层**，"编译进 worker" 不等于 "运行期可用"。作者的实机证据来自 Creo 12.4.0.0，发布记录第 29 行亦明确 **Creo 9/10 实机与 WorkBuddy 黑盒未测**。

---

## 1. 定版与版本链（远端原始 JSON）

不依赖网页抓取缓存，全部取 GitHub API 原始 JSON 交叉确认：

| 端点 | 结果 |
| --- | --- |
| `/releases/latest` | `v0.25.0`，id `446058283`，`published_at=2026-11-15T12:51:01Z`，`created_at=12:50:11Z` |
| `/releases?per_page=10` | `v0.25.0, v0.24.1, v0.24.0, ...` → **直接后继，无中间正式版** |
| `/git/ref/tags/v0.25.0` | 附注标签对象 `f617e5d26d326a0b51d52f298141e965a63d2041`，tagger `12:50:11Z` |
| 标签指向提交 | `38bee48692d67d7f962d21ad713abbaa821c2fa7`，`12:49:53Z`，`Merge remote-tracking branch 'origin/main' into main`，31 files |
| `/commits/main` | `581977e142cd1341196349f704a1e0ee748b7f4c`，`12:51:38Z`，`DEV-090: record the 0.25.0 release and post-check`，2 files |

回填提交晚于发布 **约 37 秒**，且只改 2 个文档文件。按作者自 0.23.1 起的冻结设计，实际 Release id 与四附件摘要只存在于 `main`，包内快照不回写 —— 本轮按设计核对，不作为缺陷（见 §6 观察项）。

## 2. 四附件 SHA256 四方校验

| 附件 | 字节 | 本地实算 = sidecar = API digest = Release 正文 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.25.0-source.zip` | 10,238,309 | `a1e949a302d1a0003dd9f98c0a44ec9e7096cda740fced526b09dec26f126d40` |
| `MCP_CREO_MechDog-0.25.0-source.zip.sha256` | 101 | `68486baf77050e947b00651003982926b47b193a1e5033fc35c1e449ee584174` |
| `MCP_CREO_MechDog-0.25.0-seed-library.zip` | 493,442 | `f8cf62d21d8c9d513fe6335e8e82b8064f48be642ad6a009cd433aa3257705fc` |
| `MCP_CREO_MechDog-0.25.0-seed-library.zip.sha256` | 107 | `a89288276cf7182dda630998da03130f544dfb2ddc5d7e4145b45f547d83864b` |

- `THREE_WAY_ALL_OK=true`、**`ALL_OK=true`**；`body_64hex` 恰好 4 个；四个附件名、字节数、摘要值在正文中逐项列出。
- 两个 sidecar 均 **ASCII + 仅 LF**（`b"\r\n" not in raw`、`all(b < 128 ...)`），文件名与 `<64hex>  文件名` 格式正确。
- **对比 0.24.1**：彼时 `ALL_OK=false`（正文 `body_64hex=[]`，而包内三处仍称「与 Release 正文」）→ 本版**已在当前版闭环**；但 0.24.1 的历史文档措辞仍未回填（按作者「历史快照字节不变」策略，列为观察项而非重复报缺陷）。

## 3. 升级、编译与正向验证

### 3.1 差异与覆盖

- 归一化（CRLF→LF）后：`1853 → 1876` 文件，`added=23 / removed=0 / REAL=30 / EOL-only=66`。
- native 真实改动：`native/advanced.cpp`、`native/generic.cpp`、`native/sketch_coordinates.cpp`；新增 `native/base_flange.cpp`、`native/geometry_selectors.cpp`、`native/linear_pattern.cpp`。
- rollback 快照 `rollback-0.24.1-source.zip`（17,888,222 B / `ca2feb13a89b220b`）；overlay 写入 1876 文件 / 135 目录，`version.py` → `0.25.0`。
- 本机 `config.json` 的 `vcvars64_env` 三键 `INCLUDE/LIB/PATH` 与 `client-config.json` 均保留。

### 3.2 官方原包零补丁编译（Creo 10 SDK）

```
pip install --no-deps -e .   → Successfully installed MCP_CREO_MechDog-0.25.0
bridge.py build              → BUILD_EXIT=0
build.log 诊断：error C=0 / LNK=0 / C1083=0 / C2065=0 / C3861=0 / C2039=0
                fatal error=0 / Traceback=0 / C4819=20（既有编码告警）
worker：11,008,512 B / 2aea00039cd1e280f128bb1cff437f20c122a18b935ea54475feb9c6c25194be
source.sha256：348a9bff7e2b45f7b173d3b1067fc935bac39baa5039ec897e6b1881a6d02246
package parity：1876/1876，real_diff=[]，eol_only=[]，missing=[]
registration core all same: True（protk.dat sha fc62f1548f4a1895…，loader=2 / payload=7，sha256-repo-lf-v1）
```

零补丁结论成立的三要素齐备：`BUILD_EXIT=0` + 无本地补丁 + `real_diff=[]` + build stdout 无 Traceback。worker 体积相对 0.24.1（`10,902,528 B / 55153cab…`）增长 105,984 B，与新增三个 native 文件一致 —— **但这只是编译层证据，未做运行期验证**。

### 3.3 四项官方门禁 + 反向闸门

| 门禁 | 结果 |
| --- | --- |
| `check_release_records.py --version 0.25.0` | `0.25.0: POSTCHECK, release record and per-ID states are current` / `exit 0` |
| `check_release_records.py --version 0.25.0 --source-zip <official>` | 同上 / `exit 0` |
| `check_release_assets.py --tag v0.25.0 --version 0.25.0 --dir assets` | `local_verified: four assets present; both sidecars match` / `exit 0` |
| `check_release_assets.py --tag v0.25.0 --version 0.25.0`（远端下载） | `v0.25.0: four assets downloaded and verified; both sidecars match` / `exit 0` |

反向对照（证明闸门确实在工作，而非恒真）：篡改种子包 1 字节 → `exit 1`（sidecar 不匹配）；删除两个 sidecar → `exit 1`（缺件）；原件目录 → `exit 0`。

### 3.4 静态与单测

- 公开工具：`@mcp.tool` 109 − `mcp.remove_tool` 1 = **108**（与版本说明一致）。
- `docs/BACKLOG.md` 计数 `186`（BUG 83 / FEAT 64 / DEV 39），`consistent=true`。
- `docs/seed_manifest.json`、`seed_library/seed_manifest.json`、`docs/seed_package.json` 均为 `0.25.0`，种子摘要与本地实算一致。
- **关键单测子集 41 模块 `Ran 576 tests in 31.644s OK`**（含 0.25.0 新增的 6 个测试模块）。
- `tests.unit.test_release_integrity` 全模块：干净官方源码树（1876 文件）**`Ran 28 tests OK`**；本机工作树 `Ran 28 tests / FAILED (failures=1)`。唯一差异是本机根级额外脚本 `write_runbuild.py`（339 B，2026-10-31 临时辅助文件，不在官方包内）触发 `test_source_package_ships_every_root_module` 的 `ROOT.glob("*.py")`。**属本机环境敏感，非产品缺陷**，与 0.24.1 结论相同。
- **本机全量单测未跑**：宿主 `sitecustomize.py` 的 `SAFE_DELETE_BULK_GUARD_ERROR` 会挂全量套件，按既定规则不宣称「全量通过」。发布记录第 26 行的 `Ran 3655 tests OK` 是作者在自身环境的 `dev_check.py` 结果，本轮未复现、也未否认。

---

## 4. P1-1（高，连续第四版）逐 ID 门禁不校验交付 ID 完备性，且新增列级盲区

### 4.1 根因

`src/creo_mechdog/release_integrity.py` 与 0.24.1 **逐字节相同（38792 → 38792 B）**。核心逻辑：

```python
def _id_table(text: str):
    for index, line in enumerate(lines):
        if line.strip().startswith("## 逐 ID"):   # 只认「逐 ID」段
            start = index + 1
            break
...
for work_id, cells in rows:                       # 只遍历「表内」出现的 ID
    ...
for work_id, cells in _backlog_rows(backlog):     # 全扫 BACKLOG
    if work_id in checked: continue
    if backlog_class not in ("partial", "delivered"): continue
```

门禁只回答「表内每行是否自洽」「表是否为空」，**不回答「本版交付的 ID 是否都在表里」**。0.24.1 曾有「归档项交付核对」表绕开 `_id_table()`；0.25.0 改回单表、单交付 ID，但完备性检查依然缺席。

### 4.2 对照实验（`validate_release_records("0.25.0", None, gate_root)`）

| 实验 | 注入 | problems |
| --- | --- | ---: |
| A | 基线（原样发布树） | 0 |
| B | 删掉逐 ID 表**唯一**一行 → 表变空 | **1**（仅「表空」才报） |
| **C** | 把 `[DEV-090]` 交付行**替换为合法的非交付 ID `[BUG-005]`**，并让 `BUG-005.md` 前 12 行提到 `0.25.0` | **0** |
| D | 交付版本列 `0.25.0` → `0.24.1` | **0** |
| E | BACKLOG 中 DEV-090 状态 → `开发中` | 4（其余防御仍有效） |
| F | 不在表内的活动行（BUG-014）→ `开发中` | **0**（P3-4 连续第四版） |
| G | 主台账列文本注入 | 0（见下方「纠错」） |
| H1/H2 | 断链 / 逃根链接 | 1 / 1 |
| I/J/K/L/M | 占位词、种子摘要损坏、删光 sidecar 措辞、版本回退、删交付工作卡 | 1 / 1 / 1 / 1 / 8 |

**实验 G 的纠错（避免误判）**：初版脚本用 `.replace("| 部分交付，剩余待验收 |", ...)` 命中的是「卡首页」列而非「主台账」列，且 `_status_class("已完成")` 属 `other` 会被 `line 752` 跳过 —— `G=0` **不是**「差异说明豁免」造成的。用 `ri._split_row()` 按 header 精确定位后重做（`gate_probe3.py`）：

| 精确列实验 | 结果 | 说明 |
| --- | ---: | --- |
| `主台账` → `已完成` | **1** | 该列确实受检 |
| `技术状态` → `未排期` | **1** | 该列确实受检 |
| `卡首页` → `已完成` | 0 | `_status_class` 归 `other` 被跳过（设计降级） |
| **`交付版本` → `0.19.0`** | **0** | **该列完全不校验** |
| **`实际 Release` → `v0.19.0`** | **0** | **该列完全不校验** |
| `差异说明` 改为非空 + `主台账` → `已完成` | **0** | `and not explained` 豁免关闭了主台账/状态类检查（`line 754/759`） |

### 4.3 篡改 `--source-zip` 的硬证据

把 C 的改动打进源码包，喂给**官方** `check_release_records.py --source-zip`：

```
=== swap_delivered_id_for_nondelivered === exit 0
0.25.0: POSTCHECK, release record and per-ID states are current

=== drop_only_per_id_row === exit 1
... RELEASE-0.25.0.md has no '逐 ID 状态核对' table rows

=== corrected_previous_version_label === exit 0   （把「上一版本：0.24.0」改成 0.24.1 也不影响）
=== untouched_copy === exit 0
```

即：**只要逐 ID 表非空、表内每行自洽，交付 ID 被整个替换、交付版本被改错、上一版标签被改对，官方门禁一律判 `current`**。

### 4.4 影响与建议

1. 交付清单可被整行掉包而发布门禁无感；第三方无法仅凭 `exit 0` 判断「本版交付项是否列全」。
2. `交付版本` / `实际 Release` 两列是**人工填写且无机器校验**的字段，容易与 tag 脱节。
3. `explained` 豁免（差异说明非空即跳过主台账/状态类比对）使「写一段剩余范围说明」即可关闭大半一致性检查。

建议（按成本排序）：
- 在 `validate_release_records()` 增加 `expected_ids`：从 BACKLOG 中「交付版本 = 当前版」或本版工作卡集合推导，要求逐 ID 表**ID 集合与之相等**（不只是非空）。
- 校验 `交付版本` 列含当前版本号、`实际 Release` 列等于 `v<version>`。
- 把 `explained` 豁免收窄为「仅豁免 `_status_class` 差异」，主台账逐字状态仍必须比对；或要求差异说明列显式声明豁免理由并被机器识别。
- 继续覆盖「不在表内的活动行」（P3-4）。

---

## 5. P2-4（中）「上一正式包」标签错写 `0.24.0`，跨三份文档自相矛盾

| 位置 | 原文 |
| --- | --- |
| `docs/validation/RELEASE-0.25.0.md:10` | `## 包内容对照（相对 0.24.0）` |
| `docs/validation/RELEASE-0.25.0.md:59` | `## 相对上一正式包核对（上一版本：0.24.0）` |
| `docs/validation/RELEASE-0.25.0.md:67` | `\| worker SHA256 \| 0.24.0 构建 \| 本版新增/修改原生源码 \| ...` |
| `docs/RELEASE_NOTES_0.25.0.md:6` / Release 正文 | `- 公开工具：**108 个**（0.24.0 为 107）` |
| **同文件 `:27` / 正文** | `- 合并基线：本版从已发布的 0.24.1（e1ee731）合入…` / `本版从已发布的 0.24.1 合入` |
| **远端事实** | `/releases?per_page=10`：`v0.25.0` 直接前版 `v0.24.1`；0.24.1 的 id `444282824`，published `2026-11-13T13:47:10Z` |

**影响**：对照表以 0.24.0 为基线实际上跨了两版，0.24.1 的 BUG-125—128（启动参数、无图形容错、worker 回退、`toolkit_hint`）与 `native/worker.cpp` 变更被排除在「包内容对照」外；「worker SHA256：0.24.0 构建」也与实际不符（0.24.1 已重编为 `10,902,528 B / 55153cab…`）。跨版升级者据此判断「是否需重编译 / 是否需重新注册」时会拿到错误基线。

tamper 实验 `corrected_previous_version_label`（把标题改成 `上一版本：0.24.1`）喂官方 `--source-zip` 仍 `exit 0`，说明门禁不校验该标签。建议：从版本历史推导 `previous_version` 并做机器比对；对照表基线统一改为 0.24.1，或显式标注「与 0.24.0 的功能对照（跨 0.24.1）」以免误读。

---

## 6. P3-5（低 / 观察）包内发布记录预写「发布后核对 exit 0」

`docs/validation/RELEASE-0.25.0.md:57`（tag / 发布提交处快照）：

> `- 发布后核对：tools/check_release_assets.py --tag v0.25.0 → exit 0，「four assets downloaded and verified; both sidecars match」；实际 Release id、发布时间与四个附件摘要回填到 main 上的 POSTCHECK，不回写已冻结的包内快照。`

四处 ref 实测（`fourref.py`，逐 ref 取 raw 文件）：

| ref | POSTCHECK `## v0.25.0` | 发布记录 `RELEASE-0.25.0.md` | Release id | 64hex 数 | 占位措辞 |
| --- | --- | --- | --- | ---: | --- |
| `tag` / `release_commit` | 38,579 B，无 `exit 0` 字样 | 6,349 B | 无 | 1 | `只存在于 main` / `回填到 main` |
| `backfill` / `main` | 39,562 B，含 `exit 0` | 7,171 B，无占位词 | 有 | 5 | `只存在于 main`（POSTCHECK 说明句） |

tag 指向的提交在 `12:49:53Z`，Release 到 `12:51:01Z` 才发布，回填在 `12:51:38Z` —— **打包时点不可能已跑通 `--tag` 核对**，但包内已把它写成 `→ exit 0`。本轮实测该命令确实 `exit 0`，所以结论与事实一致，属于「先写预期、后验证」的流程描述，而非虚假结论；按作者 0.23.1 起的冻结规则也属设计。

但从第三方视角：包内快照无法区分「预期」与「已核验」，而门禁 `_PLACEHOLDERS = ("待回填", "待发布后回填", "发布后在此段回填", "PENDING", "准备态")` 不覆盖 `→ exit 0` / `回填到 main` 这类变体。历史上「占位措辞换形式」已重现五次（0.21.0 → 0.23.0），本版是新形式。建议：把该行改成明确的将来时或加机器可读标记（如 `status: pending_verification`），或把 `_PLACEHOLDERS` 扩展为「发布后核对 … → exit 0 出现在包内快照即报」。

---

## 7. 上轮问题逐项闭环核对

| 上轮问题 | 本版核对 | 判定 |
| --- | --- | --- |
| P1-1 交付 ID 完备性 | `release_integrity.py` 逐字节未改；C/probe3/tamper 全部复现 | **未闭环且加剧（第四版）** |
| P2-1 `.txt` 白名单 | `tools/package.py` 逐字节相同（6925 → 6925 B），`"docs": {".md", ".json"}` 未变 | **未闭环** |
| P2-3 Release 正文摘要指引落空 | 0.25.0 正文四摘要齐全、包内只写「见同名 sidecar」 | **当前版已闭环**；0.24.1 历史文档仍写「与 Release 正文」（历史快照，按作者策略不回写） |
| P3-2 对照表单测数字掩盖失败 | 本版改为 `Ran 3655 tests OK`（作者环境）；本机全量未跑 | 数字族已换，不作为新缺陷，仅记录未复现 |
| P3-3 `3494 → 3548` | `RELEASE-0.24.0.md` 该行原样保留 | **未闭环** |
| P3-4 0.24.1 发布记录第 63 行 POSTCHECK 引用指错 | 全文扫描该措辞 `[]` | **已闭环** |
| 四附件四方校验 | `ALL_OK=true` | **已闭环** |
| 反馈归档 | 作者新增 `docs/validation/feedback-0.24.1-2026-11-15/{manifest.json,report.md}`（23,438 B / `631069bc…`） | **正面信号** |

---

## 8. 观察项（不列为缺陷，仅供作者判断）

1. `feedback-0.24.1-2026-11-15/manifest.json` 的 `"work_item": "DEV-089"`，而 0.25.0 主卡因编号冲突改为 `DEV-090`；历史归档元数据保持原标签，可能是有意保留。
2. 作者实机为 **Creo 12.4.0.0**（`release_numeric=44`），发布记录明确 **Creo 9/10 实机、WorkBuddy 黑盒、T6c/T7、`parallel`/`distance`、多约束求解与装配保存重载未测**；组合首壁与 SolidWorks `SMBaseFlange` 参照件差约 22 mm³，本版明确「不声称等价」。
3. 本轮未做实机验证（见 §0 边界）；新增三个 native 文件已编译进 worker，但**编译层结论不得外推为运行期可用**。
4. POSTCHECK / 发布记录 / BACKLOG 在 `backfill` 与 `main` 一致，tag 与发布提交处为打包时点快照 —— 符合冻结规则，回填晚于发布 37 秒。
5. 本机 `write_runbuild.py` 导致的单测 failure 是本机环境敏感，干净官方树全绿。

---

## 9. 复现命令（本机 `.venv`）

```bash
# 定版
curl -sS https://api.github.com/repos/wudahua/MCP_CREO_MechDog/releases/latest
curl -sS "https://api.github.com/repos/wudahua/MCP_CREO_MechDog/releases?per_page=10"
curl -sS https://api.github.com/repos/wudahua/MCP_CREO_MechDog/git/ref/tags/v0.25.0
curl -sS https://api.github.com/repos/wudahua/MCP_CREO_MechDog/commits/main

# 四项门禁
.venv/Scripts/python.exe tools/check_release_records.py --version 0.25.0
.venv/Scripts/python.exe tools/check_release_records.py --version 0.25.0 --source-zip <official source.zip>
.venv/Scripts/python.exe tools/check_release_assets.py --tag v0.25.0 --version 0.25.0 --dir <assets>
.venv/Scripts/python.exe tools/check_release_assets.py --tag v0.25.0 --version 0.25.0

# 门禁完备性实验与篡改包
.venv/Scripts/python.exe _creo_update_tmp/0.25.0/gate_experiments.py
.venv/Scripts/python.exe _creo_update_tmp/0.25.0/gate_probe3.py
.venv/Scripts/python.exe _creo_update_tmp/0.25.0/tamper.py

# 单测
.venv/Scripts/python.exe _creo_update_tmp/0.25.0/unit_subset.py
.venv/Scripts/python.exe _creo_update_tmp/0.25.0/clean_pkg_test.py
```

## 10. 证据清单（归档于 `_local/update-0.25.0/`）

四附件原件、`rollback-0.24.1-source.zip`、`release.json` / `release_body.md`、`download_report.json`、`diff_report.json`、`install_build.log`、`verify_build.json`、`gates_full.log` / `gates_tag.log`、`gate_experiments_result.json` / `gate_probe2_result.json` / `gate_probe3_result.json`、`tamper_result.json` / 三份篡改 ZIP、`static_verify.log` / `verify_report.json`、`fourref/` + `fourref_summary.json`、`feedback_0241/`、`unit_subset_raw.log`、`clean_pkg_test.log` / `clean_pkg_result.json`、`negative_gate_result.json`、`release_meta.json`。

---

**给作者的一句话**：0.25.0 的能力交付与编译质量都很扎实，四附件四方校验也补齐了；剩下的仍集中在「发布后台账自证一致性」——建议优先给逐 ID 门禁加一个 `expected_ids` 集合比对，并校验 `交付版本`/`实际 Release` 两列，同时把跨文档的 `previous_version` 统一到实际的 0.24.1。
