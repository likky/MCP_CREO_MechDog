"""DEV-083: the release-record gate refuses stale or placeholder documents."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from creo_mechdog.release_integrity import release_delivery_ids, validate_release_records

VERSION = "0.23.1"
DIGEST = "a" * 64
POSTCHECK = "docs/development/RELEASE-POSTCHECK-2026-11-07.md"
RECORD = f"docs/validation/RELEASE-{VERSION}.md"
NOTES = f"docs/RELEASE_NOTES_{VERSION}.md"
RELEASE_URL = f"https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v{VERSION}"
ASSETS = [
    f"MCP_CREO_MechDog-{VERSION}-source.zip",
    f"MCP_CREO_MechDog-{VERSION}-source.zip.sha256",
    f"MCP_CREO_MechDog-{VERSION}-seed-library.zip",
    f"MCP_CREO_MechDog-{VERSION}-seed-library.zip.sha256",
]


def _asset_table() -> str:
    rows = "\n".join(f"| `{name}` | `{'b' * 64}` |" for name in ASSETS)
    return f"| 附件 | SHA256 |\n| --- | --- |\n{rows}"


def _fixture_files() -> dict[str, str]:
    return {
        "version.py": f'VERSION = "{VERSION}"\n',
        "README.md": f"# MCP_CREO_MechDog {VERSION}\n\n当前正式版 **{VERSION}**\n",
        "docs/seed_package.json": (
            f'{{"compatible_server_version": "{VERSION}", "seed_archive_sha256": "{DIGEST}"}}\n'
        ),
        "docs/seed_manifest.json": f'{{"compatible_server_version": "{VERSION}"}}\n',
        "seed_library/seed_manifest.json": f'{{"compatible_server_version": "{VERSION}"}}\n',
        NOTES: (
            f"# {VERSION} 版本说明\n\n"
            f"- [BUG-119](work-items/BUG-119.md)\n"
            f"- [发布记录](validation/RELEASE-{VERSION}.md)\n"
            f"- [版本文件](../version.py)\n"
        ),
        POSTCHECK: (
            "# 发布后附件核对记录\n\n"
            f"## v{VERSION}（预发布）\n\n"
            f"- Release：[v{VERSION}]({RELEASE_URL})\n"
            f"- 种子包 SHA256 `{DIGEST}`\n\n"
            f"{_asset_table()}\n"
        ),
        RECORD: (
            f"# 发布记录 {VERSION}\n\n"
            f"- Release URL：{RELEASE_URL}\n"
            f"- 种子包 SHA256 `{DIGEST}`\n"
            "- source.zip 摘要见同名 sidecar。\n\n"
            f"{_asset_table()}\n\n"
            "## 逐 ID 状态核对\n\n"
            "| ID | 技术状态 | 卡首页 | 主台账 | 差异说明 |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| [BUG-119](../work-items/BUG-119.md) | 已实现并实机验收 | 已交付 {VERSION} "
            f"| 已交付 {VERSION} | 无 |\n"
        ),
        "docs/BACKLOG.md": (
            "# 台账\n\n"
            "| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| [BUG-119](work-items/BUG-119.md) | P1 | 已交付 {VERSION} | {VERSION} | 已交付。 |\n"
        ),
        "docs/work-items/BUG-119.md": (
            f"# BUG-119 surface_loft 实体判定\n\n- 分类：已交付 {VERSION}\n"
        ),
    }


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _write_zip(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in files.items():
            archive.writestr(f"MCP_CREO_MechDog/{name}", text)


def _partial_backlog() -> str:
    return (
        "# 台账\n\n"
        "| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"| [BUG-119](work-items/BUG-119.md) | P1 | 部分交付，剩余待验收 | {VERSION} | 待验收。 |\n"
    )


class ReleaseRecordGateTest(unittest.TestCase):
    def test_complete_fixture_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, _fixture_files())
            self.assertEqual(validate_release_records(VERSION, root=root), [])

    def test_missing_postcheck_section_is_rejected(self):
        files = _fixture_files()
        files[POSTCHECK] = "# 发布后附件核对记录\n\n## v0.23.0（2026-11-12）\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("no '## v0.23.1' section" in problem for problem in problems))

    def test_placeholder_in_section_is_rejected(self):
        files = _fixture_files()
        files[POSTCHECK] += "\n- 附件摘要：待回填\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("placeholder" in problem for problem in problems))

    def test_source_tree_rejects_placeholder_record(self):
        files = _fixture_files()
        files[RECORD] += "\n- 发布核对：待发布后回填\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("placeholder" in problem for problem in problems))

    def test_stale_documents_inside_source_zip_are_rejected(self):
        files = _fixture_files()
        files[POSTCHECK] = "# 发布后附件核对记录\n\n## v0.23.0（2026-11-12）\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, _fixture_files())
            source = root / ASSETS[0]
            _write_zip(source, files)
            problems = validate_release_records(VERSION, source, root=root)
            self.assertTrue(any("POSTCHECK" in problem for problem in problems))

    def test_work_item_status_mismatch_is_rejected(self):
        files = _fixture_files()
        files["docs/BACKLOG.md"] = (
            "# 台账\n\n"
            "| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| [BUG-119](work-items/BUG-119.md) | P1 | 开发中 | {VERSION} | 仍在开发。 |\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("work card BUG-119" in problem for problem in problems))
            self.assertTrue(any("卡首页" in problem for problem in problems))

    def test_partial_backlog_with_delivered_card_is_rejected(self):
        files = _fixture_files()
        files["docs/BACKLOG.md"] = _partial_backlog()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("work card BUG-119" in problem for problem in problems))

    def test_explained_mismatch_is_allowed(self):
        files = _fixture_files()
        files["docs/BACKLOG.md"] = _partial_backlog()
        files[RECORD] = files[RECORD].replace(
            "| 已交付 0.23.1 | 无 |", "| 已交付 0.23.1 | 整体卡仍有剩余 |"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            self.assertEqual(validate_release_records(VERSION, root=root), [])

    def test_ledger_cell_mismatch_is_rejected(self):
        files = _fixture_files()
        files["docs/BACKLOG.md"] = _partial_backlog()
        files["docs/work-items/BUG-119.md"] = (
            f"# BUG-119 surface_loft 实体判定\n\n- 分类：部分交付 {VERSION}\n"
        )
        files[RECORD] = files[RECORD].replace(
            f"| 已交付 {VERSION} | 已交付 {VERSION} | 无 |",
            f"| 部分交付 {VERSION} | 已交付 {VERSION} | 无 |",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("主台账" in problem for problem in problems))

    def test_release_table_mismatch_outside_release_rows_is_rejected(self):
        files = _fixture_files()
        files["docs/BACKLOG.md"] += (
            "| [FEAT-066](work-items/FEAT-066.md) | P1 | 部分交付，剩余待规划 | 未排期 | 剩余。 |\n"
        )
        files["docs/work-items/FEAT-066.md"] = "# FEAT-066 b_spline\n\n- 分类：已交付 0.23.0\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("work card FEAT-066" in problem for problem in problems))

    def test_broken_release_note_link_is_rejected(self):
        files = _fixture_files()
        files[NOTES] += "\n- [错误](../work-items/BUG-119.md)\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(any("broken local link" in problem for problem in problems))

    def test_broken_link_inside_source_zip_is_rejected(self):
        files = _fixture_files()
        files[NOTES] += "\n- [错误](../work-items/BUG-119.md)\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, _fixture_files())
            source = root / ASSETS[0]
            _write_zip(source, files)
            problems = validate_release_records(VERSION, source, root=root)
            self.assertTrue(any("broken local link" in problem for problem in problems))

    def test_work_item_missing_from_card_is_rejected(self):
        files = _fixture_files()
        del files["docs/work-items/BUG-119.md"]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            problems = validate_release_records(VERSION, root=root)
            self.assertTrue(
                any("missing docs/work-items/BUG-119.md" in problem for problem in problems)
            )

    def test_version_before_enforcement_skips_record_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(validate_release_records("0.23.0", root=Path(temp)), [])

    def test_non_semver_version_is_rejected(self):
        self.assertTrue(validate_release_records("0.23", root=Path(".")))


VERSION2 = "0.26.0"
PREVIOUS = "0.25.0"
PREVIOUS_COMMIT = "38bee48692d67d7f962d21ad713abbaa821c2fa7"
SNAPSHOT = f"docs/releases/{VERSION2}.json"
EVIDENCE = "docs/evidence.txt"
EVIDENCE_BYTES = b"evidence"
EVIDENCE_DIGEST = hashlib.sha256(EVIDENCE_BYTES).hexdigest()


def _snapshot(**overrides) -> str:
    document = {
        "schema_version": 1,
        "version": VERSION2,
        "previous_version": PREVIOUS,
        "previous_release_tag": f"v{PREVIOUS}",
        "previous_release_commit": PREVIOUS_COMMIT,
        "remote_verification": "pending",
        "delivery_ids": ["BUG-150"],
    }
    document.update(overrides)
    return json.dumps(document, indent=2) + "\n"


def _evidence_manifest() -> str:
    return (
        json.dumps(
            {
                "schema_version": 1,
                "files": [
                    {
                        "path": EVIDENCE,
                        "bytes": len(EVIDENCE_BYTES),
                        "sha256": EVIDENCE_DIGEST,
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )


def _snapshot_files() -> dict[str, str]:
    return {
        "version.py": f'VERSION = "{VERSION2}"\n',
        "README.md": f"# MCP_CREO_MechDog {VERSION2}\n\n当前正式版 **{VERSION2}**\n",
        "docs/seed_package.json": (
            f'{{"compatible_server_version": "{VERSION2}", "seed_archive_sha256": "{DIGEST}"}}\n'
        ),
        "docs/seed_manifest.json": f'{{"compatible_server_version": "{VERSION2}"}}\n',
        "seed_library/seed_manifest.json": f'{{"compatible_server_version": "{VERSION2}"}}\n',
        SNAPSHOT: _snapshot(),
        "docs/distribution_evidence.json": _evidence_manifest(),
        EVIDENCE: EVIDENCE_BYTES.decode("utf-8"),
        f"docs/RELEASE_NOTES_{VERSION2}.md": (
            f"# {VERSION2} 版本说明\n\n"
            f"- 上一版本：{PREVIOUS}\n"
            f"- [BUG-150](work-items/BUG-150.md)\n"
            f"- [发布记录](validation/RELEASE-{VERSION2}.md)\n"
            f"- [版本文件](../version.py)\n"
        ),
        POSTCHECK: (
            "# 发布后附件核对记录\n\n"
            f"## v{VERSION2}（预发布）\n\n"
            f"- Release：[v{VERSION2}]({_release_url(VERSION2)})\n"
            f"- 种子包 SHA256 `{DIGEST}`\n\n"
            f"{_version_asset_table(VERSION2)}\n"
        ),
        f"docs/validation/RELEASE-{VERSION2}.md": (
            f"# 发布记录 {VERSION2}\n\n"
            f"- 上一版本：{PREVIOUS}\n"
            f"- Release URL：{_release_url(VERSION2)}\n"
            f"- 种子包 SHA256 `{DIGEST}`\n"
            "- source.zip 摘要见同名 sidecar。\n"
            "- 发布后核对：发布后执行，当前未验证。\n\n"
            f"{_version_asset_table(VERSION2)}\n\n"
            "## 逐 ID 状态核对\n\n"
            "| ID | 技术状态 | 交付版本 | 卡首页 | 主台账 | 差异说明 | 实际 Release |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            f"| [BUG-150](../work-items/BUG-150.md) | 已交付 {VERSION2} | {VERSION2} "
            f"| 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v{VERSION2} |\n"
        ),
        "docs/BACKLOG.md": (
            "# 台账\n\n"
            "| ID / 工作卡 | 优先级 | 当前状态 | 目标版本 | 简短剩余工作 |\n"
            "| --- | --- | --- | --- | --- |\n"
            f"| [BUG-150](work-items/BUG-150.md) | P1 | 已交付 {VERSION2} | {VERSION2} "
            "| 已交付。 |\n"
        ),
        "docs/BACKLOG_COMPLETED.md": (
            "# 开发台账完成事项归档\n\n"
            "| ID | 优先级 | 状态 | 目标版本 | 完成摘要与证据 |\n"
            "| --- | --- | --- | --- | --- |\n"
        ),
        "docs/work-items/BUG-150.md": (f"# BUG-150 snapshot gate\n\n- 分类：已交付 {VERSION2}\n"),
    }


def _release_url(version: str) -> str:
    return f"https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v{version}"


def _version_asset_table(version: str) -> str:
    rows = "\n".join(
        f"| `MCP_CREO_MechDog-{version}-{name}` | `{'b' * 64}` |"
        for name in (
            "source.zip",
            "source.zip.sha256",
            "seed-library.zip",
            "seed-library.zip.sha256",
        )
    )
    return f"| 附件 | SHA256 |\n| --- | --- |\n{rows}"


class DeliverySnapshotGateTest(unittest.TestCase):
    """DEV-083 R1/R2: a frozen delivery snapshot makes the table prove itself."""

    def run_gate(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, files)
            return validate_release_records(VERSION2, root=root)

    def test_complete_snapshot_fixture_passes(self):
        self.assertEqual(self.run_gate(_snapshot_files()), [])

    def test_release_delivery_ids_reads_the_frozen_set(self):
        files = _snapshot_files()

        def read(name: str) -> str | None:
            return files.get(name)

        self.assertEqual(release_delivery_ids(VERSION2, read), {"BUG-150"})

    def test_replaced_delivery_id_is_rejected(self):
        files = _snapshot_files()
        files[f"docs/validation/RELEASE-{VERSION2}.md"] = files[
            f"docs/validation/RELEASE-{VERSION2}.md"
        ].replace("[BUG-150]", "[BUG-005]")
        files["docs/BACKLOG.md"] += (
            f"| [BUG-005](work-items/BUG-005.md) | P1 | 已交付 {VERSION2} | {VERSION2} | 已交付。 |\n"
        )
        files["docs/work-items/BUG-005.md"] = f"# BUG-005\n\n- 分类：已交付 {VERSION2}\n"
        problems = self.run_gate(files)
        self.assertTrue(any("missing frozen delivery id" in problem for problem in problems))
        self.assertTrue(any("not in the frozen delivery set" in problem for problem in problems))

    def test_missing_and_extra_delivery_ids_are_rejected(self):
        files = _snapshot_files()
        files[SNAPSHOT] = _snapshot(delivery_ids=["BUG-150", "BUG-151"])
        problems = self.run_gate(files)
        self.assertTrue(any("BUG-151" in problem and "missing" in problem for problem in problems))
        files = _snapshot_files()
        files[f"docs/validation/RELEASE-{VERSION2}.md"] = files[
            f"docs/validation/RELEASE-{VERSION2}.md"
        ].replace(
            f"| [BUG-150](../work-items/BUG-150.md) | 已交付 {VERSION2} | {VERSION2} "
            f"| 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v{VERSION2} |",
            f"| [BUG-150](../work-items/BUG-150.md) | 已交付 {VERSION2} | {VERSION2} "
            f"| 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v{VERSION2} |\n"
            f"| [BUG-005](../work-items/BUG-005.md) | 已交付 {VERSION2} | {VERSION2} "
            f"| 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v{VERSION2} |",
        )
        files["docs/BACKLOG.md"] += (
            f"| [BUG-005](work-items/BUG-005.md) | P1 | 已交付 {VERSION2} | {VERSION2} | 已交付。 |\n"
        )
        files["docs/work-items/BUG-005.md"] = f"# BUG-005\n\n- 分类：已交付 {VERSION2}\n"
        problems = self.run_gate(files)
        self.assertTrue(any("not in the frozen delivery set" in problem for problem in problems))

    def test_duplicate_snapshot_ids_are_rejected(self):
        files = _snapshot_files()
        files[SNAPSHOT] = _snapshot(delivery_ids=["BUG-150", "BUG-150"])
        problems = self.run_gate(files)
        self.assertTrue(any("more than once" in problem for problem in problems))

    def test_delivery_version_and_release_columns_are_checked(self):
        files = _snapshot_files()
        record = f"docs/validation/RELEASE-{VERSION2}.md"
        files[record] = files[record].replace(
            f"| {VERSION2} | 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v{VERSION2} |",
            f"| 0.25.0 | 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v0.25.0 |",
        )
        problems = self.run_gate(files)
        self.assertTrue(any("交付版本" in problem for problem in problems))
        self.assertTrue(any("实际 Release" in problem for problem in problems))

    def test_explanation_does_not_exempt_the_ledger(self):
        files = _snapshot_files()
        record = f"docs/validation/RELEASE-{VERSION2}.md"
        files[record] = files[record].replace(
            f"| 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v{VERSION2} |",
            f"| 已交付 {VERSION2} | 已完成 | 剩余范围见工作卡 | v{VERSION2} |",
        )
        problems = self.run_gate(files)
        self.assertTrue(any("主台账" in problem for problem in problems))

    def test_archived_delivery_id_is_accepted(self):
        files = _snapshot_files()
        files["docs/BACKLOG.md"] = files["docs/BACKLOG.md"].replace(
            f"| [BUG-150](work-items/BUG-150.md) | P1 | 已交付 {VERSION2} | {VERSION2} "
            "| 已交付。 |\n",
            "",
        )
        files["docs/BACKLOG_COMPLETED.md"] += (
            f"| [BUG-150](work-items/BUG-150.md) | P1 | 已完成（{VERSION2} 交付） | "
            f"{VERSION2} | 已交付。 |\n"
        )
        record = f"docs/validation/RELEASE-{VERSION2}.md"
        files[record] = files[record].replace(
            f"| 已交付 {VERSION2} | 已交付 {VERSION2} | 无 | v{VERSION2} |",
            f"| 已交付 {VERSION2} | 已完成（{VERSION2} 交付） | 无 | v{VERSION2} |",
        )
        self.assertEqual(self.run_gate(files), [])

    def test_unknown_archived_state_is_not_delivered(self):
        files = _snapshot_files()
        files["docs/BACKLOG.md"] = files["docs/BACKLOG.md"].replace(
            f"| [BUG-150](work-items/BUG-150.md) | P1 | 已交付 {VERSION2} | {VERSION2} "
            "| 已交付。 |\n",
            "",
        )
        files["docs/BACKLOG_COMPLETED.md"] += (
            f"| [BUG-150](work-items/BUG-150.md) | P1 | 开发中 | {VERSION2} | 仍在开发。 |\n"
        )
        problems = self.run_gate(files)
        self.assertTrue(any("not a delivered class" in problem for problem in problems))

    def test_out_of_table_developing_row_with_delivered_card_is_rejected(self):
        files = _snapshot_files()
        files["docs/BACKLOG.md"] += (
            f"| [BUG-161](work-items/BUG-161.md) | P2 | 开发中 | {VERSION2} | 仍在开发。 |\n"
        )
        files["docs/work-items/BUG-161.md"] = f"# BUG-161\n\n- 分类：已交付 {VERSION2}\n"
        problems = self.run_gate(files)
        self.assertTrue(any("BUG-161" in problem for problem in problems))

    def test_packaged_record_does_not_claim_future_remote_verification(self):
        files = _snapshot_files()
        record = f"docs/validation/RELEASE-{VERSION2}.md"
        files[record] = files[record].replace(
            "发布后核对：发布后执行，当前未验证。",
            f"发布后核对：`tools/check_release_assets.py --tag v{VERSION2}` → exit 0。",
        )
        problems = self.run_gate(files)
        self.assertTrue(any("claims remote verification" in problem for problem in problems))

    def test_pending_record_must_state_the_current_status(self):
        files = _snapshot_files()
        record = f"docs/validation/RELEASE-{VERSION2}.md"
        files[record] = files[record].replace("- 发布后核对：发布后执行，当前未验证。\n", "")
        problems = self.run_gate(files)
        self.assertTrue(any("发布后执行，当前未验证" in problem for problem in problems))

    def test_previous_version_mismatch_is_rejected(self):
        files = _snapshot_files()
        record = f"docs/validation/RELEASE-{VERSION2}.md"
        files[record] = files[record].replace(f"上一版本：{PREVIOUS}", "上一版本：0.24.0")
        problems = self.run_gate(files)
        self.assertTrue(any("上一版本" in problem for problem in problems))

    def test_snapshot_previous_tag_and_commit_are_checked(self):
        files = _snapshot_files()
        files[SNAPSHOT] = _snapshot(previous_release_tag="v0.24.0")
        self.assertTrue(any("previous_release_tag" in p for p in self.run_gate(files)))
        files = _snapshot_files()
        files[SNAPSHOT] = _snapshot(previous_release_commit="not-a-commit")
        self.assertTrue(any("previous_release_commit" in p for p in self.run_gate(files)))

    def test_missing_distribution_evidence_is_rejected(self):
        files = _snapshot_files()
        del files["docs/distribution_evidence.json"]
        problems = self.run_gate(files)
        self.assertTrue(any("distribution_evidence.json" in problem for problem in problems))

    def test_changed_approved_evidence_is_rejected(self):
        files = _snapshot_files()
        files[EVIDENCE] = "tampered\n"
        problems = self.run_gate(files)
        self.assertTrue(any("Approved evidence" in problem for problem in problems))

    def test_snapshot_checks_run_inside_the_source_zip(self):
        files = _snapshot_files()
        files[f"docs/validation/RELEASE-{VERSION2}.md"] = files[
            f"docs/validation/RELEASE-{VERSION2}.md"
        ].replace("[BUG-150]", "[BUG-005]")
        files["docs/BACKLOG.md"] += (
            f"| [BUG-005](work-items/BUG-005.md) | P1 | 已交付 {VERSION2} | {VERSION2} | 已交付。 |\n"
        )
        files["docs/work-items/BUG-005.md"] = f"# BUG-005\n\n- 分类：已交付 {VERSION2}\n"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_tree(root, _snapshot_files())
            source = root / "source.zip"
            _write_zip(source, files)
            problems = validate_release_records(VERSION2, source, root=root)
        self.assertTrue(any("frozen delivery" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
