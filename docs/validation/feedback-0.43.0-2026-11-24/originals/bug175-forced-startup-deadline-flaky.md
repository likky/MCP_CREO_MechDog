# 0.43.0 反馈：BUG-175 假时钟修复只覆盖第一段，第二段 `monotonic()+5.0` 真实时钟 deadline 仍随机失败

- 日期：2026-11-24
- 验证对象：`wudahua/MCP_CREO_MechDog` v0.43.0（Release id `456439582`，node_id `RE_kwDOU_ueTM4bNLce`，published `2026-11-24T07:41:46Z`；0.41.0→0.43.0 含两个中间版，逐版核对）
- 本地环境：Windows / Creo 10.0.0.0 ProToolkit SDK / WorkBuddy MCP 客户端 / Python `.venv`
- 验证性质：定版与发布链交叉核对、四附件四方校验、差异链、覆盖升级与零补丁编译、注册指纹、静态台账、门禁对照实验、篡改实验、fourref、**官方干净源码树多轮采样与因果探针**
- 实机边界：本轮**未**连接 Toolkit、**未**启动或关闭 Creo、**未**做故障注入；文中结论不代表 Creo 10 运行期验证。所有失败均来自离线单测，可在官方干净包复现。

## 1. 结论摘要

0.43.0 的发布数据、编译、门禁、注册、跨文档台账全部通过，0.41.0~0.43.0 交付的 BUG-175~185 与本轮核对一致；**上一轮反馈的 BUG-170 flaky 已被作者收到并部分修复**（BUG-175 工作卡明确引用 0.39.0 原始反馈，第一段固定 `+0.3` deadline 已改为可控假时钟，作者环境 50/50 通过）。但**同一问题族的第二段未被覆盖**，需要继续处理：

| 编号 | 问题 | 证据 | 判定 |
| --- | --- | --- | --- |
| P1（问题族未闭环） | `Bug170StaleSessionAndForceNewTests.test_drive_stale_session_without_and_with_force_new_session` 的**第二段（force_new_session，coord2）**仍用真实时钟 `creo_startup.time.monotonic() + 5.0`，官方干净包随机失败在 `assertEqual(st2["state"], "ready")` | 0.43.0 干净树 30 次采样 1 败；两轮因果探针 original 59/60 与 58/60（合计 150 次 4 败，约 2.7%），中和第二段时钟后 **120/120 全过** | **同族残留，未闭环** |

数据层正项与测试稳定性问题需区分：作者修复方向正确、第一段已真正闭环；残留仅在第二个 `_drive` 调用，属于假时钟注入范围不全，不是产品运行期功能缺陷。

## 2. 先说清楚：作者已收到并修复了上一轮反馈（避免被误读为"拒不修复"）

- 0.41.0 的交付 ID **BUG-175** 标题即「修复 BUG-170 单测固定 0.3 秒墙钟 deadline 导致的随机失败」，工作卡来源链接明确指向 `feedback-0.39.0-2026-11-23/originals/bug170-unit-test-fixed-deadline-flaky.md`。
- 0.41.0/0.42.0/0.43.0 的 source.zip 均归档了 0.39.0 原始反馈（`docs/validation/feedback-0.39.0-2026-11-23/`），0.42.0 起还归档了 0.40.0 反馈与 bspline-view 反馈。
- 修复确实生效：测试文件在 0.41.0 改变（`changed_at_041=true`），`monotonic() + 0.3` 已从第一段移除；0.42.0、0.43.0 保持该修复（`stable_041_to_043=true`）。
- 因此本条**不是**重复报同一个错误值，而是同一测试里**第二处未被修复**的真实时钟 deadline；请按"假时钟注入未覆盖全部 `_drive` 调用"处理。

## 3. 数据层正项（便于区分「测试稳定性」与「产品功能」）

### 3.1 定版与四附件

- 重新定版确认 v0.43.0 为最新；0.40.0→0.43.0 存在两个中间正式版 0.41.0（id `456259150`）、0.42.0（id `456324195`），逐版下载校验，未跳版。
- 三版每版四附件（source.zip / 两个 `.sha256` / seed-library.zip）本地实算 SHA256、sidecar、GitHub asset `digest`、Release body 四方一致（`FOUR_WAY_OK=true`，`body_hash_mismatch=[]`）；sidecar 均 ASCII+LF。
- 0.43.0 source.zip SHA256 `d4f0e993a87c596550cef22cfd7ec5783c5f2432107455407282c9a39cc1e2f4`；seed-library.zip SHA256 `b8b8408f614088ce1c3c67a12ea55fefe5dfe4fe19c2297e2024e2e3f0ebcc2f`，与 `docs/seed_package.json` 一致。
- 发布链：annotated tag `6df0d95e…` → release commit `fc64e3bc…`（30 文件，发布前 109s）→ backfill `7a6af457…`（发布后 108s）= main；三版 `previous_release_commit` 均指向上一版真实发布提交（非回填），0.43.0 的 `previous_release_commit=be2d6346…` 正是 0.42.0 发布提交。

### 3.2 编译、包一致性、注册

- 官方原包零补丁编译：`BUILD_EXIT=0`，`error C` / `error LNK` / C1083 / C2065 / C3861 / C2039 / `fatal error` / `Traceback` 全 0，C4819=0。
- worker `11,784,192 B / b25cff1a76a7272eaf6a8fd07418fbff1c4abc7bcf9f52eb03cec4d48a721950`。
- 包一致性 `2400/2400`，`real_diff=[]`，`eol_only=[]`，`missing=[]`；注册指纹 10/10 一致。

### 3.3 静态台账与门禁

