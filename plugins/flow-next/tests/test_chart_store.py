"""Unit tests for shared allocator + crash-recoverable chart store (fn-135.1).

Covers: cross-kind allocation, chart/D-ID canonicalization, v1 envelopes,
no-clobber create, handled-failure rollback, and process-termination recovery
at named failpoints. No graph/frontier/claims (later tasks).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"

spec = importlib.util.spec_from_file_location("flowctl", ROOT / "scripts" / "flowctl.py")
flowctl = importlib.util.module_from_spec(spec)
sys.modules["flowctl"] = flowctl
spec.loader.exec_module(flowctl)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "chart-test@example.com")
    _git(repo, "config", "user.name", "chart-test")
    _git(repo, "config", "commit.gpgsign", "false")


def _init_flow(repo: Path) -> Path:
    r = subprocess.run(
        [sys.executable, str(FLOWCTL_PY), "init"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"flowctl init failed: {r.stderr}\n{r.stdout}")
    return repo / ".flow"


def _run_flowctl(cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    # Never inherit a failpoint from the parent test process unless intended.
    full_env.setdefault("FLOWCTL_CHART_FAILPOINT", "")
    if env is None or "FLOWCTL_CHART_FAILPOINT" not in env:
        full_env.pop("FLOWCTL_CHART_FAILPOINT", None)
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=full_env,
    )


def _write_spec(flow_dir: Path, stem: str) -> Path:
    d = flow_dir / "specs"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{stem}.json"
    path.write_text("{}", encoding="utf-8")
    return path


def _write_chart(flow_dir: Path, chart_id: str) -> Path:
    d = flow_dir / "charts"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{chart_id}.json"
    path.write_text(
        json.dumps({"id": chart_id, "title": "x", "status": "open", "decisions": []}),
        encoding="utf-8",
    )
    (d / f"{chart_id}.md").write_text(f"# {chart_id}\n", encoding="utf-8")
    return path


class TestChartCanonicalization(unittest.TestCase):
    def test_chart_id_accepts_fn_n(self) -> None:
        self.assertEqual(flowctl.canonicalize_chart_id("fn-12"), "fn-12")
        self.assertEqual(flowctl.canonicalize_chart_id(" FN-3 "), "fn-3")

    def test_chart_id_rejects_slug_and_empty(self) -> None:
        with self.assertRaises(flowctl.ChartError) as ctx:
            flowctl.canonicalize_chart_id("fn-12-slug")
        self.assertEqual(ctx.exception.error_class, "validation")
        with self.assertRaises(flowctl.ChartError):
            flowctl.canonicalize_chart_id("")
        with self.assertRaises(flowctl.ChartError):
            flowctl.canonicalize_chart_id("wor-1")

    def test_decision_id_full_and_bare(self) -> None:
        self.assertEqual(
            flowctl.canonicalize_decision_id("fn-5.D3"), "fn-5.D3"
        )
        self.assertEqual(
            flowctl.canonicalize_decision_id("fn-5.3"), "fn-5.D3"
        )
        self.assertEqual(
            flowctl.canonicalize_decision_id("D7", chart_id="fn-5"), "fn-5.D7"
        )
        self.assertEqual(
            flowctl.canonicalize_decision_id("7", chart_id="fn-5"), "fn-5.D7"
        )

    def test_decision_id_rejects_cross_chart_and_ambiguous(self) -> None:
        with self.assertRaises(flowctl.ChartError) as ctx:
            flowctl.canonicalize_decision_id("fn-9.D1", chart_id="fn-5")
        self.assertEqual(ctx.exception.code, "cross_chart_decision_id")
        with self.assertRaises(flowctl.ChartError) as ctx2:
            flowctl.canonicalize_decision_id("D1")
        self.assertEqual(ctx2.exception.code, "ambiguous_decision_id")


class TestSharedAllocationScan(unittest.TestCase):
    def test_scan_includes_charts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            _write_spec(flow_dir, "fn-3-alpha")
            _write_chart(flow_dir, "fn-11")
            self.assertEqual(flowctl.scan_max_native_fn_spec_id(flow_dir), 11)

    def test_scan_charts_raise_above_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            _write_spec(flow_dir, "fn-2-x")
            _write_chart(flow_dir, "fn-8")
            self.assertEqual(flowctl.scan_max_native_fn_spec_id(flow_dir), 8)

    def test_worktree_chart_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            flow_dir = base / ".flow"
            _write_spec(flow_dir, "fn-1-local")
            other = base / "other-wt"
            _write_chart(other / ".flow", "fn-9")

            def fake_git(root, args, timeout=10):
                cmd = list(args)
                if cmd[:2] == ["worktree", "list"]:
                    return (
                        0,
                        f"worktree {base}\n\nworktree {other}\n",
                        "",
                    )
                if cmd and cmd[0] == "log":
                    return (0, "", "")
                return (1, "", "unexpected")

            with mock.patch.object(flowctl, "_spec_alloc_git", side_effect=fake_git):
                self.assertEqual(flowctl.scan_max_native_fn_spec_id(flow_dir), 9)


class TestChartEnvelopesAndCreate(unittest.TestCase):
    def test_create_show_list_exact_v1_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)

            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Tenant isolation",
                "--outcome",
                "A capture-ready tenant model",
                "--json",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            env = json.loads(r.stdout)
            self.assertEqual(
                env,
                {
                    "success": True,
                    "schema_version": 1,
                    "command": "chart.create",
                    "result": env["result"],
                },
            )
            result = env["result"]
            self.assertEqual(result["id"], "fn-1")
            self.assertEqual(result["title"], "Tenant isolation")
            self.assertEqual(result["outcome"], "A capture-ready tenant model")
            self.assertEqual(result["status"], "open")
            self.assertEqual(result["decision_count"], 0)
            self.assertEqual(result["chart_path"], ".flow/charts/fn-1.md")
            self.assertIn("created", result)

            md = repo / ".flow" / "charts" / "fn-1.md"
            js = repo / ".flow" / "charts" / "fn-1.json"
            self.assertTrue(md.is_file())
            self.assertTrue(js.is_file())
            body = md.read_text(encoding="utf-8")
            self.assertIn("## Decisions", body)
            self.assertIn("## Outcome", body)
            self.assertIn("A capture-ready tenant model", body)
            # Empty ledger: no D-ID lines under Decisions yet.
            self.assertNotIn("**D", body)
            side = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(side["decisions"], [])
            self.assertEqual(side["status"], "open")

            show = _run_flowctl(repo, "chart", "show", "fn-1", "--json")
            self.assertEqual(show.returncode, 0, show.stderr)
            show_env = json.loads(show.stdout)
            self.assertEqual(show_env["success"], True)
            self.assertEqual(show_env["schema_version"], 1)
            self.assertEqual(show_env["command"], "chart.show")
            self.assertEqual(show_env["result"]["id"], "fn-1")
            self.assertEqual(show_env["result"]["decision_count"], 0)
            self.assertIn("body", show_env["result"])
            self.assertIn("## Decisions", show_env["result"]["body"])

            lst = _run_flowctl(repo, "chart", "list", "--json")
            self.assertEqual(lst.returncode, 0, lst.stderr)
            list_env = json.loads(lst.stdout)
            self.assertEqual(list_env["command"], "chart.list")
            self.assertEqual(list_env["result"]["count"], 1)
            self.assertEqual(list_env["result"]["charts"][0]["id"], "fn-1")
            # Compact list: no graph/frontier/claims keys.
            self.assertNotIn("frontier", list_env["result"]["charts"][0])
            self.assertNotIn("claims", list_env["result"]["charts"][0])

    def test_create_validation_error_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            r = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "",
                "--outcome",
                "x",
                "--json",
            )
            # argparse may reject empty title before our handler; either way
            # non-zero. Prefer structured when our code runs.
            self.assertNotEqual(r.returncode, 0)

            r2 = _run_flowctl(repo, "chart", "show", "fn-999", "--json")
            self.assertNotEqual(r2.returncode, 0)
            err = json.loads(r2.stdout)
            self.assertEqual(err["success"], False)
            self.assertEqual(err["schema_version"], 1)
            self.assertEqual(err["command"], "chart.show")
            self.assertEqual(err["error"]["class"], "not_found")
            self.assertIn("code", err["error"])
            self.assertIn("message", err["error"])
            self.assertIn("details", err["error"])

    def test_no_clobber_existing_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            _write_chart(flow, "fn-1")
            # Force next id to 1 by only having fn-1 already - create must
            # refuse overwrite when scan also sees it... actually scan sees 1,
            # next is 2. Force collision by writing after allocate via hook:
            # call create_chart_pair directly for id that exists.
            with self.assertRaises(flowctl.ChartError) as ctx:
                flowctl.create_chart_pair(
                    flow, "fn-1", "T", "O"
                )
            self.assertEqual(ctx.exception.error_class, "conflict")


class TestMutationPathValidation(unittest.TestCase):
    def test_traversal_paths_rejected_atomically(self) -> None:
        """Traversal relpaths - both separator styles, absolute, drive-letter,
        '.'/'' components - are refused with no file writes. The backslash
        strings are DATA here (Windows resolves them as separators; POSIX must
        still reject them by component)."""
        bad = [
            "../escape.md",
            "a/../../escape.md",
            "x\\..\\..\\..\\escape.md",
            "..\\escape.md",
            "/abs/escape.md",
            "\\abs\\escape.md",
            "C:\\escape.md",
            "a//b.md",
            "./a.md",
            "a/./b.md",
            "",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            (repo / "escape.md").write_text("pristine\n", encoding="utf-8")
            charts = flow / "charts"
            for relpath in bad:
                with self.assertRaises(flowctl.ChartError, msg=relpath) as ctx:
                    flowctl.run_chart_transaction(
                        flow, "chart.test", [(relpath, "create", "owned\n")]
                    )
                self.assertEqual(
                    ctx.exception.code, "invalid_mutation_path", relpath
                )
                # No transaction residue and no writes landed anywhere.
                tx_root = flow / "charts" / ".transactions"
                if tx_root.is_dir():
                    self.assertEqual(list(tx_root.iterdir()), [], relpath)
                if charts.is_dir():
                    stray = [
                        p for p in charts.rglob("*")
                        if p.is_file() and p.name == "escape.md"
                    ]
                    self.assertEqual(stray, [], relpath)
            # Repo file outside .flow/charts is untouched.
            self.assertEqual(
                (repo / "escape.md").read_text(encoding="utf-8"), "pristine\n"
            )
        # A plain nested relpath still works.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            flowctl.run_chart_transaction(
                flow, "chart.test", [("fn-1/1.json", "create", "{}\n")]
            )
            self.assertEqual(
                (flow / "charts" / "fn-1" / "1.json").read_text(
                    encoding="utf-8"
                ),
                "{}\n",
            )


class TestChartHandledFailure(unittest.TestCase):
    def test_injected_raise_after_first_publish_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            # Use in-process path with env raise at after_first_publish.
            env_key = "FLOWCTL_CHART_FAILPOINT"
            old = os.environ.get(env_key)
            os.environ[env_key] = "raise:after_first_publish"
            try:
                with self.assertRaises(flowctl.ChartError):
                    with flowctl.cross_process_lock(flowctl.charts_resource_lock_path(flow)):
                        flowctl.recover_chart_transactions(flow)
                        with flowctl.cross_process_lock(flowctl.native_fn_alloc_lock_path(flow)):
                            flowctl.create_chart_pair(flow, "fn-1", "T", "Outcome text")
            finally:
                if old is None:
                    os.environ.pop(env_key, None)
                else:
                    os.environ[env_key] = old

            charts = flow / "charts"
            self.assertFalse((charts / "fn-1.json").exists())
            self.assertFalse((charts / "fn-1.md").exists())
            # No leftover incomplete journal after handled failure.
            tx = charts / ".transactions"
            if tx.is_dir():
                leftover = [p for p in tx.iterdir() if p.is_dir()]
                self.assertEqual(leftover, [])


class TestChartCrashRecovery(unittest.TestCase):
    def _create_with_failpoint(self, repo: Path, failpoint: str) -> subprocess.CompletedProcess:
        return _run_flowctl(
            repo,
            "chart",
            "create",
            "--title",
            "Crash chart",
            "--outcome",
            "Should recover",
            "--json",
            env={"FLOWCTL_CHART_FAILPOINT": failpoint},
        )

    def test_kill_after_journal_restores_pre_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            r = self._create_with_failpoint(repo, "exit:after_journal")
            self.assertEqual(r.returncode, 99)
            # Incomplete journal may exist; next show recovers.
            show = _run_flowctl(repo, "chart", "show", "fn-1", "--json")
            self.assertNotEqual(show.returncode, 0)
            err = json.loads(show.stdout)
            self.assertEqual(err["error"]["class"], "not_found")
            self.assertFalse((flow / "charts" / "fn-1.json").exists())
            self.assertFalse((flow / "charts" / "fn-1.md").exists())
            tx = flow / "charts" / ".transactions"
            if tx.is_dir():
                self.assertEqual([p for p in tx.iterdir() if p.is_dir()], [])

    def test_kill_after_stage_restores_pre_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            r = self._create_with_failpoint(repo, "exit:after_stage")
            self.assertEqual(r.returncode, 99)
            # Recovery via list
            lst = _run_flowctl(repo, "chart", "list", "--json")
            self.assertEqual(lst.returncode, 0, lst.stderr)
            env = json.loads(lst.stdout)
            self.assertEqual(env["result"]["count"], 0)
            self.assertFalse((flow / "charts" / "fn-1.json").exists())
            self.assertFalse((flow / "charts" / "fn-1.md").exists())

    def test_kill_before_publish_rolls_forward_complete_pair(self) -> None:
        """phase=ready with complete staged set is roll-forward, not restore."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            r = self._create_with_failpoint(repo, "exit:before_publish")
            self.assertEqual(r.returncode, 99)
            lst = _run_flowctl(repo, "chart", "list", "--json")
            self.assertEqual(lst.returncode, 0, lst.stderr)
            env = json.loads(lst.stdout)
            self.assertEqual(env["result"]["count"], 1)
            self.assertEqual(env["result"]["charts"][0]["id"], "fn-1")
            self.assertTrue((flow / "charts" / "fn-1.json").is_file())
            self.assertTrue((flow / "charts" / "fn-1.md").is_file())

    def test_kill_after_first_publish_rolls_forward_or_restores_complete(self) -> None:
        """After first of pair published, recovery must not leave a split pair."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            r = self._create_with_failpoint(repo, "exit:after_first_publish")
            self.assertEqual(r.returncode, 99)

            # Trigger recovery
            lst = _run_flowctl(repo, "chart", "list", "--json")
            self.assertEqual(lst.returncode, 0, lst.stderr)
            charts_dir = flow / "charts"
            json_exists = (charts_dir / "fn-1.json").exists()
            md_exists = (charts_dir / "fn-1.md").exists()
            # Either both present (roll-forward) or both absent (restore).
            self.assertEqual(
                json_exists,
                md_exists,
                f"split pair: json={json_exists} md={md_exists}",
            )
            if json_exists:
                env = json.loads(lst.stdout)
                self.assertEqual(env["result"]["count"], 1)
                self.assertEqual(env["result"]["charts"][0]["id"], "fn-1")
                side = json.loads((charts_dir / "fn-1.json").read_text(encoding="utf-8"))
                self.assertEqual(side["decisions"], [])
            else:
                self.assertEqual(json.loads(lst.stdout)["result"]["count"], 0)

    def test_kill_after_publish_before_commit_rolls_forward(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            flow = _init_flow(repo)
            r = self._create_with_failpoint(repo, "exit:after_publish_before_commit")
            self.assertEqual(r.returncode, 99)
            show = _run_flowctl(repo, "chart", "show", "fn-1", "--json")
            self.assertEqual(show.returncode, 0, show.stderr)
            env = json.loads(show.stdout)
            self.assertEqual(env["result"]["id"], "fn-1")
            self.assertTrue((flow / "charts" / "fn-1.json").is_file())
            self.assertTrue((flow / "charts" / "fn-1.md").is_file())
            tx = flow / "charts" / ".transactions"
            if tx.is_dir():
                self.assertEqual([p for p in tx.iterdir() if p.is_dir()], [])


class TestConcurrentSpecAndChart(unittest.TestCase):
    def test_concurrent_spec_and_chart_allocate_distinct_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)

            results: list[tuple[str, str]] = []
            errors: list[str] = []

            def make_spec() -> None:
                r = _run_flowctl(
                    repo, "spec", "create", "--title", "Spec concurrent", "--json"
                )
                if r.returncode != 0:
                    errors.append(f"spec: {r.stderr} {r.stdout}")
                    return
                data = json.loads(r.stdout)
                results.append(("spec", data["id"]))

            def make_chart() -> None:
                r = _run_flowctl(
                    repo,
                    "chart",
                    "create",
                    "--title",
                    "Chart concurrent",
                    "--outcome",
                    "Outcome concurrent",
                    "--json",
                )
                if r.returncode != 0:
                    errors.append(f"chart: {r.stderr} {r.stdout}")
                    return
                data = json.loads(r.stdout)
                results.append(("chart", data["result"]["id"]))

            threads = [
                threading.Thread(target=make_spec),
                threading.Thread(target=make_chart),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=60)

            self.assertEqual(errors, [], errors)
            self.assertEqual(len(results), 2, results)
            nums = []
            for _kind, cid in results:
                parts = cid.split("-")
                self.assertEqual(parts[0], "fn")
                nums.append(int(parts[1]))
            self.assertEqual(sorted(nums), [1, 2], results)
            self.assertNotEqual(nums[0], nums[1])

    def test_chart_then_spec_monotonic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            c = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "First",
                "--outcome",
                "O",
                "--json",
            )
            self.assertEqual(c.returncode, 0, c.stderr)
            chart_id = json.loads(c.stdout)["result"]["id"]
            self.assertEqual(chart_id, "fn-1")
            s = _run_flowctl(
                repo, "spec", "create", "--title", "Second Spec", "--json"
            )
            self.assertEqual(s.returncode, 0, s.stderr)
            spec_id = json.loads(s.stdout)["id"]
            self.assertTrue(spec_id.startswith("fn-2-"), spec_id)

    def test_spec_then_chart_monotonic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _init_flow(repo)
            s = _run_flowctl(
                repo, "spec", "create", "--title", "First Spec", "--json"
            )
            self.assertEqual(s.returncode, 0, s.stderr)
            self.assertTrue(json.loads(s.stdout)["id"].startswith("fn-1-"))
            c = _run_flowctl(
                repo,
                "chart",
                "create",
                "--title",
                "Second",
                "--outcome",
                "O",
                "--json",
            )
            self.assertEqual(c.returncode, 0, c.stderr)
            self.assertEqual(json.loads(c.stdout)["result"]["id"], "fn-2")


class TestWorktreeCrossKind(unittest.TestCase):
    def test_uncommitted_chart_in_worktree_a_visible_to_spec_in_b(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "main"
            _init_repo(main)
            _init_flow(main)
            _git(main, "add", "-A")
            _git(main, "commit", "-q", "-m", "base")

            wt_a = tmp_path / "wt-a"
            wt_b = tmp_path / "wt-b"
            _git(main, "worktree", "add", "-q", str(wt_a), "-b", "branch-a")
            _git(main, "worktree", "add", "-q", str(wt_b), "-b", "branch-b")

            c = _run_flowctl(
                wt_a,
                "chart",
                "create",
                "--title",
                "From A",
                "--outcome",
                "Outcome A",
                "--json",
            )
            self.assertEqual(c.returncode, 0, c.stderr)
            chart_id = json.loads(c.stdout)["result"]["id"]
            self.assertEqual(chart_id, "fn-1")

            s = _run_flowctl(
                wt_b, "spec", "create", "--title", "From B", "--json"
            )
            self.assertEqual(s.returncode, 0, s.stderr)
            spec_id = json.loads(s.stdout)["id"]
            self.assertTrue(
                spec_id.startswith("fn-2-"),
                f"B allocated {spec_id}; must see A's uncommitted chart {chart_id}",
            )


if __name__ == "__main__":
    unittest.main()
