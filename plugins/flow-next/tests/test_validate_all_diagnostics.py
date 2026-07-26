"""Black-box diagnostics coverage for ``flowctl validate --all``.

The JSON and text renderers must expose the same repository-level failures.
In particular, every error counted by ``total_errors`` must be discoverable in
``root_errors`` or a per-spec ``errors`` collection. Duplicate ordinals with
distinct full ids are top-level ``root_warnings`` (fn-134.2 / R13), counted in
``total_warnings`` and visible in both renderers.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"
# Live fn-122 pair in this repo (ids never change; R13 regression target).
LIVE_FN122_A = "fn-122-flowctl-hardening-and-performance-completion-sweep"
LIVE_FN122_B = "fn-122-harden-verdict-graduate-recurring"
REPO_ROOT = HERE.parents[2]


class ValidateAllDiagnosticsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.tmpdir,
            check=True,
            capture_output=True,
            text=True,
        )
        self._run("init", "--json", check=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(FLOWCTL_PY), *args],
            cwd=self.tmpdir,
            check=check,
            capture_output=True,
            text=True,
        )

    def _create_native_spec(self, title: str) -> str:
        result = self._run(
            "spec", "create", "--title", title, "--json", check=True
        )
        return json.loads(result.stdout)["id"]

    def _create_tracker_spec(self, title: str, identifier: str) -> str:
        result = self._run(
            "spec",
            "create",
            "--title",
            title,
            "--tracker-first",
            "--tracker-identifier",
            identifier,
            "--json",
            check=True,
        )
        return json.loads(result.stdout)["id"]

    def _rename_spec(self, old_id: str, new_id: str) -> None:
        specs_dir = self.tmpdir / ".flow" / "specs"
        old_json = specs_dir / f"{old_id}.json"
        new_json = specs_dir / f"{new_id}.json"
        payload = json.loads(old_json.read_text(encoding="utf-8"))
        payload["id"] = new_id
        new_json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        old_json.unlink()
        (specs_dir / f"{old_id}.md").rename(specs_dir / f"{new_id}.md")

    def _create_collision(self, number: int, *slugs: str) -> list[str]:
        old_ids = [self._create_native_spec(slug.title()) for slug in slugs]
        new_ids = [f"fn-{number}-{slug}" for slug in slugs]
        for old_id, new_id in zip(old_ids, new_ids):
            self._rename_spec(old_id, new_id)
        return new_ids

    @staticmethod
    def _discoverable_error_count(payload: dict) -> int:
        return len(payload["root_errors"]) + sum(
            len(spec["errors"]) for spec in payload["specs"]
        )

    @staticmethod
    def _discoverable_warning_count(payload: dict) -> int:
        return len(payload.get("root_warnings", [])) + sum(
            len(spec.get("warnings") or []) for spec in payload["specs"]
        )

    def test_collision_json_and_text_share_actionable_diagnostic(self) -> None:
        """Duplicate ordinal is a root_warning, not a root_error (R13)."""
        self._create_collision(91, "beta", "alpha")
        expected = (
            "Spec ID collision: fn-91 used by multiple specs: "
            "fn-91-alpha, fn-91-beta"
        )

        json_result = self._run("validate", "--all", "--json")
        self.assertEqual(json_result.returncode, 0)
        payload = json.loads(json_result.stdout)
        self.assertTrue(payload["success"])
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["root_errors"], [])
        self.assertEqual(payload["root_warnings"], [expected])
        self.assertEqual(payload["total_errors"], 0)
        self.assertEqual(payload["total_warnings"], 1)
        self.assertEqual(
            payload["total_warnings"], self._discoverable_warning_count(payload)
        )
        self.assertEqual(
            payload["total_errors"], self._discoverable_error_count(payload)
        )

        text_result = self._run("validate", "--all")
        self.assertEqual(text_result.returncode, 0)
        self.assertIn("Valid: True", text_result.stdout)
        self.assertIn("Warnings:", text_result.stdout)
        self.assertIn(expected, text_result.stdout)
        self.assertNotIn("  Errors:", text_result.stdout)

    def test_multiple_collisions_are_sorted_and_tracker_ids_do_not_collide(self) -> None:
        self._create_collision(91, "gamma", "alpha", "beta")
        self._create_collision(42, "zeta", "alpha")
        tracker_id = self._create_tracker_spec("Tracker peer", "WOR-91")

        result = self._run("validate", "--all", "--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["root_errors"], [])
        self.assertEqual(
            payload["root_warnings"],
            [
                "Spec ID collision: fn-42 used by multiple specs: "
                "fn-42-alpha, fn-42-zeta",
                "Spec ID collision: fn-91 used by multiple specs: "
                "fn-91-alpha, fn-91-beta, fn-91-gamma",
            ],
        )
        self.assertEqual(payload["total_errors"], 0)
        self.assertEqual(payload["total_warnings"], 2)
        self.assertEqual(
            payload["total_warnings"], self._discoverable_warning_count(payload)
        )
        self.assertIn(tracker_id, {spec["spec"] for spec in payload["specs"]})

    def test_root_and_spec_errors_remain_visible_alongside_collision(self) -> None:
        collision_ids = self._create_collision(91, "alpha", "beta")
        shutil.rmtree(self.tmpdir / ".flow" / "memory")
        (self.tmpdir / ".flow" / "specs" / f"{collision_ids[0]}.md").unlink()

        result = self._run("validate", "--all", "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertIn("Required directory missing: memory/", payload["root_errors"])
        # Collision is a warning, not mixed into root_errors.
        self.assertFalse(
            any(error.startswith("Spec ID collision:") for error in payload["root_errors"])
        )
        self.assertTrue(
            any(
                w.startswith("Spec ID collision: fn-91")
                for w in payload["root_warnings"]
            )
        )
        spec_errors = {
            spec["spec"]: spec["errors"] for spec in payload["specs"]
        }
        self.assertTrue(
            any(
                error.startswith("Spec markdown missing:")
                for error in spec_errors[collision_ids[0]]
            )
        )
        # 2 real errors (root + per-spec); collision is the 1 warning.
        self.assertEqual(payload["total_errors"], 2)
        self.assertEqual(payload["total_warnings"], 1)
        self.assertEqual(
            payload["total_errors"], self._discoverable_error_count(payload)
        )
        self.assertEqual(
            payload["total_warnings"], self._discoverable_warning_count(payload)
        )

    def test_clean_repository_preserves_success_contract(self) -> None:
        self._create_native_spec("Alpha")
        self._create_native_spec("Beta")

        json_result = self._run("validate", "--all", "--json")
        self.assertEqual(json_result.returncode, 0)
        payload = json.loads(json_result.stdout)
        self.assertTrue(payload["success"])
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["root_errors"], [])
        self.assertEqual(payload["root_warnings"], [])
        self.assertEqual(payload["total_errors"], 0)
        self.assertEqual(payload["total_warnings"], 0)
        self.assertEqual(payload["total_errors"], self._discoverable_error_count(payload))

        text_result = self._run("validate", "--all")
        self.assertEqual(text_result.returncode, 0)
        self.assertIn("Valid: True", text_result.stdout)
        self.assertNotIn("  Errors:", text_result.stdout)

    def test_live_fn122_pair_root_warnings_both_renderers(self) -> None:
        """R13: live fn-122 pair is a machine-readable warning in JSON + text.

        Recreates the two real slug names (ids never change) in a fixture so
        the suite is hermetic; shape matches the live store.
        """
        self._create_collision(
            122,
            "flowctl-hardening-and-performance-completion-sweep",
            "harden-verdict-graduate-recurring",
        )
        expected = (
            "Spec ID collision: fn-122 used by multiple specs: "
            f"{LIVE_FN122_A}, {LIVE_FN122_B}"
        )

        json_result = self._run("validate", "--all", "--json")
        self.assertEqual(json_result.returncode, 0)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["root_errors"], [])
        self.assertIn(expected, payload["root_warnings"])
        self.assertGreaterEqual(payload["total_warnings"], 1)

        text_result = self._run("validate", "--all")
        self.assertEqual(text_result.returncode, 0)
        self.assertIn(expected, text_result.stdout)
        self.assertIn("Warnings:", text_result.stdout)

        # Also pin against the live repo store when present (same message shape).
        live_a = REPO_ROOT / ".flow" / "specs" / f"{LIVE_FN122_A}.json"
        live_b = REPO_ROOT / ".flow" / "specs" / f"{LIVE_FN122_B}.json"
        if live_a.exists() and live_b.exists():
            live = subprocess.run(
                [sys.executable, str(FLOWCTL_PY), "validate", "--all", "--json"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            live_payload = json.loads(live.stdout)
            self.assertTrue(
                any(
                    w.startswith("Spec ID collision: fn-122")
                    for w in live_payload.get("root_warnings", [])
                ),
                live_payload.get("root_warnings"),
            )
            self.assertFalse(
                any(
                    e.startswith("Spec ID collision: fn-122")
                    for e in live_payload.get("root_errors", [])
                )
            )


if __name__ == "__main__":
    unittest.main()
