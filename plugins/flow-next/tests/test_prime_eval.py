"""Framework tests for the `flowctl prime classify` emitter (fn-92.4).

Covers the deterministic Phase-0.5 classification FRAMEWORK: the command/schema
skeleton, the per-collector completeness-diagnostics envelope (resolution 21b),
axes 1-4 raw signals + Axis-5 shape markers + assessment_scope, blob-ID
content-hash dedup (`git ls-files -s`, no content read), per-collector budget
scaffolding, the byte-identical dual-copy invariant, and a live-subcommand
smoke.

The substance-grep collectors, redaction hardening, the full synthetic-fixture
eval corpus (R19), and perf accounting land in fn-92.13 — NOT here.

unittest (not pytest); 3-OS portable; no bare `timeout` binary; POSIX-only
shell-outs.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
TESTS_DIR = HERE.parent
PLUGIN_DIR = TESTS_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
DOGFOOD_FLOWCTL_PY = REPO_ROOT / ".flow" / "bin" / "flowctl.py"
CLASSIFICATION_MD = PLUGIN_DIR / "skills" / "flow-next-prime" / "classification.md"


def _load_flowctl() -> Any:
    spec = importlib.util.spec_from_file_location("flowctl_prime_under_test", FLOWCTL_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _pinned_env() -> dict:
    env = dict(os.environ)
    env["GIT_AUTHOR_DATE"] = "2026-01-01T00:00:00Z"
    env["GIT_COMMITTER_DATE"] = "2026-01-01T00:00:00Z"
    env["GIT_AUTHOR_NAME"] = "t"
    env["GIT_AUTHOR_EMAIL"] = "t@example.com"
    env["GIT_COMMITTER_NAME"] = "t"
    env["GIT_COMMITTER_EMAIL"] = "t@example.com"
    return env


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=_pinned_env(),
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")


def _write(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _commit_all(repo: Path, msg: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)


# ── Schema-shape / envelope framework tests (in-process) ──────────────────────


class SchemaShapeTestCase(unittest.TestCase):
    """The emitted payload matches the pinned schema field structure."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "acme-api"
        _init_repo(self.repo)
        _write(self.repo, "src/main.py", "def main():\n    return 1\n")
        _write(self.repo, "README.md", "# acme-api\n")
        _commit_all(self.repo, "seed")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_top_level_field_order_and_presence(self) -> None:
        payload = self.flowctl._prime_classify(self.repo)
        self.assertEqual(
            list(payload.keys()),
            ["schema_version", "assessment_scope", "axes", "shape_markers", "collectors"],
        )
        self.assertEqual(payload["schema_version"], self.flowctl.PRIME_SCHEMA_VERSION)

    def test_axes_structure(self) -> None:
        axes = self.flowctl._prime_classify(self.repo)["axes"]
        self.assertEqual(list(axes.keys()), ["lifecycle", "topology", "size", "stacks"])
        for key in ("value", "confidence", "signals", "evidence"):
            self.assertIn(key, axes["lifecycle"], key)
        self.assertIn("monorepo", axes["topology"])
        self.assertIn("constellation_member", axes["topology"])
        self.assertIsInstance(axes["stacks"], list)

    def test_topology_two_independent_bits(self) -> None:
        topo = self.flowctl._prime_classify(self.repo)["axes"]["topology"]
        for bit in ("monorepo", "constellation_member"):
            self.assertIn("value", topo[bit], bit)
            self.assertIn("confidence", topo[bit], bit)
            self.assertIn("signals", topo[bit], bit)
        self.assertIn("tier", topo["constellation_member"])
        self.assertIn("workspace_parent", topo["constellation_member"])

    def test_shape_markers_are_raw_markers_only(self) -> None:
        markers = self.flowctl._prime_classify(self.repo)["shape_markers"]
        self.assertEqual(
            set(markers.keys()),
            {"bin_exports", "framework_markers", "serve_health_code", "desktop_markers", "prose_ratio"},
        )
        # Axis 5 shape VALUES are never resolved by the emitter — only markers.
        self.assertNotIn("shape", self.flowctl._prime_classify(self.repo)["axes"])

    def test_every_collector_carries_full_envelope(self) -> None:
        collectors = self.flowctl._prime_classify(self.repo)["collectors"]
        self.assertTrue(collectors)
        for col in collectors:
            self.assertEqual(
                set(col.keys()),
                {
                    "name",
                    "status",
                    "complete",
                    "sampled",
                    "truncated",
                    "cap_hit",
                    "errors",
                    "tool",
                    "operations",
                },
                col.get("name"),
            )
            self.assertIn(col["status"], ("ok", "error"))
            self.assertIsInstance(col["operations"], int)

    def test_assessment_scope_repository(self) -> None:
        scope = self.flowctl._prime_classify(self.repo)["assessment_scope"]
        self.assertEqual(scope["value"], "repository")
        self.assertEqual(scope["confidence"], "high")


