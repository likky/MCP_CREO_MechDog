"""Versioned resident-panel UI profiles and the candidate admission gate.

BUG-120/D1. A ``resident_panel`` surface loft replays recorded Creo UI commands,
so the exact command text and the metadata that participated in the run have to be
frozen evidence, not something a caller (or this module) invents per job. This
module only reads and verifies that evidence:

- ``templates/panel/manifest.json`` names every profile, its status and the digest
  of its frozen command text;
- ``templates/panel/certifications/`` holds the acceptance record of a profile that
  was measured on a real host.

Two modes reach the same public tool chain:

- **certified**: a profile with ``status="certified"`` whose certification file is
  still present and still names the frozen command digest. Normal clients can only
  use this mode.
- **candidate**: the development driver (``tools/test_surface_loft_panel.py``)
  starts a server process with ``CREO_MECHDOG_PANEL_CANDIDATE`` set. The ticket
  binds one run, this workspace, the profile digest and (when known) the worker,
  loader and payload digests. A client payload cannot claim candidate mode: no
  public tool exposes a candidate field and the plan schema refuses unknown keys.

Nothing here proves a profile works. A certified profile is evidence from the
target host; a candidate profile is explicitly *not* a published capability, and
its result marker travels with the job so no receipt reads as released support.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

CONTRACT = "panel-profiles-v1"
LIBRARY = "templates/panel"
MANIFEST = "templates/panel/manifest.json"
CERTIFICATIONS = "templates/panel/certifications"
CANDIDATE_ENV = "CREO_MECHDOG_PANEL_CANDIDATE"

#: Keys a profile entry may carry. Anything else is a schema change, not a note.
PROFILE_KEYS = frozenset(
    {
        "profile_id",
        "status",
        "release_numeric",
        "creo_release",
        "commands",
        "digest",
        "certification",
    }
)
CERTIFICATION_KEYS = frozenset({"file", "digest", "environment"})
#: The slots a profile must freeze. The panel route cannot open a dialog without the
#: recorded open sequence, cannot consume a position without the command that issues
#: one selection, and cannot close without the restricted Done. A profile missing any
#: of them is refused at admission, which is before a job exists and long before a
#: dialog opens.
COMMAND_SLOTS = ("open_macro", "select_command", "done_macro", "done_command")
#: Substituted with the resident command the payload registered at initialize time.
#: The recorded mapkey's screen-pick pauses are replaced by one invocation of this
#: command per position, so the profile never carries "wait for a human click".
SELECT_PLACEHOLDER = "%MECHDOG_COMMAND%"

CANDIDATE_REQUIRED = ("profile_id", "run_id", "workspace", "profile_digest")
CANDIDATE_OPTIONAL = ("worker_sha256", "loader_sha256", "payload_sha256")
CANDIDATE_INT_OPTIONAL = ("release_numeric",)
CANDIDATE_KEYS = frozenset(CANDIDATE_REQUIRED + CANDIDATE_OPTIONAL + CANDIDATE_INT_OPTIONAL)

ROOT = Path(__file__).resolve().parents[2]


class PanelProfileError(ValueError):
    """A panel profile is missing, unreadable or not admissible for this request."""


@dataclass(frozen=True)
class PanelProfile:
    """One frozen command profile and, when certified, its acceptance record."""

    profile_id: str
    status: str
    release_numeric: int
    creo_release: str
    commands: dict[str, str]
    digest: str
    certification: dict | None

    def document(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "status": self.status,
            "release_numeric": self.release_numeric,
            "creo_release": self.creo_release,
            "digest": self.digest,
            "certification": self.certification,
        }


def command_digest(commands: dict[str, str]) -> str:
    """SHA-256 of the canonical command text a profile was measured with."""
    return hashlib.sha256(
        json.dumps(commands, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _library(root: Path | None) -> Path:
    return Path(root) if root is not None else ROOT


def _refuse_unknown_keys(value: dict, allowed: frozenset[str], where: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise PanelProfileError(f"{where} carries undeclared keys: {', '.join(unknown)}")


def _read_json(path: Path, where: str) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PanelProfileError(f"{where} is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PanelProfileError(f"{where} cannot be read as JSON: {path} ({exc})") from exc
    if not isinstance(loaded, dict):
        raise PanelProfileError(f"{where} must be a JSON object: {path}")
    return loaded


def _digest_shape(value: object, where: str) -> str:
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise PanelProfileError(f"{where} must be a 64-character hex digest")
    return text


def _commands(raw: object, where: str) -> dict[str, str]:
    if not isinstance(raw, dict) or not raw:
        raise PanelProfileError(f"{where}.commands must be a non-empty object of slot -> text")
    commands: dict[str, str] = {}
    for slot, text in raw.items():
        if not isinstance(slot, str) or not slot:
            raise PanelProfileError(f"{where}.commands has a non-string slot name")
        if not isinstance(text, str) or not text.strip():
            raise PanelProfileError(f"{where}.commands[{slot!r}] must be non-empty command text")
        commands[slot] = text
    missing = [slot for slot in COMMAND_SLOTS if slot not in commands]
    if missing:
        raise PanelProfileError(
            f"{where}.commands is missing {', '.join(missing)}; a panel profile must freeze all "
            f"of {', '.join(COMMAND_SLOTS)}, because the route refuses to improvise the part it "
            "was not recorded with"
        )
    if SELECT_PLACEHOLDER not in commands["select_command"]:
        raise PanelProfileError(
            f"{where}.commands['select_command'] must contain {SELECT_PLACEHOLDER}; the resident "
            "command is named at runtime, and a selection step that cannot name it would reopen "
            "the recorded screen-pick pause"
        )
    if "~ Command `" not in commands["select_command"]:
        # A bare placeholder substitutes to a bare command name, which the macro
        # engine ignores: three Creo 10 attempts consumed zero positions that way.
        raise PanelProfileError(
            f"{where}.commands['select_command'] must be the whole macro line "
            "~ Command `%MECHDOG_COMMAND%`;, not the bare placeholder; a command name without "
            "the ~ Command wrapper is not a macro step and silently does nothing"
        )
    return commands


def _certification(raw: object, base: Path, where: str, digest: str) -> dict:
    if not isinstance(raw, dict):
        raise PanelProfileError(f"{where}.certification must be an object")
    _refuse_unknown_keys(raw, CERTIFICATION_KEYS, f"{where}.certification")
    name = raw.get("file")
    if not isinstance(name, str) or not name.strip():
        raise PanelProfileError(f"{where}.certification.file must name an evidence file")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise PanelProfileError(
            f"{where}.certification.file must stay inside {CERTIFICATIONS}: {name!r}"
        )
    path = base / CERTIFICATIONS / relative
    if not path.is_file():
        raise PanelProfileError(
            f"{where}.certification.file is missing: {path}; a certified profile ships its "
            "acceptance record"
        )
    body = path.read_bytes()
    declared = _digest_shape(raw.get("digest"), f"{where}.certification.digest")
    if hashlib.sha256(body).hexdigest() != declared:
        raise PanelProfileError(
            f"{where}.certification.digest does not match {name}; a changed record invalidates "
            "the certification instead of being rewritten"
        )
    environment = raw.get("environment")
    if not isinstance(environment, dict) or not environment:
        raise PanelProfileError(f"{where}.certification.environment must record the test host")
    try:
        record = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PanelProfileError(
            f"{where}.certification is not a JSON record: {name} ({exc})"
        ) from exc
    if not isinstance(record, dict) or record.get("profile_digest") != digest:
        raise PanelProfileError(
            f"{where}.certification does not bind profile digest {digest}; code or commands "
            "changed after the acceptance run, so the profile is no longer certified"
        )
    return {
        "file": str(relative).replace("\\", "/"),
        "digest": declared,
        "environment": environment,
    }


def profiles(root: Path | None = None) -> list[PanelProfile]:
    """Read and verify every profile the manifest names, in manifest order."""
    base = _library(root)
    manifest_path = base / MANIFEST
    manifest = _read_json(manifest_path, "The panel profile manifest")
    if manifest.get("contract") != CONTRACT:
        raise PanelProfileError(
            f"{MANIFEST} declares contract {manifest.get('contract')!r}; this release reads "
            f"{CONTRACT!r}"
        )
    entries = manifest.get("profiles")
    if not isinstance(entries, list):
        raise PanelProfileError(f"{MANIFEST}.profiles must be a list")
    parsed: list[PanelProfile] = []
    seen: set[str] = set()
    for index, raw in enumerate(entries):
        where = f"{MANIFEST}.profiles[{index}]"
        if not isinstance(raw, dict):
            raise PanelProfileError(f"{where} must be an object")
        _refuse_unknown_keys(raw, PROFILE_KEYS, where)
        profile_id = raw.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise PanelProfileError(f"{where}.profile_id must be a non-empty string")
        if profile_id in seen:
            raise PanelProfileError(f"{MANIFEST} names profile {profile_id!r} more than once")
        seen.add(profile_id)
        status = raw.get("status")
        if status not in ("candidate", "certified"):
            raise PanelProfileError(f"{where}.status must be 'candidate' or 'certified'")
        release = raw.get("release_numeric")
        if type(release) is not int or release < 0:
            raise PanelProfileError(
                f"{where}.release_numeric must be the nonnegative integer the recording ran on"
            )
        creo_release = raw.get("creo_release")
        if not isinstance(creo_release, str) or not creo_release.strip():
            raise PanelProfileError(f"{where}.creo_release must name the measured Creo release")
        commands = _commands(raw.get("commands"), where)
        digest = _digest_shape(raw.get("digest"), f"{where}.digest")
        if command_digest(commands) != digest:
            raise PanelProfileError(
                f"{where}.digest does not match its frozen command text; re-record and re-certify "
                "instead of editing the digest"
            )
        certification = raw.get("certification")
        if status == "certified":
            certification = _certification(certification, base, where, digest)
        elif certification is not None:
            raise PanelProfileError(
                f"{where} is a candidate but carries a certification; mark it certified or drop "
                "the record instead of publishing an accepted profile as a candidate"
            )
        parsed.append(
            PanelProfile(
                profile_id=profile_id,
                status=status,
                release_numeric=release,
                creo_release=creo_release,
                commands=commands,
                digest=digest,
                certification=certification,
            )
        )
    return parsed


def find_profile(profile_id: str, root: Path | None = None) -> PanelProfile:
    entries = profiles(root)
    for profile in entries:
        if profile.profile_id == profile_id:
            return profile
    known = ", ".join(profile.profile_id for profile in entries) or "none"
    raise PanelProfileError(
        f"panel profile {profile_id!r} is not in {MANIFEST} (known: {known}); no native job "
        "was queued"
    )


def host_release(identity: object) -> int | None:
    """The Creo release this executor last reported, or None when nothing recorded it.

    A profile is measured on one release, so admission needs the host's own number
    rather than a guess from the Python environment. The worker's build-info does
    not carry it; the recorded surface_loft observation does, both at the top level
    and inside its evidence block.
    """
    if not isinstance(identity, dict):
        return None
    release = identity.get("release_numeric")
    if type(release) is int:
        return release
    features = identity.get("features")
    loft = features.get("surface_loft") if isinstance(features, dict) else None
    if not isinstance(loft, dict):
        return None
    release = loft.get("release_numeric")
    if type(release) is int:
        return release
    evidence = loft.get("evidence")
    release = evidence.get("release_numeric") if isinstance(evidence, dict) else None
    return release if type(release) is int else None


def certified_profile(root: Path | None = None, release_numeric: int | None = None) -> PanelProfile:
    """The profile normal clients may use, or a refusal that names why there is none.

    ``release_numeric`` prefers the profile measured on the release the host
    reported, so a library that later holds two certified releases never serves the
    wrong one. When none matches, the first certified profile is returned so
    admission reports the release mismatch by name instead of "no profile".
    """
    entries = profiles(root)
    certified = [profile for profile in entries if profile.status == "certified"]
    if release_numeric is not None:
        matching = [profile for profile in certified if profile.release_numeric == release_numeric]
        certified = matching or certified
    if certified:
        return certified[0]
    candidates = ", ".join(
        profile.profile_id for profile in entries if profile.status == "candidate"
    )
    raise PanelProfileError(
        "creation_route='resident_panel' has no certified UI profile for this release: "
        f"{MANIFEST} lists {'candidate(s) ' + candidates if candidates else 'no profiles'}. "
        "A profile becomes certified only after the documented target-host acceptance run; "
        f"a candidate is usable only by the development driver, which sets {CANDIDATE_ENV} for "
        "its own --candidate-profile run. Normal clients cannot select a candidate and no "
        "native job was queued. Keep the element_tree route for supported hosts."
    )


def candidate_ticket(environ: dict | None = None) -> dict | None:
    """The development driver's internal ticket, or None when the server is normal."""
    raw = (environ if environ is not None else os.environ).get(CANDIDATE_ENV)
    if raw is None or not raw.strip():
        return None
    try:
        ticket = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PanelProfileError(
            f"{CANDIDATE_ENV} is not valid JSON; a candidate run is refused rather than "
            f"guessed ({exc})"
        ) from exc
    if not isinstance(ticket, dict):
        raise PanelProfileError(f"{CANDIDATE_ENV} must carry a JSON object")
    _refuse_unknown_keys(ticket, CANDIDATE_KEYS, CANDIDATE_ENV)
    for key in CANDIDATE_REQUIRED:
        if not isinstance(ticket.get(key), str) or not ticket[key].strip():
            raise PanelProfileError(f"{CANDIDATE_ENV}.{key} must be a non-empty string")
    for key in CANDIDATE_OPTIONAL:
        if ticket.get(key) is not None:
            ticket[key] = _digest_shape(ticket[key], f"{CANDIDATE_ENV}.{key}")
    for key in CANDIDATE_INT_OPTIONAL:
        if ticket.get(key) is not None and type(ticket[key]) is not int:
            raise PanelProfileError(f"{CANDIDATE_ENV}.{key} must be an integer Creo release number")
    return ticket


