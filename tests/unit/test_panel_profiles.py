"""BUG-120/D1: panel profiles are frozen evidence, and only the driver admits a candidate.

A normal server may use a certified profile only. A candidate profile is reachable
solely through the development driver's ticket, which binds one workspace, one
profile digest and the executor digests; every mismatch refuses before a job.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from creo_mechdog import panel_profiles

COMMANDS = {"open": "~ Command ProCmdFtBndBlend", "finalize": "~ Activate main_dlg_cur.Done"}
WORKER_SHA = "a" * 64


def manifest(profiles, contract=panel_profiles.CONTRACT):
    return {"contract": contract, "profiles": profiles}


def profile(status="candidate", certification=None, commands=None, digest=None):
    commands = commands or COMMANDS
    entry = {
        "profile_id": "creo10-bbl-1",
        "status": status,
        "release_numeric": 42,
        "creo_release": "10.0.0.0",
        "commands": commands,
        "digest": digest or panel_profiles.command_digest(commands),
    }
    if certification is not None:
        entry["certification"] = certification
    return entry


class Library(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        (self.root / "templates/panel/certifications").mkdir(parents=True)

    def tearDown(self):
        self._directory.cleanup()

    def write_manifest(self, document):
        path = self.root / "templates/panel/manifest.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def write_certification(self, name="creo10-bbl-1.json", **overrides):
        record = {"profile_digest": panel_profiles.command_digest(COMMANDS), "job_id": "j"}
        record.update(overrides.pop("record", {}))
        path = self.root / "templates/panel/certifications" / name
        path.write_text(json.dumps(record), encoding="utf-8")
        body = path.read_bytes()
        certification = {
            "file": name,
            "digest": hashlib.sha256(body).hexdigest(),
            "environment": {"creo_release": "10.0.0.0", "release_numeric": 42},
        }
        certification.update(overrides)
        return certification


class ShippedLibraryIsClosed(Library):
    def test_the_repository_manifest_is_valid_and_empty(self):
        self.assertEqual(panel_profiles.profiles(), [])

    def test_find_profile_names_the_known_profiles(self):
        with self.assertRaises(panel_profiles.PanelProfileError) as caught:
            panel_profiles.find_profile("creo10-bbl-1")
        self.assertIn("known: none", str(caught.exception))

    def test_normal_requests_have_no_certified_profile(self):
        with self.assertRaises(panel_profiles.PanelProfileError) as caught:
            panel_profiles.certified_profile()
        text = str(caught.exception)
        self.assertIn("no certified UI profile", text)
        self.assertIn("No native job was queued".lower(), text.lower())

    def test_a_missing_manifest_is_an_error_not_an_empty_library(self):
        with self.assertRaises(panel_profiles.PanelProfileError) as caught:
            panel_profiles.profiles(self.root)
        self.assertIn("is missing", str(caught.exception))


class ManifestValidation(Library):
    def test_a_candidate_profile_is_read_without_a_certification(self):
        self.write_manifest(manifest([profile()]))
        entries = panel_profiles.profiles(self.root)
        self.assertEqual([entry.profile_id for entry in entries], ["creo10-bbl-1"])
        self.assertIsNone(entries[0].certification)

    def test_a_changed_command_text_invalidates_the_digest(self):
        entry = profile(commands={"open": "different"})
        entry["digest"] = panel_profiles.command_digest(COMMANDS)
        self.write_manifest(manifest([entry]))
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "does not match its frozen"):
            panel_profiles.profiles(self.root)

    def test_an_unknown_profile_key_is_refused(self):
        entry = profile()
        entry["notes"] = "free text"
        self.write_manifest(manifest([entry]))
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "undeclared keys"):
            panel_profiles.profiles(self.root)

    def test_a_wrong_contract_is_refused(self):
        self.write_manifest(manifest([profile()], contract="panel-profiles-v0"))
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "declares contract"):
            panel_profiles.profiles(self.root)

    def test_a_candidate_cannot_carry_a_certification(self):
        certification = self.write_certification()
        self.write_manifest(manifest([profile(certification=certification)]))
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "is a candidate"):
            panel_profiles.profiles(self.root)

    def test_a_certified_profile_needs_its_record(self):
        entry = profile(status="certified")
        self.write_manifest(manifest([entry]))
        with self.assertRaisesRegex(
            panel_profiles.PanelProfileError, "certification must be an object"
        ):
            panel_profiles.profiles(self.root)

    def test_a_missing_record_file_is_refused(self):
        certification = self.write_certification()
        (self.root / "templates/panel/certifications" / "creo10-bbl-1.json").unlink()
        self.write_manifest(manifest([profile(status="certified", certification=certification)]))
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "is missing"):
            panel_profiles.profiles(self.root)

    def test_a_changed_record_invalidates_the_certification(self):
        certification = self.write_certification()
        path = self.root / "templates/panel/certifications/creo10-bbl-1.json"
        path.write_text(json.dumps({"profile_digest": "b" * 64}), encoding="utf-8")
        self.write_manifest(manifest([profile(status="certified", certification=certification)]))
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "does not match"):
            panel_profiles.profiles(self.root)

    def test_a_record_bound_to_another_digest_is_refused(self):
        certification = self.write_certification(record={"profile_digest": "b" * 64})
        self.write_manifest(manifest([profile(status="certified", certification=certification)]))
        with self.assertRaisesRegex(
            panel_profiles.PanelProfileError, "does not bind profile digest"
        ):
            panel_profiles.profiles(self.root)

    def test_a_record_path_cannot_escape_the_certifications_directory(self):
        self.write_manifest(
            manifest(
                [
                    profile(
                        status="certified",
                        certification={
                            "file": "../manifest.json",
                            "digest": "a" * 64,
                            "environment": {"creo_release": "10.0.0.0"},
                        },
                    )
                ]
            )
        )
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "must stay inside"):
            panel_profiles.profiles(self.root)


def identity(worker_sha=WORKER_SHA, release_numeric=42, nested=True):
    record = {
        "identity_status": "verified",
        "worker_sha256": worker_sha,
        "source_digest": "c" * 64,
    }
    if release_numeric is not None:
        if nested:
            record["features"] = {"surface_loft": {"release_numeric": release_numeric}}
        else:
            record["release_numeric"] = release_numeric
    return record


def ticket(workspace, **overrides):
    value = {
        "profile_id": "creo10-bbl-1",
        "run_id": "run-1",
        "workspace": workspace,
        "profile_digest": panel_profiles.command_digest(COMMANDS),
        "worker_sha256": WORKER_SHA,
    }
    value.update(overrides)
    return {panel_profiles.CANDIDATE_ENV: json.dumps(value)}


class CandidateAdmission(Library):
    def setUp(self):
        super().setUp()
        self.write_manifest(manifest([profile()]))
        self.workspace = str(self.root.resolve())

    def test_a_candidate_is_refused_without_the_driver_ticket(self):
        with self.assertRaises(panel_profiles.PanelProfileError) as caught:
            panel_profiles.admit_for_request(identity(), root=self.root, environ={})
        text = str(caught.exception)
        self.assertIn("no certified UI profile", text)
        self.assertIn(panel_profiles.CANDIDATE_ENV, text)
        self.assertIn("no native job was queued", text)

    def test_the_driver_ticket_admits_the_named_profile(self):
        admission = panel_profiles.admit_for_request(
            identity(), root=self.root, environ=ticket(self.workspace)
        )
        self.assertEqual(admission["mode"], "candidate")
        self.assertEqual(admission["profile_id"], "creo10-bbl-1")
        self.assertEqual(admission["candidate"]["run_id"], "run-1")

    def test_a_ticket_for_an_unknown_profile_is_refused_by_name(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "is not in"):
            panel_profiles.admit_for_request(
                identity(),
                root=self.root,
                environ=ticket(self.workspace, profile_id="creo10-other"),
            )

    def test_a_ticket_for_another_profile_does_not_admit_this_one(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "bound to profile"):
            panel_profiles.admit(
                "creo10-bbl-1",
                identity(),
                root=self.root,
                environ=ticket(self.workspace, profile_id="creo10-other"),
            )

    def test_a_ticket_from_another_workspace_is_refused(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "issued for workspace"):
            panel_profiles.admit_for_request(
                identity(), root=self.root, environ=ticket("D:/other/checkout")
            )

    def test_a_ticket_for_another_digest_is_refused(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "names profile digest"):
            panel_profiles.admit_for_request(
                identity(), root=self.root, environ=ticket(self.workspace, profile_digest="b" * 64)
            )

    def test_a_ticket_bound_to_another_worker_is_refused(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "current worker reports"):
            panel_profiles.admit_for_request(
                identity(worker_sha="d" * 64),
                root=self.root,
                environ=ticket(self.workspace),
            )

    def test_an_unverified_worker_is_refused(self):
        with self.assertRaisesRegex(
            panel_profiles.PanelProfileError, "verified worker build identity"
        ):
            panel_profiles.admit_for_request(
                {"identity_status": "worker_missing"},
                root=self.root,
                environ=ticket(self.workspace),
            )

    def test_a_malformed_ticket_is_refused_instead_of_ignored(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "not valid JSON"):
            panel_profiles.admit_for_request(
                identity(), root=self.root, environ={panel_profiles.CANDIDATE_ENV: "{"}
            )

    def test_a_ticket_with_an_undeclared_key_is_refused(self):
        raw = json.loads(ticket(self.workspace)[panel_profiles.CANDIDATE_ENV])
        raw["candidate"] = True
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "undeclared keys"):
            panel_profiles.admit_for_request(
                identity(),
                root=self.root,
                environ={panel_profiles.CANDIDATE_ENV: json.dumps(raw)},
            )

    def test_loader_and_payload_bindings_travel_with_the_admission(self):
        admission = panel_profiles.admit_for_request(
            identity(), root=self.root, environ=ticket(self.workspace, loader_sha256="e" * 64)
        )
        self.assertEqual(admission["candidate"]["bindings"]["loader_sha256"], "e" * 64)
        self.assertEqual(admission["candidate"]["unchecked_bindings"], ["loader_sha256"])

    def test_a_candidate_may_run_before_the_host_release_is_recorded(self):
        admission = panel_profiles.admit_for_request(
            identity(release_numeric=None), root=self.root, environ=ticket(self.workspace)
        )
        self.assertEqual(admission["mode"], "candidate")
        self.assertEqual(admission["unverified_bindings"], ["host_release_numeric"])
        self.assertIsNone(admission["host_release_numeric"])

    def test_a_candidate_on_another_release_is_refused(self):
        with self.assertRaisesRegex(
            panel_profiles.PanelProfileError, "never re-used across releases"
        ):
            panel_profiles.admit_for_request(
                identity(release_numeric=43), root=self.root, environ=ticket(self.workspace)
            )

    def test_a_ticket_for_another_release_is_refused(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "issued for release_numeric"):
            panel_profiles.admit_for_request(
                identity(), root=self.root, environ=ticket(self.workspace, release_numeric=43)
            )

    def test_a_non_integer_ticket_release_is_refused(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "must be an integer"):
            panel_profiles.admit_for_request(
                identity(), root=self.root, environ=ticket(self.workspace, release_numeric="42")
            )


class CertifiedAdmission(Library):
    def setUp(self):
        super().setUp()
        certification = self.write_certification()
        self.write_manifest(manifest([profile(status="certified", certification=certification)]))

    def test_a_certified_profile_is_admitted_without_a_ticket(self):
        admission = panel_profiles.admit_for_request(identity(), root=self.root, environ={})
        self.assertEqual(admission["mode"], "certified")
        self.assertIsNone(admission["candidate"])
        self.assertEqual(admission["release_numeric"], 42)
        self.assertEqual(admission["host_release_numeric"], 42)
        self.assertEqual(admission["unverified_bindings"], [])
        self.assertEqual(admission["certification"]["environment"]["creo_release"], "10.0.0.0")

    def test_a_certified_profile_also_serves_the_driver_ticket(self):
        admission = panel_profiles.admit_for_request(
            identity(), root=self.root, environ=ticket(str(self.root.resolve()))
        )
        self.assertEqual(admission["mode"], "certified")

    def test_a_top_level_host_release_is_matched_too(self):
        admission = panel_profiles.admit_for_request(
            identity(nested=False), root=self.root, environ={}
        )
        self.assertEqual(admission["host_release_numeric"], 42)

    def test_a_host_on_another_release_is_refused(self):
        with self.assertRaisesRegex(
            panel_profiles.PanelProfileError, "never re-used across releases"
        ):
            panel_profiles.admit_for_request(
                identity(release_numeric=43), root=self.root, environ={}
            )

    def test_an_unrecorded_host_release_is_refused_for_a_normal_client(self):
        with self.assertRaisesRegex(panel_profiles.PanelProfileError, "no recorded host release"):
            panel_profiles.admit_for_request(
                identity(release_numeric=None), root=self.root, environ={}
            )


if __name__ == "__main__":
    unittest.main()