- 工具数 111（`@mcp.tool` − `remove_tool`，与 `creo_capabilities.tool_count` 一致）；BACKLOG 计数 `exit 0`；版本入口与 seed 清单一致；release body 自证通过。
- 交付 ID：0.41.0 `BUG-175/176/177/178`+`FEAT-078/079`、0.42.0 `BUG-179/180/181/182`+`FEAT-080/081`、0.43.0 `BUG-183/184/185`+`FEAT-082/083`，与冻结快照、逐 ID 表、BACKLOG、工作卡一致，逐 ID 交付版本/Release 号正确。
- 门禁：assets+body `exit 0`；本机 records 无 unit evidence `exit 1` 是 BUG-144 正确行为；21 类记录门禁负例全部捕获（G3 snapshot 删除 0 为设计可选）；source-zip 6 类篡改全部 `exit 1`、correct/untouched `exit 0`；反向资产闸门 1/1/0；fourref 四处引用一致（tag/release_commit 为打包时点预写措辞，backfill/main 含数字 Release id 与资产门禁 `exit 0`）。
- 干净官方树 `test_release_integrity` 55 tests OK、宿主保护 30 tests OK；本机核心单测子集 224 tests OK。

## 4. P1 详细证据：第二段真实时钟 deadline 残留 flaky

### 4.1 修复只覆盖第一段

0.43.0 干净树 `tests/unit/test_feedback0360_fixes.py` 中该用例有两段 `_drive`：

```python
# 第一段 coord1（BUG-175 已修）：用可控假时钟
fake_now = [100.0]
def fake_monotonic(): return fake_now[0]
def probe_then_expire(*_args, **_kwargs):
    fake_now[0] += 1.0; return bad_probe
def wait_then_expire(timeout=None):
    fake_now[0] += max(0.5, float(timeout or 0.5)); return False
with (
    patch.object(creo_startup.time, "monotonic", side_effect=fake_monotonic),  # 假时钟
    patch.object(coord1._stop, "wait", side_effect=wait_then_expire),
    ...
):
    coord1._drive(settings, True, fake_now[0] + 0.3)

# 第二段 coord2（未修）：仍是真实墙钟 deadline
with (
    patch.object(creo_startup, "inventory", return_value=alive_inv),
    ...
    patch.object(creo_startup, "launch_creo", return_value=...) as launcher,
):                                             # 注意：此处没有 patch time.monotonic
    coord2._drive(
        settings, True, creo_startup.time.monotonic() + 5.0, force_new_session=True
    )                                          # ← 真实时钟 +5.0
```

逐版核对 `monotonic() + N` 字面量：

```text
0.39.0 / 0.40.0 : ['monotonic() + 0.3', 'monotonic() + 5.0']   (两处都是真实时钟)
0.41.0 / 0.42.0 / 0.43.0 : ['monotonic() + 5.0']              (只移除了第一处 +0.3)
```

BUG-175 把第一处 `+0.3` 换成假时钟后，第二处 `+5.0` 原样保留至 0.43.0。

### 4.2 官方干净树多轮采样仍失败

在官方 0.43.0 干净源码树（`_creo_update_tmp/0.43.0/clean_pkg_v13/MCP_CREO_MechDog/`，无本机诊断脚本污染）采样该用例：

```text
flaky probe（30 次）          : 29 pass / 1 fail
因果探针第 1 轮 original（60 次）: 59 pass / 1 fail
因果探针第 2 轮 original（60 次）: 58 pass / 2 fail
合计                          : 146 pass / 4 fail（约 2.7% 失败率）
失败断言（一致）:
  File ".../tests/unit/test_feedback0360_fixes.py", line 166, in test_drive_stale_session...
    self.assertEqual(st2["state"], "ready")
  AssertionError: 'timeout' != 'ready'
失败序列（第二节拍）:
  checking->waiting_for_channel->building_worker->connecting->waiting_for_connection->timeout
```

失败点正是第二段 coord2 的 `st2["state"]`，与真实时钟 deadline 所在段一致；第一段 coord1 的断言（`st1`）在全部采样中均通过。

### 4.3 因果探针确认机制

在干净树中额外把第二段 `_drive` 的真实时钟也中和（全局 `patch.object(creo_startup.time, "monotonic", side_effect=缓慢推进的假时钟)`），两轮各 60 次：

```text
第 1 轮: original 59/60 fail=1  |  neutralize_second_clock 60/60 fail=0
第 2 轮: original 58/60 fail=2  |  neutralize_second_clock 60/60 fail=0
合计:   original 117/120 fail=3 |  neutralize 120/120 fail=0
```

中和第二段真实时钟后失败完全消失，证明残留 flaky 的根因是第二段仍在用墙钟 deadline：当 preparation / 连接模拟的 I/O 稍慢，`monotonic()+5.0` 预算在第一次成功连接前耗尽，`st2["state"]` 停在 `timeout`。这与第一段已修复的机制完全同类。

## 5. 建议

- 将 BUG-175 的假时钟注入扩展到同一用例的第二段 coord2：对第二段 `_drive` 同样 mock `creo_startup.time.monotonic`（必要时连同 `_stop.wait` 一起推进），或复用一个贯穿两段的统一假时钟夹具，避免逐段遗漏。
- 验收时请在外部解压的官方源码包上连续采样（建议 ≥60 次，两段合计 0 失败），而不仅依赖作者环境的 50/50；BUG-175 工作卡当前"未验范围"一栏写明"外部 Creo 10 报告方解压官方源码包复测"，本反馈即该复测结果。
- 可在门禁/单测里加一条静态断言：该用例中不得出现 `monotonic() + <常数>` 形式的真实时钟 deadline，防止后续再遗漏。

---

附：本轮所有验证均为安装、编译、文件、静态与离线单测层面；未做 Toolkit/Creo 实机连接或故障注入。正项与问题项分别列出，便于按问题族判断修复范围。