def admit_for_request(
    identity: object,
    *,
    root: Path | None = None,
    environ: dict | None = None,
) -> dict:
    """Admit the profile this request may use: the ticket's, else the certified one."""
    ticket = candidate_ticket(environ)
    profile = (
        find_profile(ticket["profile_id"], root)
        if ticket
        else certified_profile(root, host_release(identity))
    )
    return admit(profile.profile_id, identity, root=root, environ=environ)


def _workspace(root: Path | None) -> str:
    return str(_library(root).resolve())


def admit(
    profile_id: str,
    identity: object,
    *,
    root: Path | None = None,
    environ: dict | None = None,
) -> dict:
    """Admit one profile for this request, or refuse before any native job exists.

    A certified profile needs nothing beyond its own verified evidence. A candidate
    profile additionally needs the driver ticket to match this workspace, this
    profile digest and — when the ticket names them — the worker, loader and payload
    digests of the executor that would run the job.

    Both modes compare the host's recorded Creo release with the release the profile
    was measured on: a mismatch always refuses, and a normal client refuses an
    unknown release too. The development driver may run a candidate while the host
    release is still unrecorded, because the test itself is what produces that
    observation; the admission record then says so instead of implying a match.
    """
    profile = find_profile(profile_id, root)
    ticket = candidate_ticket(environ)
    release = host_release(identity)
    unverified: list[str] = []
    if release is None:
        if ticket is None:
            raise PanelProfileError(
                f"panel profile {profile.profile_id!r} was measured on Creo "
                f"release_numeric={profile.release_numeric} ({profile.creo_release}), but this "
                "worker has no recorded host release, so the profile cannot be matched to it. "
                "No native job was queued. A certified profile is bound to one release; run a "
                "recorded job on this host first, or use the element_tree route."
            )
        unverified.append("host_release_numeric")
    elif release != profile.release_numeric:
        raise PanelProfileError(
            f"panel profile {profile.profile_id!r} was measured on Creo "
            f"release_numeric={profile.release_numeric} ({profile.creo_release}), but this host "
            f"reports release_numeric={release}. A profile is never re-used across releases; "
            "no native job was queued."
        )
    if ticket is not None and ticket.get("release_numeric") is not None:
        if ticket["release_numeric"] != profile.release_numeric:
            raise PanelProfileError(
                f"the candidate ticket was issued for release_numeric={ticket['release_numeric']}, "
                f"but profile {profile.profile_id!r} is measured on "
                f"{profile.release_numeric}; re-record the profile instead of reusing a ticket"
            )
        if release is not None and release != ticket["release_numeric"]:
            raise PanelProfileError(
                f"the candidate ticket was issued for release_numeric={ticket['release_numeric']}, "
                f"but this host reports {release}; no native job was queued"
            )
    if profile.status == "certified":
        return {
            "profile_id": profile.profile_id,
            "mode": "certified",
            "profile_digest": profile.digest,
            "release_numeric": profile.release_numeric,
            "creo_release": profile.creo_release,
            "host_release_numeric": release,
            "unverified_bindings": unverified,
            "certification": profile.certification,
            "candidate": None,
            # The frozen command text is what the job carries to the native route.
            # Admission is the only place that reads it, so the job cannot name a
            # command the profile was not measured with.
            "commands": dict(profile.commands),
            **{slot: profile.commands[slot] for slot in COMMAND_SLOTS},
        }
    if ticket is None:
        raise PanelProfileError(
            f"panel profile {profile.profile_id!r} is a candidate: it was never accepted on a "
            "target host, so only the development driver may use it and normal clients cannot. "
            f"Set {CANDIDATE_ENV} from the driver's --candidate-profile run, or use a certified "
            "profile. No native job was queued."
        )
    if ticket["profile_id"] != profile.profile_id:
        raise PanelProfileError(
            f"the candidate ticket is bound to profile {ticket['profile_id']!r}, not "
            f"{profile.profile_id!r}; one ticket never admits another profile"
        )
    if ticket["workspace"] != _workspace(root):
        raise PanelProfileError(
            f"the candidate ticket was issued for workspace {ticket['workspace']!r}, not "
            f"{_workspace(root)!r}; a ticket from another checkout does not admit this run"
        )
    if ticket["profile_digest"] != profile.digest:
        raise PanelProfileError(
            f"the candidate ticket names profile digest {ticket['profile_digest']}, but "
            f"{profile.profile_id!r} now has {profile.digest}; re-record the profile instead of "
            "reusing an older ticket"
        )
    if not isinstance(identity, dict) or identity.get("identity_status") != "verified":
        raise PanelProfileError(
            "a candidate panel run needs a verified worker build identity to bind the job to; "
            "the current worker has none, so no native job was queued"
        )
    unchecked: list[str] = []
    for key in CANDIDATE_OPTIONAL:
        expected = ticket.get(key)
        if not expected:
            continue
        observed = identity.get(key)
        if observed is None:
            # The build identity of the worker probe does not carry every digest
            # (the loader/payload pair is a deployment fact). The binding stays in
            # the admission record so the native side and the receipt can check it
            # against the executor that actually ran the job.
            unchecked.append(key)
            continue
        if observed != expected:
            raise PanelProfileError(
                f"the candidate ticket was issued for {key}={expected}, but the current worker "
                f"reports {observed}; rebuild the ticket against this executor"
            )
    return {
        "profile_id": profile.profile_id,
        "mode": "candidate",
        "profile_digest": profile.digest,
        "release_numeric": profile.release_numeric,
        "creo_release": profile.creo_release,
        "host_release_numeric": release,
        "unverified_bindings": unverified,
        "certification": None,
        "commands": dict(profile.commands),
        **{slot: profile.commands[slot] for slot in COMMAND_SLOTS},
        "candidate": {
            "run_id": ticket["run_id"],
            "workspace": ticket["workspace"],
            "bindings": {key: ticket[key] for key in CANDIDATE_OPTIONAL if ticket.get(key)},
            "unchecked_bindings": unchecked,
        },
    }
