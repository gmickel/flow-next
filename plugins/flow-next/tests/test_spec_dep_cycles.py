"""Cycle detection for dependencies between specs.

`spec add-dep` refuses an edge that closes a cycle and names the path,
`validate --all` lists cycles already on disk, and the `/flow-next:deps` phase
fence names the cause of every deadlocked spec.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling test helpers
from chain_fixture_support import fence
from flowctl_test_support import FLOWCTL_CMD

DEPS_SKILL = Path(__file__).resolve().parents[1] / "skills" / "flow-next-deps" / "SKILL.md"


class SpecDepCycleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=self.tmpdir, check=True, capture_output=True)
        self._run("init", "--json")
        self.ids = {name: self._spec(name) for name in "abcde"}

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*FLOWCTL_CMD, *args], cwd=self.tmpdir, capture_output=True, text=True
        )

    def _spec(self, title: str) -> str:
        res = self._run("spec", "create", "--title", title, "--json")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return json.loads(res.stdout)["id"]

    def _add(self, spec: str, dep: str) -> subprocess.CompletedProcess[str]:
        return self._run("spec", "add-dep", self.ids[spec], self.ids[dep], "--json")

    def _deps(self, spec: str) -> list[str]:
        path = self.tmpdir / ".flow" / "specs" / f"{self.ids[spec]}.json"
        return json.loads(path.read_text(encoding="utf-8")).get("depends_on_epics", [])

    def _write_deps(self, spec: str, *deps: str) -> None:
        """Write edges straight to disk, as an older flowctl could."""
        path = self.tmpdir / ".flow" / "specs" / f"{self.ids[spec]}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["depends_on_epics"] = [self.ids[d] for d in deps]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _path(self, *names: str) -> list[str]:
        return [self.ids[n] for n in names]

    def assertCycleRefused(self, res, cycle: list[str]) -> None:
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        out = json.loads(res.stdout)
        self.assertFalse(out["success"])
        self.assertEqual(out["code"], "dependency_cycle")
        self.assertEqual(out["cycle"], cycle)
        self.assertIn(" -> ".join(cycle), out["error"])

    # ---- R1: refusal at the point an edge is added ----
    def test_self_dependency_is_a_cycle_of_one(self) -> None:
        self.assertCycleRefused(self._add("a", "a"), self._path("a", "a"))
        self.assertEqual(self._deps("a"), [])

    def test_two_spec_cycle_is_refused_and_disk_unchanged(self) -> None:
        self.assertEqual(self._add("a", "b").returncode, 0)
        self.assertCycleRefused(self._add("b", "a"), self._path("b", "a", "b"))
        self.assertEqual(self._deps("b"), [])
        self.assertEqual(self._deps("a"), [self.ids["b"]])

    def test_three_spec_cycle_names_the_full_path(self) -> None:
        self._add("a", "b")
        self._add("b", "c")
        self.assertCycleRefused(self._add("c", "a"), self._path("c", "a", "b", "c"))
        self.assertEqual(self._deps("c"), [])

    def test_text_mode_prints_the_path_to_stderr(self) -> None:
        self._add("a", "b")
        res = self._run("spec", "add-dep", self.ids["b"], self.ids["a"])
        self.assertEqual(res.returncode, 1)
        self.assertIn(f"Dependency cycle: {self.ids['b']} -> {self.ids['a']} -> {self.ids['b']}", res.stderr)

    def test_unknown_dependency_keeps_its_error(self) -> None:
        res = self._run("spec", "add-dep", self.ids["a"], "fn-999", "--json")
        self.assertEqual(res.returncode, 1)
        self.assertNotIn("code", json.loads(res.stdout))

    # ---- R2: no false positives ----
    def test_diamond_and_long_chain_pass(self) -> None:
        for spec, dep in (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")):
            self.assertEqual(self._add(spec, dep).returncode, 0)
        chain = [self._spec(f"link {i}") for i in range(13)]
        for spec, dep in zip(chain, chain[1:], strict=False):
            res = self._run("spec", "add-dep", spec, dep, "--json")
            self.assertEqual(res.returncode, 0, res.stdout)
        self.assertEqual(self._deps("a"), self._path("b", "c"))

    def test_existing_edge_stays_idempotent(self) -> None:
        self._add("a", "b")
        res = self._add("a", "b")
        self.assertEqual(res.returncode, 0)
        self.assertTrue(json.loads(res.stdout)["success"])

    # ---- R3: whole-graph check over what is already on disk ----
    def test_validate_all_lists_each_cycle_once(self) -> None:
        self._write_deps("a", "b")
        self._write_deps("b", "c")
        self._write_deps("c", "a")
        self._write_deps("d", "e")
        self._write_deps("e", "d")
        res = self._run("validate", "--all", "--json")
        self.assertEqual(res.returncode, 1)
        out = json.loads(res.stdout)
        self.assertFalse(out["valid"])
        self.assertEqual(
            sorted(out["spec_cycles"]),
            sorted([self._path("a", "b", "c", "a"), self._path("d", "e", "d")]),
        )
        cycle_errors = [e for e in out["root_errors"] if e.startswith("Spec dependency cycle: ")]
        self.assertEqual(len(cycle_errors), 2)

        text = self._run("validate", "--all")
        self.assertEqual(text.returncode, 1)
        self.assertIn(f"Spec dependency cycle: {' -> '.join(self._path('d', 'e', 'd'))}", text.stdout)

    def test_validate_all_without_cycles_reports_none(self) -> None:
        self._add("a", "b")
        out = json.loads(self._run("validate", "--all", "--json").stdout)
        self.assertEqual(out["spec_cycles"], [])
        self.assertFalse([e for e in out["root_errors"] if "cycle" in e])


@unittest.skipIf(os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"),
                 "needs bash and jq")
class DepsPhaseFenceTestCase(unittest.TestCase):
    """R5/R6: the real `/flow-next:deps` phase fence over a cached gather."""

    def phases(self, specs: list[dict]) -> dict:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        specs_file = tmp / "specs.json"
        specs_file.write_text(json.dumps(specs), encoding="utf-8")
        res = subprocess.run(
            ["bash", "-c", fence(DEPS_SKILL, "deps-phases")],
            env={**os.environ, "SPECS_FILE": str(specs_file)},
            capture_output=True, text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    @staticmethod
    def spec(spec_id: str, *deps: str, status: str = "open") -> dict:
        return {"id": spec_id, "title": spec_id, "status": status, "deps": list(deps)}

    def test_chain_deeper_than_ten_is_phased(self) -> None:
        chain = [self.spec("s0")] + [self.spec(f"s{i}", f"s{i - 1}") for i in range(1, 14)]
        out = self.phases(chain)
        self.assertEqual(out["deadlocked"], [])
        self.assertEqual(len(out["phases"]), 14)

    def test_each_deadlocked_spec_names_its_cause(self) -> None:
        out = self.phases([
            self.spec("done", status="done"),
            self.spec("ok", "done"),
            self.spec("a", "b"),
            self.spec("b", "a"),
            self.spec("lost", "gone"),
            self.spec("down", "a"),
            self.spec("both", "both2", "gone"),
            self.spec("both2", "both"),
        ])
        self.assertEqual([s["id"] for p in out["phases"] for s in p["specs"]], ["ok"])
        by_id = {d["id"]: d for d in out["deadlocked"]}
        self.assertEqual(by_id["a"], {"id": "a", "status": "open", "unresolved_deps": ["b"],
                                      "cause": "cycle", "cycle": ["a", "b", "a"]})
        self.assertEqual(by_id["b"]["cycle"], ["b", "a", "b"])
        self.assertEqual(by_id["lost"], {"id": "lost", "status": "open",
                                         "unresolved_deps": ["gone"], "cause": "missing"})
        self.assertEqual(by_id["down"], {"id": "down", "status": "open",
                                         "unresolved_deps": ["a"], "cause": "blocked"})
        self.assertEqual(by_id["both"]["cause"], "cycle")
        self.assertIn("gone", by_id["both"]["unresolved_deps"])


if __name__ == "__main__":
    unittest.main()
