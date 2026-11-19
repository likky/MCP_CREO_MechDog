"""BUG-089 / DEV-053 P04: the seed archive and the release inputs must agree.

The failure regressions here use real built archives and real bytes: a tampered
archive, a wrong digest, a foreign version, disagreeing manifests and a stale
README version section are all rejected before anything is written.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import bridge
from creo_mechdog import panel_profiles, release_integrity, seeds
from tools import package, package_seeds

ROOT = Path(__file__).resolve().parents[2]
VERSION = release_integrity.read_version(ROOT)


def build_seed_archive(root: Path, archive: Path) -> str:
    """Build the real seed archive of ``root`` and return its SHA256."""
    return package_seeds.build_seed_archive(root, archive)


class SeedArchiveFixture(unittest.TestCase):
    """A source tree whose seed library, manifests and record describe one release."""

    def setUp(self):
        self.temp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.temp / "source"
        self.root.mkdir()
        shutil.copytree(ROOT / "seed_library", self.root / "seed_library")
        # BUG-123: a source tree that claims to be releasable now also carries
        # the element tree templates and their manifest.
        shutil.copytree(ROOT / "templates", self.root / "templates")
        (self.root / "docs").mkdir()
        shutil.copy2(ROOT / "docs/seed_manifest.json", self.root / "docs/seed_manifest.json")
        shutil.copy2(ROOT / "LICENSE", self.root / "LICENSE")
        shutil.copy2(ROOT / "README.md", self.root / "README.md")
        (self.root / "version.py").write_text(f'VERSION = "{VERSION}"\n', encoding="utf-8")
        self.archive = self.temp / f"MCP_CREO_MechDog-{VERSION}-seed-library.zip"
        self.digest = build_seed_archive(self.root, self.archive)
        release_integrity.write_sidecar(
            self.archive.with_suffix(".zip.sha256"), self.digest, self.archive.name
        )
        self.write_record(self.digest, VERSION)

    def write_record(self, digest: str, version: str, name: str | None = None):
        record = {
            "compatible_server_version": version,
            "seed_archive_name": name or self.archive.name,
            "seed_archive_sha256": digest,
        }
        (self.root / "docs/seed_package.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )

    def rewrite_archive(self, mutate) -> Path:
        """Rebuild the archive with one member mutated; return the new archive path."""
        target = self.temp / "mutated.zip"
        with zipfile.ZipFile(self.archive) as source:
            members = [(info.filename, source.read(info.filename)) for info in source.infolist()]
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for name, data in members:
                output.writestr(name, mutate(name, data))
        return target


class SeedArchiveValidationTests(SeedArchiveFixture):
    def test_real_built_archive_matches_the_repository_release_inputs(self):
        summary = release_integrity.validate_release_inputs(self.root, self.archive)
        self.assertEqual(summary["version"], VERSION)
        self.assertEqual(summary["seed_archive_sha256"], self.digest)
        self.assertEqual(summary["seed_count"], 9)
        self.assertEqual(summary["readme_title_version"], VERSION)
        self.assertEqual(summary["readme_current_version"], VERSION)

    def test_tampered_archive_bytes_are_rejected(self):
        tampered = self.rewrite_archive(
            lambda name, data: data + b"\x00" if name.endswith(".prt.1") else data
        )
        with self.assertRaisesRegex(ValueError, "SHA256 differs"):
            release_integrity.validate_seed_archive(self.root, tampered)

    def test_trusted_record_digest_mismatch_is_rejected(self):
        self.write_record("0" * 64, VERSION)
        with self.assertRaisesRegex(ValueError, "SHA256 differs"):
            release_integrity.validate_seed_archive(self.root, self.archive)

    def test_foreign_archive_version_is_rejected(self):
        foreign = self.temp / "foreign.zip"
        with zipfile.ZipFile(self.archive) as source:
            members = [(info.filename, source.read(info.filename)) for info in source.infolist()]
        with zipfile.ZipFile(foreign, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for name, data in members:
                output.writestr(
                    name.replace(f"-{VERSION}-seed-library/", "-0.0.1-seed-library/"), data
                )
        self.write_record(hashlib.sha256(foreign.read_bytes()).hexdigest(), VERSION)
        with self.assertRaisesRegex(ValueError, "outside"):
            release_integrity.validate_seed_archive(self.root, foreign)

    def test_archive_manifest_version_mismatch_is_rejected(self):
        manifest = json.loads((self.root / "docs/seed_manifest.json").read_text(encoding="utf-8"))
        manifest["compatible_server_version"] = "0.0.1"
        (self.root / "docs/seed_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            release_integrity.validate_seed_archive(self.root, self.archive)

    def test_native_seed_bytes_inside_the_archive_are_protected(self):
        tampered = self.rewrite_archive(
            lambda name, data: data + b"\x00" if name.endswith(".prt.1") else data
        )
        self.write_record(hashlib.sha256(tampered.read_bytes()).hexdigest(), VERSION)
        with self.assertRaisesRegex(ValueError, "differ from the published SHA256"):
            release_integrity.validate_seed_archive(self.root, tampered)

    def test_unsafe_archive_member_path_is_rejected(self):
        unsafe = self.temp / "unsafe.zip"
        with zipfile.ZipFile(self.archive) as source:
            members = [(info.filename, source.read(info.filename)) for info in source.infolist()]
        with zipfile.ZipFile(unsafe, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for name, data in members:
                output.writestr(name.replace("seeds/", "../escape/", 1), data)
        self.write_record(hashlib.sha256(unsafe.read_bytes()).hexdigest(), VERSION)
        with self.assertRaisesRegex(ValueError, "Unsafe seed archive path"):
            release_integrity.validate_seed_archive(self.root, unsafe)

    def test_disagreeing_seed_manifests_are_rejected(self):
        manifest = json.loads((self.root / "docs/seed_manifest.json").read_text(encoding="utf-8"))
        manifest["compatible_server_version"] = "0.0.1"
        (self.root / "seed_library/seed_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "manifests differ"):
            release_integrity.validate_release_inputs(self.root, self.archive)

    def test_stale_readme_current_version_section_is_rejected(self):
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        (self.root / "README.md").write_text(
            readme.replace(f"当前正式版 **{VERSION}**", "当前正式版 **0.0.1**"), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "README current release section"):
            release_integrity.validate_release_inputs(self.root, self.archive)

    def test_stale_readme_title_version_is_rejected(self):
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        (self.root / "README.md").write_text(
            readme.replace(f"# MCP_CREO_MechDog {VERSION}", "# MCP_CREO_MechDog 0.0.1"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "README title version"):
            release_integrity.validate_release_inputs(self.root, self.archive)

    def test_missing_trusted_record_is_rejected(self):
        (self.root / "docs/seed_package.json").unlink()
        with self.assertRaisesRegex(ValueError, "Trusted seed package record is missing"):
            release_integrity.validate_seed_archive(self.root, self.archive)

    def test_the_shipped_panel_library_is_a_valid_release_input(self):
        # BUG-120/D6+D7: two certified Creo 10 profiles (candidate-2 and the
        # candidate-3 superset) plus their own certification records.
        summary = release_integrity.validate_release_inputs(self.root, self.archive)
        self.assertEqual(summary["panel_certification_count"], 2)

    def test_a_missing_panel_manifest_refuses_the_release_inputs(self):
        (self.root / "templates/panel/manifest.json").unlink()
        with self.assertRaisesRegex(ValueError, "panel profile manifest is missing"):
            release_integrity.validate_release_inputs(self.root, self.archive)

    def test_a_stale_panel_certification_refuses_the_release_inputs(self):
        library = self.root / "templates" / "panel"
        (library / "certifications").mkdir(exist_ok=True)
        record = library / "certifications" / "creo10-panel-smoke.json"
        record.write_text(json.dumps({"profile_digest": "0" * 64}), encoding="utf-8")
        commands = {
            "open_macro": "~ Command `ProCmdFtBndBlend`;",
            "select_command": "~ Command `" + panel_profiles.SELECT_PLACEHOLDER + "`;",
            "done_macro": "~ Activate `main_dlg_cur` `dashInst0.Done`;",
            "done_command": "ProCmdFtBndBlend",
        }
        (library / "manifest.json").write_text(
            json.dumps(
                {
                    "contract": panel_profiles.CONTRACT,
                    "profiles": [
                        {
                            "profile_id": "creo10-panel-smoke",
                            "status": "certified",
                            "release_numeric": 10,
                            "creo_release": "Creo 10.0.0.0",
                            "commands": commands,
                            "digest": panel_profiles.command_digest(commands),
                            "certification": {
                                "file": record.name,
                                "digest": hashlib.sha256(record.read_bytes()).hexdigest(),
                                "environment": {"host": "win32"},
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "no longer certified"):
            release_integrity.validate_release_inputs(self.root, self.archive)


class SeedArchiveInstallTests(SeedArchiveFixture):
    """The published archive installs through the public seed library entry."""

    def install_root(self) -> Path:
        root = self.temp / "install-root"
        root.mkdir()
        shutil.copytree(ROOT / "seed_library", root / "seed_library")
        (root / "docs").mkdir()
        shutil.copy2(ROOT / "docs/seed_manifest.json", root / "docs/seed_manifest.json")
        shutil.copy2(ROOT / "docs/seed_package.json", root / "docs/seed_package.json")
        shutil.copy2(ROOT / "LICENSE", root / "LICENSE")
        shutil.copy2(ROOT / "version.py", root / "version.py")
        return root

    def test_published_archive_installs_into_a_temporary_root(self):
        install_root = self.install_root()
        shutil.rmtree(install_root / "seed_library")
        with patch.object(bridge, "ROOT", install_root):
            result = seeds.install_seed_library(archive_file=str(self.archive))
        self.assertTrue(result["installed"])
        self.assertEqual(result["available_count"], 9)
        self.assertTrue((install_root / "seed_library/seed_manifest.json").is_file())

    def test_tampered_archive_is_refused_before_writing_the_target(self):
        install_root = self.install_root()
        shutil.rmtree(install_root / "seed_library")
        tampered = self.rewrite_archive(
            lambda name, data: data + b"\x00" if name.endswith(".prt.1") else data
        )
        with patch.object(bridge, "ROOT", install_root):
            with self.assertRaisesRegex(ValueError, "SHA256 differs"):
                seeds.install_seed_library(archive_file=str(tampered))
        self.assertFalse((install_root / "seed_library").exists())

    def test_wrong_digest_archive_is_refused_before_writing_the_target(self):
        install_root = self.install_root()
        shutil.rmtree(install_root / "seed_library")
        record = json.loads((install_root / "docs/seed_package.json").read_text(encoding="utf-8"))
        record["seed_archive_sha256"] = "0" * 64
        (install_root / "docs/seed_package.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        with patch.object(bridge, "ROOT", install_root):
            with self.assertRaisesRegex(ValueError, "SHA256 differs"):
                seeds.install_seed_library(archive_file=str(self.archive))
        self.assertFalse((install_root / "seed_library").exists())

    def test_directory_install_stays_compatible(self):
        install_root = self.install_root()
        with patch.object(bridge, "ROOT", install_root):
            result = seeds.install_seed_library()
        self.assertTrue(result["installed"])
        self.assertEqual(result["available_count"], 9)


class SeedPackagingGateTests(SeedArchiveFixture):
    """The source package entry refuses a missing or mismatched seed archive."""

    def run_package(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/package.py"), *args],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )

    def test_missing_seed_archive_argument_is_refused(self):
        result = self.run_package("--output", str(self.temp / "source.zip"))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.temp / "source.zip").exists())

    def test_mismatched_seed_archive_is_refused_without_writing_a_source_package(self):
        wrong = self.temp / "wrong.zip"
        shutil.copy2(self.archive, wrong)
        with zipfile.ZipFile(wrong, "a") as archive:
            archive.writestr("extra.txt", "not part of the release")
        result = self.run_package(
            "--seed-archive", str(wrong), "--output", str(self.temp / "source.zip")
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refused", result.stderr)
        self.assertFalse((self.temp / "source.zip").exists())
        self.assertFalse((self.temp / "source.zip.sha256").exists())

    def test_valid_seed_archive_packages_the_source_with_the_explicit_output(self):
        output = self.temp / f"MCP_CREO_MechDog-{VERSION}-source.zip"
        result = self.run_package("--seed-archive", str(self.archive), "--output", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        self.assertTrue(output.with_suffix(".zip.sha256").is_file())
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
        self.assertIn("MCP_CREO_MechDog/version.py", names)
        self.assertIn("MCP_CREO_MechDog/docs/seed_manifest.json", names)
        self.assertIn("MCP_CREO_MechDog/seed_library/seed_manifest.json", names)

    def test_valid_seed_archive_packages_the_source_with_the_default_output(self):
        default = ROOT.parent / f"MCP_CREO_MechDog-{VERSION}-source.zip"
        self.assertFalse(default.exists(), "default output path is already taken")
        result = self.run_package("--seed-archive", str(self.archive))
        try:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(default.is_file())
        finally:
            default.unlink(missing_ok=True)
            default.with_suffix(".zip.sha256").unlink(missing_ok=True)

    def test_valid_seed_archive_packages_a_new_empty_stage_directory(self):
        stage = self.temp / "stage"
        result = self.run_package(
            "--seed-archive",
            str(self.archive),
            "--output",
            str(self.temp / f"MCP_CREO_MechDog-{VERSION}-source.zip"),
            "--stage",
            str(stage),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((stage / "version.py").is_file())
        self.assertTrue((stage / "docs/seed_manifest.json").is_file())

    def test_existing_output_archive_is_still_refused(self):
        output = self.temp / "source.zip"
        output.write_bytes(b"existing")
        result = self.run_package("--seed-archive", str(self.archive), "--output", str(output))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_bytes(), b"existing")

    def test_non_empty_stage_directory_is_still_refused(self):
        stage = self.temp / "stage"
        stage.mkdir()
        (stage / "occupied.txt").write_text("keep me", encoding="utf-8")
        result = self.run_package(
            "--seed-archive",
            str(self.archive),
            "--output",
            str(self.temp / "source.zip"),
            "--stage",
            str(stage),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((stage / "occupied.txt").read_text(encoding="utf-8"), "keep me")


class SeedPackagerAllowlistTests(unittest.TestCase):
    def test_feedback0184_manifest_members_are_distributed_intact(self):
        base = ROOT / "docs/validation/feedback-0.18.4-2026-11-08"
        packaged = set(package.source_files())
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
        for item in manifest["files"]:
            path = base / item["archived_path"]
            self.assertIn(path, packaged)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])

    def test_seed_packager_and_release_gate_share_one_member_set(self):
        members = {
            path.relative_to(ROOT / "seed_library").as_posix()
            for path in release_integrity.seed_library_files(ROOT)
        }
        self.assertEqual(len(members), 24)
        self.assertIn("seed_manifest.json", members)
        self.assertIn("LICENSE", members)
        self.assertIn("resolve_seed.py", members)
        self.assertTrue(any(name.endswith(".prt.1") for name in members))

    def test_source_package_allowlist_includes_the_seed_library_members(self):
        packaged = {path.relative_to(ROOT).as_posix() for path in package.source_files()}
        for path in release_integrity.seed_library_files(ROOT):
            self.assertIn(path.relative_to(ROOT).as_posix(), packaged)

    def test_source_package_includes_native_test_sources_only(self):
        packaged = {path.relative_to(ROOT).as_posix() for path in package.source_files()}
        fixtures = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "tests/native").rglob("*")
            if path.is_file() and path.suffix in {".cpp", ".h", ".hpp"}
        }
        self.assertIn("tests/native/test_axis_geometry.cpp", fixtures)
        self.assertIn("tests/native/test_surface_measure_guard.cpp", fixtures)
        self.assertEqual({name for name in packaged if name.startswith("tests/native/")}, fixtures)

    def test_source_package_ships_every_root_module(self):
        packaged = {path.relative_to(ROOT).as_posix() for path in package.source_files()}
        root_modules = {path.name for path in ROOT.glob("*.py") if path.is_file()}
        self.assertTrue(root_modules)
        self.assertEqual(
            sorted(root_modules - packaged),
            [],
            "a root-level module is imported at runtime but missing from the source allowlist",
        )

    def test_seeds_module_exposes_the_trusted_digest_entry_point(self):
        self.assertEqual(
            seeds.expected_archive_sha256(), release_integrity.trusted_seed_archive_digest(ROOT)
        )
        self.assertRegex(seeds.expected_archive_sha256(), r"^[a-f0-9]{64}$")


class DistributionEvidenceTests(unittest.TestCase):
    """DEV-083 R3: reviewed TXT evidence ships byte-exact, nothing else does."""

    def write_manifest(self, root: Path, name: str, data: bytes, *, bytes_: int | None = None):
        (root / "docs").mkdir(parents=True, exist_ok=True)
        target = root / name
        if ".." not in name.replace("\\", "/").split("/") and name.startswith("docs/"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        document = {
            "schema_version": 1,
            "files": [
                {
                    "path": name,
                    "bytes": len(data) if bytes_ is None else bytes_,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ],
        }
        (root / release_integrity.DISTRIBUTION_EVIDENCE).write_text(
            json.dumps(document), encoding="utf-8"
        )

    def test_approved_txt_is_shipped_byte_exact(self):
        packaged = {path.relative_to(ROOT).as_posix(): path for path in package.source_files()}
        for path in release_integrity.approved_evidence_files(ROOT):
            relative = path.relative_to(ROOT).as_posix()
            self.assertIn(relative, packaged)
            self.assertEqual(packaged[relative].read_bytes(), path.read_bytes())
        self.assertIn(
            "docs/validation/feedback-0.23.2-2026-11-12/originals/MANIFEST-SHA256.txt", packaged
        )

    def test_unapproved_txt_is_excluded(self):
        packaged = {path.relative_to(ROOT).as_posix() for path in package.source_files()}
        unapproved = (
            "docs/validation/feedback-0.23.2-2026-11-12/originals/源数据/"
            "简易护卫舰_跨软件三维建模自然语言说明.txt"
        )
        self.assertNotIn(unapproved, packaged)

    def test_missing_or_changed_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_manifest(root, "docs/evidence.txt", b"evidence")
            self.assertEqual(
                [path.name for path in release_integrity.approved_evidence_files(root)],
                ["evidence.txt"],
            )
            (root / "docs/evidence.txt").write_bytes(b"changed!")
            with self.assertRaisesRegex(ValueError, "but the manifest declares"):
                release_integrity.approved_evidence_files(root)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_manifest(root, "docs/evidence.txt", b"evidence")
            (root / "docs/evidence.txt").unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                release_integrity.approved_evidence_files(root)

    def test_declared_byte_count_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_manifest(root, "docs/evidence.txt", b"evidence", bytes_=1)
            with self.assertRaisesRegex(ValueError, "bytes"):
                release_integrity.approved_evidence_files(root)

    def test_unsafe_or_unapproved_txt_paths_are_rejected(self):
        for name in (
            "../evidence.txt",
            "docs/../evidence.txt",
            "docs/evidence.md",
            "evidence.txt",
        ):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.write_manifest(root, name, b"evidence")
                with (
                    self.subTest(path=name),
                    self.assertRaisesRegex(ValueError, "unsafe or non-TXT"),
                ):
                    release_integrity.approved_evidence_files(root)


class PanelLibraryFixture(unittest.TestCase):
    """A source tree carrying one resident-panel profile library (BUG-120/D1)."""

    # The four slots a panel profile must freeze; the selection step names the
    # resident command by placeholder because it is created at run time.
    commands = {
        "open_macro": "~ Command `ProCmdFtBndBlend`;",
        "select_command": "~ Command `" + panel_profiles.SELECT_PLACEHOLDER + "`;",
        "done_macro": "~ Activate `main_dlg_cur` `dashInst0.Done`;",
        "done_command": "ProCmdFtBndBlend",
    }

    def setUp(self):
        self.temp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.temp / "source"
        self.library = self.root / "templates" / "panel"
        self.manifest = self.library / "manifest.json"
        self.library.mkdir(parents=True)
        self.digest = panel_profiles.command_digest(self.commands)

    def profile(self, **overrides) -> dict:
        entry = {
            "profile_id": "creo10-panel-smoke",
            "status": "certified",
            "release_numeric": 10,
            "creo_release": "Creo 10.0.0.0",
            "commands": dict(self.commands),
            "digest": self.digest,
        }
        entry.update(overrides)
        return entry

    def write_manifest(self, *profiles: dict) -> Path:
        document = {"contract": panel_profiles.CONTRACT, "profiles": list(profiles)}
        self.manifest.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return self.manifest

    def write_certification(
        self, name: str = "creo10-panel-smoke.json", *, profile_digest: str | None = None
    ) -> Path:
        directory = self.library / "certifications"
        directory.mkdir(exist_ok=True)
        path = directory / name
        record = {"profile_digest": self.digest if profile_digest is None else profile_digest}
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return path

    def certification(self, path: Path, **overrides) -> dict:
        entry = {
            "file": path.relative_to(self.library / "certifications").as_posix(),
            "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            "environment": {"host": "win32", "creo_release": "10.0.0.0"},
        }
        entry.update(overrides)
        return entry


class PanelLibraryAllowlistTests(PanelLibraryFixture):
    """Only the manifest and the certification records it names are shipped."""

    def test_a_certified_profile_ships_its_manifest_and_record(self):
        record = self.write_certification()
        self.write_manifest(self.profile(certification=self.certification(record)))
        self.assertEqual(
            release_integrity.panel_profile_library_files(self.root), [self.manifest, record]
        )

    def test_a_record_nobody_references_is_not_shipped(self):
        shipped = self.write_certification("shipped.json")
        stray = self.write_certification("stray.json")
        self.write_manifest(self.profile(certification=self.certification(shipped)))
        files = release_integrity.panel_profile_library_files(self.root)
        self.assertIn(shipped, files)
        self.assertNotIn(stray, files)

    def test_the_shipped_repository_library_ships_the_certified_profile(self):
        # The library carries two certified Creo 10 profiles (candidate-2 from
        # 2026-11-18 and the candidate-3 superset from 2026-11-19) plus the
        # second-direction recording frozen for the superset, so the shipped set is
        # the manifest, both recordings and both certification records.
        shipped = release_integrity.panel_profile_library_files(ROOT)
        names = {path.relative_to(ROOT).as_posix() for path in shipped}
        self.assertEqual(
            names,
            {
                "templates/panel/manifest.json",
                "templates/panel/recordings/creo10_blend_gui_t1a.pro",
                "templates/panel/recordings/creo10_blend_gui_t2.pro",
                "templates/panel/certifications/creo10-bbl-2026-11-18.json",
                "templates/panel/certifications/creo10-bbl-2026-11-19.json",
            },
        )
        self.assertEqual(
            [entry.status for entry in panel_profiles.profiles(ROOT)],
            ["certified", "certified", "candidate"],
        )

    def test_the_source_package_ships_the_panel_manifest(self):
        packaged = {path.relative_to(ROOT).as_posix() for path in package.source_files()}
        self.assertIn("templates/panel/manifest.json", packaged)

    def test_the_packager_uses_the_shared_panel_allowlist(self):
        source = (ROOT / "tools" / "package.py").read_text(encoding="utf-8")
        self.assertIn("panel_profile_library_files(ROOT)", source)


class PanelLibraryRefusalTests(PanelLibraryFixture):
    """A missing, changed or escaping record fails before the ZIP is written."""

    def test_a_missing_manifest_is_refused(self):
        with self.assertRaisesRegex(ValueError, "panel profile manifest is missing"):
            release_integrity.panel_profile_library_files(self.root)

    def test_a_referenced_certification_that_is_missing_is_refused(self):
        self.write_manifest(
            self.profile(
                certification={
                    "file": "absent.json",
                    "digest": hashlib.sha256(b"{}").hexdigest(),
                    "environment": {"host": "win32"},
                }
            )
        )
        with self.assertRaisesRegex(ValueError, "is missing"):
            release_integrity.panel_profile_library_files(self.root)

    def test_a_certification_path_that_escapes_the_library_is_refused(self):
        self.write_manifest(
            self.profile(
                certification={
                    "file": "../escape.json",
                    "digest": hashlib.sha256(b"{}").hexdigest(),
                    "environment": {"host": "win32"},
                }
            )
        )
        with self.assertRaisesRegex(ValueError, "must stay inside"):
            release_integrity.panel_profile_library_files(self.root)

    def test_a_changed_certification_record_is_refused(self):
        record = self.write_certification()
        self.write_manifest(self.profile(certification=self.certification(record)))
        record.write_bytes(record.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "does not match"):
            release_integrity.panel_profile_library_files(self.root)

    def test_a_certification_for_older_commands_is_refused(self):
        record = self.write_certification(profile_digest="0" * 64)
        self.write_manifest(self.profile(certification=self.certification(record)))
        with self.assertRaisesRegex(ValueError, "no longer certified"):
            release_integrity.panel_profile_library_files(self.root)

    def test_the_gate_reuses_the_profile_module_rules(self):
        # A digest that does not match its own command text is refused by
        # creo_mechdog.panel_profiles; the packaging gate must not carry a second
        # copy of that rule that could disagree with it.
        self.write_manifest(self.profile(digest="0" * 64))
        with self.assertRaisesRegex(ValueError, "does not match its frozen command text"):
            release_integrity.panel_profile_library_files(self.root)


if __name__ == "__main__":
    unittest.main()