# ── Confidence ceiling (resolution 21b) ───────────────────────────────────────


class ConfidenceCeilingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def test_complete_collector_keeps_base(self) -> None:
        c = self.flowctl._PrimeCollector("x")
        self.assertEqual(self.flowctl._prime_cap_confidence("high", c), "high")

    def test_sampled_caps_to_medium(self) -> None:
        c = self.flowctl._PrimeCollector("x")
        c.note_sampled()
        self.assertEqual(self.flowctl._prime_cap_confidence("high", c), "medium")

    def test_truncated_caps_to_medium(self) -> None:
        c = self.flowctl._PrimeCollector("x")
        c.note_truncated()
        self.assertEqual(self.flowctl._prime_cap_confidence("high", c), "medium")

    def test_cap_hit_caps_to_medium(self) -> None:
        c = self.flowctl._PrimeCollector("x", budget=1)
        c.op()
        c.op()  # exceeds budget → cap_hit
        self.assertTrue(c.cap_hit)
        self.assertEqual(self.flowctl._prime_cap_confidence("high", c), "medium")

    def test_error_forces_low(self) -> None:
        c = self.flowctl._PrimeCollector("x")
        c.fail("boom")
        self.assertEqual(self.flowctl._prime_cap_confidence("high", c), "low")

    def test_budget_scaffolding_present(self) -> None:
        # Per-collector budgets are wired (a real cap, not None) on the bounded
        # collectors — regression guard for the budget-scaffolding acceptance.
        self.assertIsInstance(self.flowctl._PRIME_MAX_TRACKED_FILES, int)
        self.assertIsInstance(self.flowctl._PRIME_MAX_LOC_FILES, int)


# ── Blob-ID content-hash dedup (no content read) ──────────────────────────────


class BlobDedupTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.tmp / "repo"
        _init_repo(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_identical_files_deduped_via_blob_id(self) -> None:
        # Two byte-identical files share a git blob SHA → the duplicate is
        # dropped without any content read, and hash-duplicate is recorded.
        dup = "line1\nline2\nline3\n"
        _write(self.repo, "a/copy1.py", dup)
        _write(self.repo, "b/copy2.py", dup)
        _write(self.repo, "unique.py", "x = 1\n")
        _commit_all(self.repo, "seed")
        payload = self.flowctl._prime_classify(self.repo)
        size = payload["axes"]["size"]
        self.assertIn("hash-duplicate", size["exclusions_applied"])
        # 3 tracked files, 1 is a content duplicate → 2 unique.
        self.assertEqual(size["files"], 2)

    def test_staged_parse_returns_blob_and_path_no_read(self) -> None:
        _write(self.repo, "x.py", "y = 2\n")
        _commit_all(self.repo, "seed")
        col = self.flowctl._PrimeCollector("inventory")
        staged, truncated = self.flowctl._prime_parse_ls_files_staged(self.repo, col)
        self.assertFalse(truncated)
        self.assertEqual(len(staged), 1)
        sha, path = staged[0]
        self.assertEqual(path, "x.py")
        self.assertRegex(sha, r"^[0-9a-f]{40}$")


# ── Path exclusions ───────────────────────────────────────────────────────────


class ExclusionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def test_tool_managed_dirs_excluded(self) -> None:
        self.assertEqual(self.flowctl._prime_exclusion_category(".flow/bin/flowctl.py"), "tool-managed")
        self.assertEqual(self.flowctl._prime_exclusion_category(".claude/x.md"), "tool-managed")

    def test_vendor_excluded(self) -> None:
        self.assertEqual(self.flowctl._prime_exclusion_category("node_modules/foo/index.js"), "vendored")
        self.assertEqual(self.flowctl._prime_exclusion_category("gen/service_pb2.py"), "vendored")

    def test_fixtures_and_agent_state_excluded(self) -> None:
        self.assertEqual(self.flowctl._prime_exclusion_category("tests/fixtures/x.json"), "fixtures")
        self.assertEqual(self.flowctl._prime_exclusion_category("plans/roadmap.md"), "agent-state")

    def test_source_not_excluded(self) -> None:
        self.assertIsNone(self.flowctl._prime_exclusion_category("src/app/main.py"))

    def test_own_tooling_never_pollutes_classification(self) -> None:
        # A repo whose ONLY tracked file lives under .flow/ must not report that
        # as its stack / LOC — prime polluting its own classification is the
        # most embarrassing failure (classification.md Axis 3).
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "repo"
            _init_repo(repo)
            _write(repo, ".flow/bin/flowctl.py", "x = 1\n" * 500)
            _write(repo, "app.ts", "export const a = 1\n")
            _commit_all(repo, "seed")
            payload = self.flowctl._prime_classify(repo)
            self.assertIn("tool-managed", payload["axes"]["size"]["exclusions_applied"])
            self.assertEqual(payload["axes"]["size"]["files"], 1)  # only app.ts
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ── Lifecycle axis ─────────────────────────────────────────────────────────────


class LifecycleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def test_greenfield_fresh_repo(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "fresh"
            _init_repo(repo)
            _write(repo, "index.js", "console.log(1)\n")
            _commit_all(repo, "init")
            life = self.flowctl._prime_classify(repo)["axes"]["lifecycle"]
            self.assertEqual(life["value"], "greenfield")
            self.assertEqual(life["signals"]["tags"], 0)
            self.assertFalse(life["signals"]["ci_config"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_unborn_head_is_greenfield_no_crash(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "unborn"
            _init_repo(repo)  # no commits
            payload = self.flowctl._prime_classify(repo)
            life = payload["axes"]["lifecycle"]
            self.assertEqual(life["signals"]["commit_count"], 0)
            self.assertEqual(life["value"], "greenfield")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_ci_and_lockfile_push_to_hybrid_or_brownfield(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "young-real"
            _init_repo(repo)
            _write(repo, "index.js", "console.log(1)\n")
            _write(repo, ".github/workflows/ci.yml", "name: ci\n")
            _write(repo, "package-lock.json", "{}\n")
            _commit_all(repo, "init")
            life = self.flowctl._prime_classify(repo)["axes"]["lifecycle"]
            # Young (1 commit) but CI + lockfile present → signals disagree.
            self.assertIn(life["value"], ("hybrid", "brownfield"))
            self.assertTrue(life["signals"]["ci_config"])
            self.assertTrue(life["signals"]["lockfile"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ── Topology axis ──────────────────────────────────────────────────────────────


class TopologyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def test_monorepo_detected_from_workspace_config(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "mono"
            _init_repo(repo)
            _write(repo, "pnpm-workspace.yaml", "packages:\n  - 'packages/*'\n")
            _write(repo, "packages/a/index.ts", "export const a = 1\n")
            _commit_all(repo, "seed")
            mono = self.flowctl._prime_classify(repo)["axes"]["topology"]["monorepo"]
            self.assertTrue(mono["value"])
            self.assertIn("pnpm-workspace.yaml", mono["signals"]["workspace_config"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_worktree_sibling_excluded_from_constellation(self) -> None:
        # A sibling whose `.git` is a FILE (gitdir: pointer) resolves to the
        # SAME repo — a worktree, not a constellation sibling (R19 edge case).
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            parent = tmp / "workspace"
            parent.mkdir()
            repo = parent / "proj"
            _init_repo(repo)
            _write(repo, "a.py", "x = 1\n")
            _commit_all(repo, "seed")
            # Real worktree sibling (its .git is a file).
            wt = parent / "proj-wt"
            _git(repo, "worktree", "add", "-q", str(wt))
            self.assertTrue((wt / ".git").is_file())
            self_dir = repo.resolve()
            siblings, worktrees = self.flowctl._prime_sibling_git_dirs(parent, self_dir)
            self.assertGreaterEqual(worktrees, 1)
            self.assertNotIn("proj-wt", siblings)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_workspace_parent_dampener(self) -> None:
        # A parent holding many git dirs is a developer WORKSPACE — shared-org
        # is meaningless there and must not auto-confirm a constellation.
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            parent = tmp / "work"
            parent.mkdir()
            repo = parent / "solo"
            _init_repo(repo)
            _write(repo, "a.py", "x = 1\n")
            _commit_all(repo, "seed")
            # 22 sibling git dirs → over the >20 dampener threshold.
            for i in range(22):
                sib = parent / f"other{i}"
                _init_repo(sib)
            con = self.flowctl._prime_classify(repo)["axes"]["topology"]["constellation_member"]
            self.assertTrue(con["workspace_parent"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ── Stacks + shape markers ─────────────────────────────────────────────────────


class StacksAndShapeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def test_stack_is_manifest_gated(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "py"
            _init_repo(repo)
            _write(repo, "pyproject.toml", "[project]\nname='x'\n")
            _write(repo, "src/app.py", "x = 1\n")
            _commit_all(repo, "seed")
            stacks = self.flowctl._prime_classify(repo)["axes"]["stacks"]
            names = {s["name"] for s in stacks}
            self.assertIn("Python", names)
            for s in stacks:
                self.assertIn("manifest", s)
                self.assertIn("loc_share", s)
                self.assertIn("subproject", s)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bin_export_marker_emitted(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "cli"
            _init_repo(repo)
            _write(repo, "package.json", json.dumps({"name": "cli", "bin": {"cli": "index.js"}}))
            _write(repo, "index.js", "console.log(1)\n")
            _commit_all(repo, "seed")
            markers = self.flowctl._prime_classify(repo)["shape_markers"]
            self.assertIn("package.json bin", markers["bin_exports"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ── Assessment scope edge cases ────────────────────────────────────────────────


class AssessmentScopeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.flowctl = _load_flowctl()

    def test_workspace_member_when_below_toplevel(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "mono"
            _init_repo(repo)
            _write(repo, "packages/pkg-a/index.ts", "export const a = 1\n")
            _commit_all(repo, "seed")
            member_dir = repo / "packages" / "pkg-a"
            scope = self.flowctl._prime_classify(member_dir)["assessment_scope"]
            self.assertEqual(scope["value"], "workspace-member")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_non_git_home_base_no_crash(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            home = tmp / "home"
            home.mkdir()
            # Two child git repos, no own manifest → constellation home base.
            for name in ("svc-a", "svc-b"):
                _init_repo(home / name)
            payload = self.flowctl._prime_classify(home)
            self.assertEqual(payload["assessment_scope"]["value"], "constellation-home-base")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ── Dual-copy invariant + live subcommand smoke ────────────────────────────────


class DualCopyInvariantTestCase(unittest.TestCase):
    """The repo dogfoods a BYTE-IDENTICAL `.flow/bin/flowctl.py`; the emitter
    MUST land in BOTH copies or the live `.flow/bin/flowctl` runs stale code."""

    def test_two_copies_are_byte_identical(self) -> None:
        self.assertEqual(
            FLOWCTL_PY.read_bytes(),
            DOGFOOD_FLOWCTL_PY.read_bytes(),
            "scripts/flowctl.py and .flow/bin/flowctl.py must be byte-identical",
        )

    def test_both_copies_carry_emitter(self) -> None:
        for path in (FLOWCTL_PY, DOGFOOD_FLOWCTL_PY):
            text = path.read_text(encoding="utf-8")
            self.assertIn("def cmd_prime_classify", text, str(path))
            self.assertIn("def _prime_classify", text, str(path))
            self.assertIn("def _prime_parse_ls_files_staged", text, str(path))

    def test_schema_contract_is_pinned_in_classification_md(self) -> None:
        # Guard the source-of-truth link: the emitter implements the pinned
        # schema, so the contract file must exist and carry the schema block.
        self.assertTrue(CLASSIFICATION_MD.is_file())
        text = CLASSIFICATION_MD.read_text(encoding="utf-8")
        self.assertIn("flowctl prime classify --json", text)
        self.assertIn('"schema_version"', text)

    @unittest.skipIf(
        sys.platform == "win32",
        "live subcommand-resolution subprocess is Windows-runner fragile; the "
        "byte-identical + emitter-present checks cover the dual-copy invariant.",
    )
    def test_live_bin_resolves_classify_subcommand(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(DOGFOOD_FLOWCTL_PY), "prime", "classify", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--json", proc.stdout)
        self.assertIn("root", proc.stdout)

    @unittest.skipIf(
        sys.platform == "win32",
        "live subcommand subprocess is Windows-runner fragile.",
    )
    def test_live_json_emits_pinned_schema(self) -> None:
        tmp = Path(tempfile.mkdtemp()).resolve()
        try:
            repo = tmp / "repo"
            _init_repo(repo)
            _write(repo, "main.py", "x = 1\n")
            _commit_all(repo, "seed")
            proc = subprocess.run(
                [sys.executable, str(DOGFOOD_FLOWCTL_PY), "prime", "classify", str(repo), "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["schema_version"], 1)
            self.assertIn("assessment_scope", payload)
            self.assertIn("axes", payload)
            self.assertIn("collectors", payload)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
