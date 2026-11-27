"""Spec folder lookup (.flow/specs/, .flow/specs/open/, and .flow/specs/parked/) and path safety."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "flow"
sys.path.insert(0, str(ROOT / "skills" / "flow" / "scripts"))

from flowctl_tracker import spec_store as SS  # noqa: E402
from flowctl_tracker import status as S  # noqa: E402
from flowctl_tracker.lifecycle.helpers import (  # noqa: E402
    SPEC_SUBDIRS, leaf_is_safe, load_spec,
)
from flowctl_tracker.types import ErrorClass, Response, TrackerError  # noqa: E402


def _ok(body) -> Response:
    return Response(200, {}, json.dumps(body).encode(), 0.01)


def _write_spec(path: Path, spec_id: str, *, tracker_id: str = "",
                identifier: str = "", url: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"id: {spec_id}", f"title: {spec_id}"]
    if tracker_id or identifier:
        lines.append("tracker:")
        if tracker_id:
            lines.append(f'  id: "{tracker_id}"')
        if identifier:
            lines.append(f'  identifier: "{identifier}"')
        if url:
            lines.append(f'  url: "{url}"')
    lines.extend(["---", "", "## Acceptance Criteria", "", "- **R1:** Works.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class SpecFolderTests(unittest.TestCase):
    def setUp(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp = Path(td.name)
        self.flow = self.tmp / ".flow"
        self.specs = self.flow / "specs"
        self.specs.mkdir(parents=True)

    def test_spec_path_lookup_and_precedence(self) -> None:
        # Neither exists -> returns root path.
        self.assertEqual(
            SS.spec_path(self.flow, "missing-spec"),
            self.specs / "missing-spec.md",
        )

        # Only in open/ -> returns open/ path.
        open_file = _write_spec(self.specs / "open" / "only-open.md", "only-open")
        self.assertEqual(SS.spec_path(self.flow, "only-open"), open_file)

        # Only at root -> returns root path.
        root_file = _write_spec(self.specs / "only-root.md", "only-root")
        self.assertEqual(SS.spec_path(self.flow, "only-root"), root_file)

        # Both present -> root wins and nothing is raised.
        _write_spec(self.specs / "open" / "both-present.md", "both-present")
        both_root = _write_spec(self.specs / "both-present.md", "both-present")
        self.assertEqual(SS.spec_path(self.flow, "both-present"), both_root)

        # Only in parked/ -> returns parked/ path.
        parked_file = _write_spec(self.specs / "parked" / "only-parked.md", "only-parked")
        self.assertEqual(SS.spec_path(self.flow, "only-parked"), parked_file)

        # In open/ and parked/ -> open/ wins.
        _write_spec(self.specs / "parked" / "open-and-parked.md", "open-and-parked")
        open_wins = _write_spec(self.specs / "open" / "open-and-parked.md", "open-and-parked")
        self.assertEqual(SS.spec_path(self.flow, "open-and-parked"), open_wins)

        # In root, open/, and parked/ -> root wins.
        _write_spec(self.specs / "parked" / "all-three.md", "all-three")
        _write_spec(self.specs / "open" / "all-three.md", "all-three")
        root_wins = _write_spec(self.specs / "all-three.md", "all-three")
        self.assertEqual(SS.spec_path(self.flow, "all-three"), root_wins)

    def test_iter_spec_trackers_yields_from_all_folders(self) -> None:
        _write_spec(
            self.specs / "finished-slug.md", "finished-slug",
            tracker_id="ID_ROOT", identifier="#10", url="https://example.test/10",
        )
        _write_spec(
            self.specs / "open" / "open-slug.md", "open-slug",
            tracker_id="ID_OPEN", identifier="#11", url="https://example.test/11",
        )
        _write_spec(
            self.specs / "parked" / "parked-slug.md", "parked-slug",
            tracker_id="ID_PARKED", identifier="#12", url="https://example.test/12",
        )
        # Duplicate ids across folders: root beats open beats parked.
        _write_spec(
            self.specs / "open" / "finished-slug.md", "finished-slug",
            tracker_id="ID_STALE", identifier="#99", url="https://example.test/99",
        )
        _write_spec(
            self.specs / "parked" / "open-slug.md", "open-slug",
            tracker_id="ID_PARKED_STALE", identifier="#98", url="https://example.test/98",
        )

        found = list(SS.iter_spec_trackers(self.flow))
        self.assertEqual(
            [(sid, tr.get("id")) for sid, tr in found],
            [
                ("finished-slug", "ID_ROOT"),
                ("open-slug", "ID_OPEN"),
                ("parked-slug", "ID_PARKED"),
            ],
        )

    def test_status_in_review_works_for_spec_in_open_folder(self) -> None:
        spec_id = "eng-42-add-widget"
        node_id = "I_kwDOTestOpen42"
        (self.flow / "config.json").write_text(json.dumps({
            "tracker": {
                "type": "github",
                "resolved": {"destination": {"owner": "o", "repo": "r"}},
            },
        }), encoding="utf-8")
        open_file = _write_spec(
            self.specs / "open" / f"{spec_id}.md", spec_id,
            tracker_id=node_id, identifier="#42", url="https://github.com/o/r/issues/42",
        )

        loaded = load_spec(self.flow, spec_id)
        self.assertNotIsInstance(loaded, TrackerError)
        self.assertEqual(loaded[0], open_file)

        calls = []

        def fake_execute(req):
            calls.append(req.op)
            if req.op == "status-parent-read":
                return _ok({
                    "node_id": node_id, "number": 42, "state": "open",
                    "labels": [{"name": "status:in_progress"}],
                    "state_reason": None,
                })
            if req.op == "merge-evidence":
                return _ok([{"state": "OPEN", "number": 7}])
            if req.op == "status-label-rm":
                return Response(204, {}, b"", 0.01)
            if req.op in ("status-label-add", "status-label-readback"):
                return _ok([{"name": "status:in-review"}])
            if req.op == "status-set":
                return _ok({"node_id": node_id, "number": 42, "state": "open"})
            raise AssertionError(f"unexpected op {req.op!r}")

        payload_str, code = S.run(
            self.flow, spec_id=spec_id, to="in_review",
            branch="feat/eng-42-add-widget", execute=fake_execute,
        )
        self.assertEqual(code, 0, payload_str)
        payload = json.loads(payload_str)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["kind"], "applied")
        self.assertIn("status-label-rm", calls)
        self.assertIn("status-label-add", calls)
        self.assertTrue(open_file.is_file())
        self.assertFalse((self.specs / f"{spec_id}.md").exists())

    def test_safety_check_allows_open_and_rejects_nested_or_outside(self) -> None:
        self.assertIsNone(
            leaf_is_safe(self.specs, self.specs / "a.md", allowed_subdirs=SPEC_SUBDIRS),
        )
        self.assertIsNone(
            leaf_is_safe(self.specs, self.specs / "open" / "a.md", allowed_subdirs=SPEC_SUBDIRS),
        )
        self.assertIsNone(
            leaf_is_safe(self.specs, self.specs / "parked" / "a.md", allowed_subdirs=SPEC_SUBDIRS),
        )

        for bad in (
            self.specs / "open" / "nested" / "x.md",
            self.specs / "parked" / "nested" / "x.md",
            self.specs / "other" / "x.md",
            self.specs / ".." / "victim.md",
            self.tmp / "outside.md",
        ):
            with self.subTest(bad=str(bad)):
                err = leaf_is_safe(self.specs, bad, allowed_subdirs=SPEC_SUBDIRS)
                self.assertIsInstance(err, TrackerError)
                self.assertIs(err.cls, ErrorClass.INVALID_INPUT)
                self.assertEqual(err.subtype, "path")

        outside = self.tmp / "outside_dir"
        outside.mkdir()
        try:
            (self.specs / "open").symlink_to(outside, target_is_directory=True)
            (self.specs / "parked").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        for sub in ("open", "parked"):
            with self.subTest(symlink_subdir=sub):
                err = leaf_is_safe(self.specs, self.specs / sub / "x.md", allowed_subdirs=SPEC_SUBDIRS)
                self.assertIsInstance(err, TrackerError)
                self.assertIs(err.cls, ErrorClass.INVALID_INPUT)
                self.assertEqual(err.subtype, "path")


if __name__ == "__main__":
    unittest.main()
