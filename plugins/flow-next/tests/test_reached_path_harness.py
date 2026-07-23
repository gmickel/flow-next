"""fn-130.1: reached-path harness self-tests (CI).

Exercises the actual optimization/reached-path modules — character algorithm,
ratchet policy, privacy scrub, isolation tripwires, and trace parsing —
including at least one active direct-reference activation and one cold
forbidden-reference non-read (deterministic trace fixture, no live model).
"""

from __future__ import annotations

import copy
import datetime as _dt
import importlib.util
import json
import shutil
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / "optimization" / "reached-path"
RUN_EVAL = HARNESS / "run_eval.py"
SYNTHETIC = HARNESS / "fixtures" / "synthetic"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestReachedPathHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.character = _load("rp_character", HARNESS / "character.py")
        cls.ratchet = _load("rp_ratchet", HARNESS / "ratchet.py")
        cls.privacy = _load("rp_privacy", HARNESS / "privacy.py")
        cls.isolation = _load("rp_isolation", HARNESS / "isolation.py")
        cls.trace = _load("rp_trace", HARNESS / "trace.py")
        cls.inventory = _load("rp_inventory", HARNESS / "inventory.py")
        cls.run_eval = _load("rp_run_eval", RUN_EVAL)

    def test_harness_entrypoint_present(self) -> None:
        self.assertTrue(RUN_EVAL.is_file())
        self.assertTrue((HARNESS / "README.md").is_file())
        self.assertTrue((HARNESS / "deferrals.md").is_file())

    def test_self_test_passes(self) -> None:
        rc = self.run_eval.self_test()
        self.assertEqual(rc, 0, "reached-path --self-test failed")

    def test_character_algorithm_active_and_cold(self) -> None:
        """Active direct reference counts; cold forbidden file is not activated."""
        root = (SYNTHETIC / "SKILL.md").read_text(encoding="utf-8")
        active = (SYNTHETIC / "references" / "active.md").read_text(encoding="utf-8")
        cold = (SYNTHETIC / "references" / "cold.md").read_text(encoding="utf-8")
        metrics = self.character.compute_reached_path(
            root_skill_text=root,
            root_skill_path="fixtures/synthetic/SKILL.md",
            activated=[("fixtures/synthetic/references/active.md", active)],
        )
        paths = {f["path"] for f in metrics["files"]}
        self.assertIn("fixtures/synthetic/SKILL.md", paths)
        self.assertIn("fixtures/synthetic/references/active.md", paths)
        self.assertNotIn("fixtures/synthetic/references/cold.md", paths)
        with_cold = self.character.compute_reached_path(
            root_skill_text=root,
            root_skill_path="fixtures/synthetic/SKILL.md",
            activated=[
                ("fixtures/synthetic/references/active.md", active),
                ("fixtures/synthetic/references/cold.md", cold),
            ],
        )
        self.assertGreater(with_cold["reached_path_chars"], metrics["reached_path_chars"])

    def test_synthetic_skill_is_neutral_two_route(self) -> None:
        """Subject-visible skill must not disclose scorer required/forbidden conclusions."""
        text = (SYNTHETIC / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("route=alpha", text)
        self.assertIn("route=beta", text)
        self.assertIn("references/active.md", text)
        self.assertIn("references/cold.md", text)
        # Must not spoon-feed the scorer answer key.
        lowered = text.lower()
        self.assertNotIn("do not read `references/cold.md`", lowered)
        self.assertNotIn("do not read references/cold.md", lowered)
        self.assertNotIn("forbidden", lowered)
        self.assertNotIn("required action", lowered)

    def test_trace_paired_success_included(self) -> None:
        """Successful Read requires matching non-error tool_result by tool_use_id."""
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "a",
                                    "name": "Read",
                                    "input": {
                                        "file_path": "/arena/skill/references/active.md",
                                        "offset": 2,
                                        "limit": 10,
                                    },
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "a",
                                    "content": "ok",
                                }
                            ]
                        },
                    }
                ),
                # Repeated successful read of the same path (evidence preserved).
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "a2",
                                    "name": "Read",
                                    "input": {
                                        "file_path": "/arena/skill/references/active.md",
                                    },
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "a2",
                                    "is_error": False,
                                    "content": "ok again",
                                }
                            ]
                        },
                    }
                ),
                json.dumps({"type": "result", "usage": {"input_tokens": 3}}),
            ]
        )
        reads = self.trace.parse_stream_json_reads(stream)
        self.assertEqual(len(reads), 2)
        self.assertEqual(reads[0]["offset"], 2)
        self.assertEqual(reads[0]["limit"], 10)
        self.assertEqual(reads[0]["tool_use_id"], "a")
        self.assertIsNone(reads[1].get("offset"))
        acts = self.trace.successful_activations(reads, [])
        self.assertEqual(len(acts), 1)  # path-deduped
        self.assertTrue(acts[0].endswith("active.md"))

    def test_trace_unpaired_tool_use_excluded(self) -> None:
        """Truncated stream: unpaired Read tool_use is not a successful activation."""
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "orphan",
                                    "name": "Read",
                                    "input": {
                                        "file_path": "/arena/skill/references/active.md"
                                    },
                                }
                            ]
                        },
                    }
                ),
                json.dumps({"type": "result", "usage": {"input_tokens": 1}}),
            ]
        )
        reads = self.trace.parse_stream_json_reads(stream)
        failed = self.trace.parse_stream_json_failed_reads(stream)
        acts = self.trace.successful_activations(reads, failed)
        self.assertEqual(reads, [])
        self.assertEqual(failed, [])
        self.assertEqual(acts, [])

    def test_trace_error_tool_result_excluded_and_failed(self) -> None:
        """is_error tool_result is failed, not successful."""
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "bad",
                                    "name": "Read",
                                    "input": {
                                        "file_path": "/arena/skill/references/missing.md"
                                    },
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "bad",
                                    "is_error": True,
                                    "content": "ENOENT",
                                }
                            ]
                        },
                    }
                ),
            ]
        )
        reads = self.trace.parse_stream_json_reads(stream)
        failed = self.trace.parse_stream_json_failed_reads(stream)
        acts = self.trace.successful_activations(reads, failed)
        self.assertEqual(reads, [])
        self.assertEqual(len(failed), 1)
        self.assertTrue(failed[0]["path"].endswith("missing.md"))
        self.assertEqual(failed[0]["tool_use_id"], "bad")
        self.assertEqual(acts, [])

    def test_trace_cold_forbidden_non_read(self) -> None:
        """Cold forbidden path never appears when only a paired active Read succeeded."""
        stream = "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "a",
                                    "name": "Read",
                                    "input": {
                                        "file_path": "/arena/skill/references/active.md"
                                    },
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "a",
                                    "content": "active",
                                }
                            ]
                        },
                    }
                ),
                json.dumps({"type": "result", "usage": {"input_tokens": 3}}),
            ]
        )
        reads = self.trace.parse_stream_json_reads(stream)
        acts = self.trace.successful_activations(reads, [])
        self.assertTrue(any(a.endswith("active.md") for a in acts))
        self.assertFalse(any(a.endswith("cold.md") for a in acts))

    def test_freeze_b0_refuses_existing_canonical_before_writes(self) -> None:
        """Existing fixtures/b0/ is nonempty/immutable — refuse before any write."""
        index = HARNESS / "fixtures" / "b0" / "INDEX.json"
        self.assertTrue(index.is_file())
        before = index.read_bytes()
        before_mtime = index.stat().st_mtime_ns
        # Also snapshot a manifest to prove no rewrite.
        sample = next((HARNESS / "fixtures" / "b0").glob("*/*.json"))
        sample_before = sample.read_bytes()
        rc = self.run_eval.freeze_b0()
        self.assertEqual(rc, 1)
        self.assertEqual(index.read_bytes(), before)
        self.assertEqual(index.stat().st_mtime_ns, before_mtime)
        self.assertEqual(sample.read_bytes(), sample_before)

    def test_freeze_b0_refuses_nonempty_temp_without_index(self) -> None:
        """Nonempty temp target without INDEX refuses before any git/source work."""
        with tempfile.TemporaryDirectory(prefix="rp-freeze-nonempty-") as td:
            out = Path(td) / "b0"
            out.mkdir()
            leftover = out / "plan" / "p1-flow-native.json"
            leftover.parent.mkdir(parents=True)
            marker = b'{"leftover": true}\n'
            leftover.write_bytes(marker)
            mat_calls: list[object] = []
            real_mat = self.run_eval.materialize_baseline_sources

            def _track_mat(*args, **kwargs):
                mat_calls.append((args, kwargs))
                return real_mat(*args, **kwargs)

            self.run_eval.materialize_baseline_sources = _track_mat  # type: ignore[method-assign]
            try:
                rc = self.run_eval.freeze_b0(output_dir=out)
            finally:
                self.run_eval.materialize_baseline_sources = real_mat  # type: ignore[method-assign]
            self.assertEqual(rc, 1)
            self.assertEqual(
                mat_calls, [], "nonempty guard must precede baseline source materialize"
            )
            self.assertFalse((out / "INDEX.json").exists())
            self.assertEqual(leftover.read_bytes(), marker)
            # No extra freeze artifacts beside the leftover tree.
            written = sorted(p for p in out.rglob("*") if p.is_file())
            self.assertEqual(written, [leftover])

    def test_freeze_b0_git_show_failure_leaves_no_output(self) -> None:
        """Baseline git-show failure must leave absent output untouched."""
        with tempfile.TemporaryDirectory(prefix="rp-freeze-gitsfail-") as td:
            out = Path(td) / "b0"
            real_mat = self.run_eval.materialize_baseline_sources

            def _boom(*args, **kwargs):
                raise RuntimeError("simulated git show failure")

            self.run_eval.materialize_baseline_sources = _boom  # type: ignore[method-assign]
            try:
                rc = self.run_eval.freeze_b0(output_dir=out)
            finally:
                self.run_eval.materialize_baseline_sources = real_mat  # type: ignore[method-assign]
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())
            self.assertFalse((out / "INDEX.json").exists())

    def test_freeze_b0_bootstraps_from_current_head_without_monkeypatch(self) -> None:
        """Absent temp target bootstraps from git-show at current non-baseline HEAD."""
        with tempfile.TemporaryDirectory(prefix="rp-freeze-ok-") as td:
            out = Path(td) / "b0"
            # No HEAD monkeypatch — harness must work from the live checkout.
            self.assertFalse(hasattr(self.run_eval, "resolve_git_head"))
            rc = self.run_eval.freeze_b0(output_dir=out)
            self.assertEqual(rc, 0)
            self.assertTrue((out / "INDEX.json").is_file())
            index = json.loads((out / "INDEX.json").read_text(encoding="utf-8"))
            baseline = self.run_eval.BASELINE_COMMIT
            self.assertEqual(index["baseline"], "B0")
            self.assertEqual(index["baseline_commit"], baseline)
            self.assertGreater(index["fixture_count"], 0)
            # Canonical B0 untouched.
            canon_path = HARNESS / "fixtures" / "b0" / "INDEX.json"
            self.assertTrue(canon_path.is_file())
            self.assertNotEqual(canon_path.resolve(), (out / "INDEX.json").resolve())
            # Prove baseline git-show sources — match checked-in INDEX ids/hashes/counts
            # even when the live worktree may differ from BASELINE_COMMIT.
            canon = json.loads(canon_path.read_text(encoding="utf-8"))
            self.assertEqual(index["fixture_count"], canon["fixture_count"])
            self.assertEqual(len(index["fixtures"]), len(canon["fixtures"]))
            by_id_boot = {f["fixture_id"]: f for f in index["fixtures"]}
            by_id_canon = {f["fixture_id"]: f for f in canon["fixtures"]}
            self.assertEqual(set(by_id_boot), set(by_id_canon))
            for fid, crow in by_id_canon.items():
                brow = by_id_boot[fid]
                self.assertEqual(
                    brow["fixture_hash"],
                    crow["fixture_hash"],
                    f"fixture_hash drift for {fid}",
                )
                self.assertEqual(
                    brow["reached_path_chars"],
                    crow["reached_path_chars"],
                    f"reached_path_chars drift for {fid}",
                )
                self.assertEqual(brow["cluster"], crow["cluster"])

    def test_freeze_b0_ignores_poisoned_live_source_reader(self) -> None:
        """Freeze uses preflighted baseline map; a live reader seam cannot alter hashes."""
        items = self.inventory.inventory()
        paths = self.run_eval.inventory_prompt_paths(items)
        sources = self.run_eval.materialize_baseline_sources(
            paths, commit=self.run_eval.BASELINE_COMMIT
        )
        fx = copy.deepcopy(items[0])

        def _poison(_path: str) -> str:
            return "POISONED_LIVE_WORKTREE_CONTENT\n"

        live_poisoned = self.run_eval._fill_hashes(copy.deepcopy(fx), source_reader=_poison)
        baseline_filled = self.run_eval._fill_hashes(copy.deepcopy(fx), sources=sources)
        default_live = self.run_eval._fill_hashes(copy.deepcopy(fx))
        self.assertNotEqual(
            live_poisoned["fixture_hash"],
            baseline_filled["fixture_hash"],
            "poisoned live reader must diverge from baseline sources",
        )
        # Baseline sources match what freeze will write; default live may match
        # or not depending on worktree dirtiness — only assert baseline path works.
        self.assertTrue(
            all(
                not str(h).startswith("MISSING:")
                for h in baseline_filled["prompt_hashes"].values()
            )
        )
        # Sanity: default live path still functions (validation call sites).
        self.assertIn("fixture_hash", default_live)
        self.assertIn("prompt_hashes", default_live)

    def test_freeze_b0_output_immune_to_poisoned_live_reader_seam(self) -> None:
        """End-to-end: poison live reader; freeze output still matches canonical B0."""
        with tempfile.TemporaryDirectory(prefix="rp-freeze-poison-") as td:
            out = Path(td) / "b0"
            real_reader = self.run_eval._read_live_repo_text

            def _poison(_path: str):
                return "POISONED_LIVE_WORKTREE_CONTENT\n"

            self.run_eval._read_live_repo_text = _poison  # type: ignore[method-assign]
            try:
                rc = self.run_eval.freeze_b0(output_dir=out)
            finally:
                self.run_eval._read_live_repo_text = real_reader  # type: ignore[method-assign]
            self.assertEqual(rc, 0)
            boot = json.loads((out / "INDEX.json").read_text(encoding="utf-8"))
            canon = json.loads(
                (HARNESS / "fixtures" / "b0" / "INDEX.json").read_text(encoding="utf-8")
            )
            by_boot = {f["fixture_id"]: f for f in boot["fixtures"]}
            by_canon = {f["fixture_id"]: f for f in canon["fixtures"]}
            self.assertEqual(set(by_boot), set(by_canon))
            for fid, crow in by_canon.items():
                self.assertEqual(by_boot[fid]["fixture_hash"], crow["fixture_hash"])
                self.assertEqual(
                    by_boot[fid]["reached_path_chars"], crow["reached_path_chars"]
                )
            # Spot-check one manifest body hash against canonical file.
            sample_id = next(iter(by_canon))
            cluster = by_canon[sample_id]["cluster"]
            name = sample_id.split(".", 1)[-1] + ".json"
            boot_fx = json.loads((out / cluster / name).read_text(encoding="utf-8"))
            canon_fx = json.loads(
                (HARNESS / "fixtures" / "b0" / cluster / name).read_text(encoding="utf-8")
            )
            self.assertEqual(boot_fx["fixture_hash"], canon_fx["fixture_hash"])
            self.assertEqual(boot_fx["prompt_hashes"], canon_fx["prompt_hashes"])
            self.assertTrue(
                all("POISON" not in str(v) for v in boot_fx["prompt_hashes"].values())
            )

    def test_inventory_covers_required_clusters(self) -> None:
        items = self.inventory.inventory()
        clusters = {i["cluster"] for i in items}
        for c in (
            "version",
            "setup",
            "tracker",
            "prime",
            "plan-review",
            "plan",
            "work",
            "strategy",
            "make-pr",
            "pilot",
            "cross-host",
        ):
            self.assertIn(c, clusters)
        self.assertEqual(items[0]["baseline_commit"], self.inventory.BASELINE_COMMIT)
        for i in items:
            self.assertIsNot(i.get("branch_inputs", {}).get("live_tracker"), True)
            self.assertTrue(i["privacy"]["no_live_tracker"])
            self.assertEqual(i["ratchet"]["flat_or_noisy"], "discard")
            self.assertEqual(
                i["provenance"]["capture_kind"], "deterministic_freeze"
            )
            self.assertTrue(i["provenance"].get("capture_reason"))
            self.assertIsNone(i["provenance"].get("model"))
            self.assertIsNone(i["provenance"].get("cli_version"))

    def test_codex_fixture_hashes_mirror_not_canonical(self) -> None:
        """Codex manifests count regenerated mirror files; hash differs when content differs."""
        items = {i["fixture_id"]: i for i in self.inventory.inventory()}
        fx = items["cross-host.codex-slash"]
        self.assertTrue(fx.get("mirror_skill"))
        for p in fx["prompt_files"] + fx["required_reads"]:
            self.assertTrue(
                p.startswith("plugins/flow-next/codex/"),
                f"Codex fixture must hash mirror path, got {p}",
            )
            self.assertFalse(p.startswith("plugins/flow-next/skills/"))
        filled = self.run_eval._fill_hashes(copy.deepcopy(fx))
        mirror_root = (
            "plugins/flow-next/codex/skills/flow-next-work/SKILL.md"
        )
        canon_root = "plugins/flow-next/skills/flow-next-work/SKILL.md"
        mirror_hash = filled["prompt_hashes"][mirror_root]
        canon_hash = self.character.content_hash(
            (REPO / canon_root).read_text(encoding="utf-8")
        )
        self.assertEqual(
            mirror_hash,
            self.character.content_hash(
                (REPO / mirror_root).read_text(encoding="utf-8")
            ),
        )
        self.assertNotEqual(
            mirror_hash,
            canon_hash,
            "canonical and regenerated mirror must differ for this skill",
        )
        # Reached-path root must be the mirror file.
        root_entry = filled["metrics"]["reached_path_files"][0]
        self.assertEqual(root_entry["path"], mirror_root)
        self.assertEqual(root_entry["content_hash"], mirror_hash)

    def test_tracker_required_reads_all_hashed_and_counted(self) -> None:
        items = {i["fixture_id"]: i for i in self.inventory.inventory()}
        fx = items["tracker.linear-mcp"]
        self.assertGreater(len(fx["required_reads"]), len(self.inventory.TRACKER_COMMON))
        for req in fx["required_reads"]:
            self.assertIn(req, fx["prompt_files"])
        filled = self.run_eval._fill_hashes(copy.deepcopy(fx))
        reached = {f["path"] for f in filled["metrics"]["reached_path_files"]}
        for req in fx["required_reads"]:
            self.assertIn(req, filled["prompt_hashes"])
            self.assertFalse(str(filled["prompt_hashes"][req]).startswith("MISSING:"))
            self.assertIn(req, reached)

    def test_version_oracles_are_current_main_not_130_2(self) -> None:
        items = {i["fixture_id"]: i for i in self.inventory.inventory()}
        plugin = items["version.plugin-mode"]
        detail = plugin["oracles"]["output"][0]["detail"]
        self.assertIn("FLOW_SNIPPET_ASK", detail)
        self.assertNotEqual(detail, "no runtime snippet/version ceremony in Plan")
        self.assertIn("target_output", plugin.get("mutation_targets") or {})
        cont = items["version.interactive-mismatch-continue"]
        self.assertEqual(cont["branch_inputs"].get("choice"), "skip")
        self.assertIn("Skip this run", cont["oracles"]["output"][0]["detail"])
        self.assertIn("version.interactive-mismatch-remind", items)
        remind = items["version.interactive-mismatch-remind"]
        self.assertTrue(
            any(
                w.get("kind") == "version_ack_write"
                for w in remind["oracles"]["writes"]
            )
        )

    def test_b0_manifests_frozen_and_valid(self) -> None:
        index = HARNESS / "fixtures" / "b0" / "INDEX.json"
        self.assertTrue(
            index.is_file(),
            "B0 INDEX.json missing — run python3 optimization/reached-path/run_eval.py --freeze-b0",
        )
        self.assertEqual(self.run_eval.validate_b0(), 0)

    def test_auth_envelope_positive_and_zero_token(self) -> None:
        """Deterministic JSON-envelope auth contract — no live model."""
        positive = {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "OK",
            "usage": {
                "input_tokens": 8,
                "output_tokens": 2,
                "cache_creation_input_tokens": 4,
                "cache_read_input_tokens": 50,
            },
            "modelUsage": {
                "claude-haiku-4-5": {
                    "inputTokens": 8,
                    "outputTokens": 2,
                    "cacheCreationInputTokens": 4,
                    "cacheReadInputTokens": 50,
                }
            },
        }
        ok = self.isolation.evaluate_auth_envelope(positive, rc=0)
        self.assertTrue(ok["ok"])
        self.assertFalse(ok["invalid"])
        self.assertEqual(ok["reason"], "ok")
        self.assertGreater(ok["usage_totals"]["backend_total"], 0)
        self.assertGreater(ok["usage_totals"]["model_total"], 0)

        zero = copy.deepcopy(positive)
        zero["usage"] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        zero["modelUsage"] = {
            "claude-haiku-4-5": {
                "inputTokens": 0,
                "outputTokens": 0,
                "cacheCreationInputTokens": 0,
                "cacheReadInputTokens": 0,
            }
        }
        bad = self.isolation.evaluate_auth_envelope(zero, rc=0)
        self.assertFalse(bad["ok"])
        self.assertTrue(bad["invalid"])
        self.assertEqual(bad["reason"], "zero_token_auth_failure")

        parsed = self.isolation.parse_claude_json_envelope(json.dumps(positive))
        self.assertEqual(parsed.get("result"), "OK")
        self.assertEqual(
            self.isolation.evaluate_auth_envelope(None, rc=0)["reason"],
            "envelope_parse_error",
        )

    def test_validate_b0_detects_tampered_hash_and_index(self) -> None:
        """Tamper regression on an isolated copy — never mutate committed B0."""
        with tempfile.TemporaryDirectory(prefix="rp-tamper-") as td:
            tmp_here = Path(td)
            src = HARNESS / "fixtures" / "b0"
            dst = tmp_here / "fixtures" / "b0"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)

            manifests = [
                json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(dst.glob("*/*.json"))
            ]
            self.assertTrue(manifests)
            index = json.loads((dst / "INDEX.json").read_text(encoding="utf-8"))

            # Clean copy must pass the production INDEX validator.
            self.assertEqual(
                self.run_eval.validate_index(index, manifests, tmp_here),
                [],
            )

            # Manifest body hash mismatch (validate_manifest seam).
            sample = copy.deepcopy(manifests[0])
            mutated = copy.deepcopy(sample)
            mutated["oracles"] = {
                "output": [{"kind": "tampered"}],
                "tools": [],
                "writes": [],
                "receipts": [],
            }
            self.assertNotEqual(
                mutated["fixture_hash"],
                self.run_eval.recompute_fixture_hash(mutated),
            )
            errs = self.run_eval.validate_manifest(mutated)
            self.assertTrue(
                any("fixture_hash mismatch" in e for e in errs),
                f"expected hash mismatch, got {errs}",
            )

            # INDEX duplicate fixture_id.
            dup = copy.deepcopy(index)
            dup["fixtures"] = list(dup["fixtures"]) + [
                copy.deepcopy(dup["fixtures"][0])
            ]
            dup_errs = self.run_eval.validate_index(dup, manifests, tmp_here)
            self.assertTrue(
                any("duplicate fixture_id" in e for e in dup_errs),
                f"expected duplicate rejection, got {dup_errs}",
            )

            # INDEX missing a manifest id.
            missing = copy.deepcopy(index)
            missing["fixtures"] = list(missing["fixtures"][1:])
            missing["fixture_count"] = len(missing["fixtures"])
            miss_errs = self.run_eval.validate_index(missing, manifests, tmp_here)
            self.assertTrue(
                any("id mismatch" in e or "INDEX count" in e for e in miss_errs),
                f"expected missing-id rejection, got {miss_errs}",
            )

            # Wrong INDEX fixture_hash.
            bad_hash = copy.deepcopy(index)
            bad_hash["fixtures"] = copy.deepcopy(bad_hash["fixtures"])
            bad_hash["fixtures"][0]["fixture_hash"] = "0" * 64
            hash_errs = self.run_eval.validate_index(bad_hash, manifests, tmp_here)
            self.assertTrue(
                any("INDEX fixture_hash != manifest" in e for e in hash_errs),
                f"expected hash rejection, got {hash_errs}",
            )

            # Wrong INDEX path.
            bad_path = copy.deepcopy(index)
            bad_path["fixtures"] = copy.deepcopy(bad_path["fixtures"])
            bad_path["fixtures"][0]["path"] = "fixtures/b0/nope/missing.json"
            path_errs = self.run_eval.validate_index(bad_path, manifests, tmp_here)
            self.assertTrue(
                any("INDEX path invalid" in e for e in path_errs),
                f"expected path rejection, got {path_errs}",
            )

            # Wrong INDEX reached_path_chars.
            bad_chars = copy.deepcopy(index)
            bad_chars["fixtures"] = copy.deepcopy(bad_chars["fixtures"])
            bad_chars["fixtures"][0]["reached_path_chars"] = -1
            chars_errs = self.run_eval.validate_index(bad_chars, manifests, tmp_here)
            self.assertTrue(
                any("reached_path_chars" in e for e in chars_errs),
                f"expected chars rejection, got {chars_errs}",
            )
    def test_isolation_arena_only_write_breaches(self) -> None:
        """Arena-only create/modify/remove must make unclean + breached; sentinel intact."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            arena = base / "arena"
            arena.mkdir()
            (arena / "x.txt").write_text("1\n", encoding="utf-8")
            pre = self.isolation.fs_snapshot(arena)
            sentinel, token, sig = self.isolation.plant_sentinel(base)
            (arena / "y.txt").write_text("2\n", encoding="utf-8")
            iso = self.isolation.isolation_report(
                arena, pre, sentinel, token, sig, stdout="clean", stderr=""
            )
            self.assertIn("y.txt", iso["arena_diff"]["created"])
            self.assertTrue(iso["arena_changed"])
            self.assertFalse(iso["clean"])
            self.assertTrue(self.isolation.isolation_breached(iso))
            self.assertFalse(iso["sentinel_modified"])
            self.assertFalse(iso["sentinel_deleted"])
            self.assertFalse(iso["sentinel_token_leaked"])
            # Modify existing arena file.
            pre2 = self.isolation.fs_snapshot(arena)
            (arena / "x.txt").write_text("changed\n", encoding="utf-8")
            iso_mod = self.isolation.isolation_report(
                arena, pre2, sentinel, token, sig, stdout="clean", stderr=""
            )
            self.assertIn("x.txt", iso_mod["arena_diff"]["modified"])
            self.assertTrue(self.isolation.isolation_breached(iso_mod))
            # Remove arena file.
            pre3 = self.isolation.fs_snapshot(arena)
            (arena / "y.txt").unlink()
            iso_rm = self.isolation.isolation_report(
                arena, pre3, sentinel, token, sig, stdout="clean", stderr=""
            )
            self.assertIn("y.txt", iso_rm["arena_diff"]["removed"])
            self.assertTrue(self.isolation.isolation_breached(iso_rm))
            # Sentinel leak still trips (no arena change needed).
            pre4 = self.isolation.fs_snapshot(arena)
            iso_leak = self.isolation.isolation_report(
                arena, pre4, sentinel, token, sig, stdout=token, stderr=""
            )
            self.assertTrue(iso_leak["sentinel_token_leaked"])
            self.assertTrue(self.isolation.isolation_breached(iso_leak))
            self.assertFalse(iso_leak["clean"])

    def test_instruction_leak_identity_residual_vs_guidance(self) -> None:
        """OAuth userEmail is residual; planted guidance signatures still fail."""
        marker = "REACHED-PATH-LEAK-MARKER-deadbeef"
        identity_only = (
            f"Project marker UNIQUE_MARKER={marker}. "
            "Session also exposes userEmail gordon@mickel.tech as account identity."
        )
        pass_verdict = self.isolation.evaluate_instruction_leak(
            identity_only, marker=marker, rc=0
        )
        self.assertTrue(pass_verdict["ok"])
        self.assertTrue(pass_verdict["marker_present"])
        self.assertEqual(pass_verdict["global_leaks"], [])
        self.assertIn("userEmail", pass_verdict["identity_residual"])
        self.assertIn("account_email", pass_verdict["identity_residual"])
        scrubbed = pass_verdict["stdout_scrubbed"]
        self.assertNotIn("gordon@mickel.tech", scrubbed)
        self.assertNotIn(marker, scrubbed)
        self.assertIn("[REDACTED-EMAIL]", scrubbed)
        self.assertIn("[REDACTED-MARKER]", scrubbed)

        guidance_leak = (
            f"UNIQUE_MARKER={marker}\n"
            "Also loaded Owner block from global instructions."
        )
        fail_verdict = self.isolation.evaluate_instruction_leak(
            guidance_leak, marker=marker, rc=0
        )
        self.assertFalse(fail_verdict["ok"])
        self.assertIn("Owner block", fail_verdict["global_leaks"])
        # Email alone must never be classified as a guidance needle.
        self.assertNotIn(
            "gordon@mickel.tech", self.isolation.GLOBAL_GUIDANCE_NEEDLES
        )

    def test_ratchet_rejects_flat(self) -> None:
        decision = self.ratchet.decide_ratchet(
            baseline_accuracy={"a": True},
            candidate_accuracy={"a": True},
            baseline_metrics={
                "reached_path_chars": 100,
                "__lower_better__": ["reached_path_chars"],
            },
            candidate_metrics={
                "reached_path_chars": 100,
                "__lower_better__": ["reached_path_chars"],
            },
        )
        self.assertEqual(decision["verdict"], "discard")

    def test_smoke_persist_candidate_leaves_tracked_proof_untouched(self) -> None:
        """Ordinary success/failure candidate writes never touch tracked B0 proof."""
        with tempfile.TemporaryDirectory(prefix="rp-smoke-cand-") as td:
            runs = Path(td) / "runs"
            runs.mkdir()
            tracked = self.run_eval.tracked_b0_smoke_path(runs)
            marker = b'{"status":"pass","immutable":true}\n'
            tracked.write_bytes(marker)
            before_mtime = tracked.stat().st_mtime_ns
            when = _dt.datetime(2026, 7, 23, 12, 0, 0, 123456, tzinfo=_dt.timezone.utc)

            path_ok, kind_ok = self.run_eval.persist_production_path_smoke(
                {"status": "pass", "note": "ok", "email": "gordon@mickel.tech"},
                runs_dir=runs,
                mode="candidate",
                when=when,
            )
            self.assertEqual(kind_ok, "candidate")
            self.assertTrue(path_ok.is_file())
            self.assertEqual(path_ok.parent.name, "candidates")
            self.assertIn("production-path-smoke-pass", path_ok.name)
            body_ok = json.loads(path_ok.read_text(encoding="utf-8"))
            self.assertEqual(body_ok["status"], "pass")
            self.assertIn("[REDACTED-EMAIL]", json.dumps(body_ok))
            self.assertNotIn("gordon@mickel.tech", json.dumps(body_ok))

            when_fail = when + _dt.timedelta(seconds=1)
            path_fail, kind_fail = self.run_eval.persist_production_path_smoke(
                {"status": "invalid_auth", "reason": "zero_token"},
                runs_dir=runs,
                mode="candidate",
                when=when_fail,
            )
            self.assertEqual(kind_fail, "candidate")
            self.assertIn("invalid_auth", path_fail.name)
            self.assertNotEqual(path_ok, path_fail)

            self.assertEqual(tracked.read_bytes(), marker)
            self.assertEqual(tracked.stat().st_mtime_ns, before_mtime)

    def test_smoke_persist_freeze_b0_pass_and_refreeze_refuse(self) -> None:
        """One-time B0 pass creates only when absent; second promotion refuses."""
        with tempfile.TemporaryDirectory(prefix="rp-smoke-freeze-") as td:
            runs = Path(td) / "runs"
            when = _dt.datetime(2026, 7, 23, 13, 0, 0, 1, tzinfo=_dt.timezone.utc)
            path1, kind1 = self.run_eval.persist_production_path_smoke(
                {"status": "pass", "proof": True},
                runs_dir=runs,
                mode="freeze_b0",
                when=when,
            )
            self.assertEqual(kind1, "b0_proof")
            self.assertEqual(path1.name, self.run_eval.B0_SMOKE_FILENAME)
            before = path1.read_bytes()
            before_mtime = path1.stat().st_mtime_ns

            with self.assertRaises(RuntimeError) as ctx:
                self.run_eval.persist_production_path_smoke(
                    {"status": "pass", "proof": "second"},
                    runs_dir=runs,
                    mode="freeze_b0",
                    when=when + _dt.timedelta(seconds=2),
                )
            self.assertIn("refuse overwrite", str(ctx.exception).lower())
            self.assertEqual(path1.read_bytes(), before)
            self.assertEqual(path1.stat().st_mtime_ns, before_mtime)
            # Race/refreeze still parks candidate evidence.
            cands = list((runs / "candidates").glob("*-production-path-smoke-pass.json"))
            self.assertGreaterEqual(len(cands), 1)

    def test_smoke_persist_freeze_b0_failure_candidate_only(self) -> None:
        """One-time B0 failure creates candidate only — no tracked proof."""
        with tempfile.TemporaryDirectory(prefix="rp-smoke-fail-") as td:
            runs = Path(td) / "runs"
            when = _dt.datetime(2026, 7, 23, 14, 0, 0, 99, tzinfo=_dt.timezone.utc)
            path, kind = self.run_eval.persist_production_path_smoke(
                {"status": "fail", "required_read_ok": False},
                runs_dir=runs,
                mode="freeze_b0",
                when=when,
            )
            self.assertEqual(kind, "candidate")
            self.assertEqual(path.parent.name, "candidates")
            self.assertIn("fail", path.name)
            self.assertFalse(self.run_eval.tracked_b0_smoke_path(runs).exists())

    def test_smoke_candidate_names_exclusive_and_gitignore_pattern(self) -> None:
        """Candidate basenames are distinct/exclusive; repo pattern ignores them."""
        with tempfile.TemporaryDirectory(prefix="rp-smoke-excl-") as td:
            runs = Path(td) / "runs"
            when = _dt.datetime(2026, 7, 23, 15, 0, 0, 0, tzinfo=_dt.timezone.utc)
            p1, _ = self.run_eval.persist_production_path_smoke(
                {"status": "pass"}, runs_dir=runs, mode="candidate", when=when
            )
            # Force collision on same stamp — helper must exclusive-create distinct file.
            p2, _ = self.run_eval.persist_production_path_smoke(
                {"status": "pass"}, runs_dir=runs, mode="candidate", when=when
            )
            self.assertNotEqual(p1, p2)
            self.assertTrue(p1.is_file() and p2.is_file())

        gi = (HARNESS / "runs" / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("*\n", gi if gi.endswith("\n") else gi + "\n")
        self.assertTrue(
            any(line.strip() == "*" for line in gi.splitlines()),
            "runs/.gitignore must ignore * so candidates/ stay local",
        )
        self.assertIn("!b0-production-path-smoke.json", gi)
        self.assertNotIn("!candidates", gi)
        # git check-ignore confirms candidate paths are ignored; tracked proof is not.
        import subprocess

        cand_rel = "optimization/reached-path/runs/candidates/example-production-path-smoke-pass.json"
        tracked_rel = "optimization/reached-path/runs/b0-production-path-smoke.json"
        cand_check = subprocess.run(
            ["git", "check-ignore", "-q", cand_rel],
            cwd=REPO,
            check=False,
        )
        self.assertEqual(cand_check.returncode, 0, "candidate path must be gitignored")
        tracked_check = subprocess.run(
            ["git", "check-ignore", "-q", tracked_rel],
            cwd=REPO,
            check=False,
        )
        self.assertEqual(
            tracked_check.returncode, 1, "tracked B0 proof must NOT be gitignored"
        )

    def test_smoke_cli_mode_wiring_deterministic(self) -> None:
        """CLI flags wire freeze_b0 vs candidate without a live model."""
        ap = self.run_eval.build_arg_parser()
        args_ord = ap.parse_args(["--production-path-smoke", "--model", "haiku"])
        self.assertTrue(args_ord.production_path_smoke)
        self.assertFalse(args_ord.freeze_b0_smoke)
        args_fr = ap.parse_args(["--freeze-b0-smoke"])
        self.assertTrue(args_fr.freeze_b0_smoke)
        self.assertFalse(args_fr.production_path_smoke)
        args_all = ap.parse_args(["--all", "--backend", "claude"])
        self.assertTrue(args_all.all)
        self.assertEqual(args_all.backend, "claude")

        calls: list[dict] = []

        def _stub_smoke(**kwargs):
            calls.append(kwargs)
            return 0

        with mock.patch.object(self.run_eval, "production_path_smoke", _stub_smoke):
            self.assertEqual(self.run_eval.main(["--production-path-smoke"]), 0)
            self.assertEqual(self.run_eval.main(["--freeze-b0-smoke"]), 0)
            with mock.patch.object(self.run_eval, "validate_b0", return_value=0):
                self.assertEqual(
                    self.run_eval.main(["--all", "--backend", "claude"]), 0
                )
        self.assertEqual(calls[0].get("freeze_b0"), False)
        self.assertEqual(calls[1].get("freeze_b0"), True)
        self.assertEqual(calls[2].get("freeze_b0"), False)

    def test_freeze_b0_smoke_refuses_existing_tracked_before_backend(self) -> None:
        """--freeze-b0-smoke refuses when tracked proof exists; no claude required."""
        with tempfile.TemporaryDirectory(prefix="rp-smoke-refuse-") as td:
            runs = Path(td) / "runs"
            runs.mkdir()
            tracked = self.run_eval.tracked_b0_smoke_path(runs)
            tracked.write_text('{"status":"pass"}\n', encoding="utf-8")
            before = tracked.read_bytes()
            # Ensure we would have skipped only due to tracked presence, not missing CLI.
            with mock.patch.object(self.run_eval.shutil, "which", return_value="/bin/claude"):
                rc = self.run_eval.production_path_smoke(
                    freeze_b0=True, runs_dir=runs, model="haiku", timeout=5
                )
            self.assertEqual(rc, 1)
            self.assertEqual(tracked.read_bytes(), before)
            self.assertFalse((runs / "candidates").exists())

    def _smoke_candidate_records(self, runs: Path) -> list[Path]:
        cand = runs / "candidates"
        if not cand.is_dir():
            return []
        return sorted(cand.glob("*-production-path-smoke-*.json"))

    def test_smoke_missing_claude_cli_ordinary_persists_candidate(self) -> None:
        """Missing CLI is invalid/non-run: nonzero + candidate evidence, no tracked proof."""
        when = _dt.datetime(2026, 7, 23, 16, 0, 0, 111111, tzinfo=_dt.timezone.utc)
        with tempfile.TemporaryDirectory(prefix="rp-smoke-no-cli-") as td:
            runs = Path(td) / "runs"
            with mock.patch.object(self.run_eval.shutil, "which", return_value=None):
                rc = self.run_eval.production_path_smoke(
                    freeze_b0=False,
                    runs_dir=runs,
                    model="haiku",
                    timeout=5,
                    when=when,
                )
            self.assertNotEqual(rc, 0)
            cands = self._smoke_candidate_records(runs)
            self.assertEqual(len(cands), 1)
            body = json.loads(cands[0].read_text(encoding="utf-8"))
            self.assertEqual(body["status"], "claude_cli_missing")
            self.assertIn("reason", body)
            self.assertTrue(str(body["reason"]).strip())
            self.assertEqual(body.get("baseline"), "B0")
            self.assertEqual(
                body.get("baseline_commit"), self.run_eval.BASELINE_COMMIT
            )
            dumped = json.dumps(body)
            self.assertNotIn("gordon@mickel.tech", dumped)
            self.assertNotIn("/Users/", dumped)
            self.assertFalse(self.run_eval.tracked_b0_smoke_path(runs).exists())
            self.assertIn("claude_cli_missing", cands[0].name)

    def test_smoke_missing_claude_cli_freeze_candidate_only(self) -> None:
        """Freeze + missing CLI: nonzero, candidate only — never creates tracked proof."""
        when = _dt.datetime(2026, 7, 23, 16, 1, 0, 222222, tzinfo=_dt.timezone.utc)
        with tempfile.TemporaryDirectory(prefix="rp-smoke-no-cli-fr-") as td:
            runs = Path(td) / "runs"
            with mock.patch.object(self.run_eval.shutil, "which", return_value=None):
                rc = self.run_eval.production_path_smoke(
                    freeze_b0=True,
                    runs_dir=runs,
                    model="haiku",
                    timeout=5,
                    when=when,
                )
            self.assertNotEqual(rc, 0)
            cands = self._smoke_candidate_records(runs)
            self.assertEqual(len(cands), 1)
            body = json.loads(cands[0].read_text(encoding="utf-8"))
            self.assertEqual(body["status"], "claude_cli_missing")
            self.assertFalse(self.run_eval.tracked_b0_smoke_path(runs).exists())

    def test_smoke_missing_claude_cli_preserves_existing_tracked(self) -> None:
        """Ordinary missing-CLI must not mutate an existing tracked B0 proof."""
        when = _dt.datetime(2026, 7, 23, 16, 2, 0, 333333, tzinfo=_dt.timezone.utc)
        with tempfile.TemporaryDirectory(prefix="rp-smoke-no-cli-trk-") as td:
            runs = Path(td) / "runs"
            runs.mkdir()
            tracked = self.run_eval.tracked_b0_smoke_path(runs)
            marker = b'{"status":"pass","immutable":true}\n'
            tracked.write_bytes(marker)
            before_mtime = tracked.stat().st_mtime_ns
            with mock.patch.object(self.run_eval.shutil, "which", return_value=None):
                rc = self.run_eval.production_path_smoke(
                    freeze_b0=False,
                    runs_dir=runs,
                    model="haiku",
                    timeout=5,
                    when=when,
                )
            self.assertNotEqual(rc, 0)
            self.assertEqual(tracked.read_bytes(), marker)
            self.assertEqual(tracked.stat().st_mtime_ns, before_mtime)
            self.assertEqual(len(self._smoke_candidate_records(runs)), 1)

    def _patch_smoke_backend(self, *, auth, leak=None, run_ret=None):
        """Stack mocks so smoke never hits a live model / long wait."""
        stack = ExitStack()
        stack.enter_context(
            mock.patch.object(self.run_eval.shutil, "which", return_value="/bin/claude")
        )
        stack.enter_context(
            mock.patch.object(self.run_eval.isolation, "auth_probe", return_value=auth)
        )
        if leak is not None:
            stack.enter_context(
                mock.patch.object(
                    self.run_eval.isolation,
                    "instruction_leak_probe",
                    return_value=leak,
                )
            )
        if run_ret is not None:
            stack.enter_context(
                mock.patch.object(
                    self.run_eval.isolation, "run_cmd", return_value=run_ret
                )
            )
            stack.enter_context(
                mock.patch.object(self.run_eval, "_claude_version", return_value="test")
            )
        return stack

    def test_smoke_auth_leak_timeout_backend_candidate_only(self) -> None:
        """Auth/leak/timeout/backend failures stay nonzero candidate-only (mocked)."""
        when = _dt.datetime(2026, 7, 23, 17, 0, 0, 0, tzinfo=_dt.timezone.utc)
        auth_ok = {
            "ok": True,
            "invalid": False,
            "reason": "ok",
            "flags": [],
            "used_bare": False,
            "used_fresh_config_dir": False,
        }
        leak_ok = {"ok": True, "leaked": False, "needles": []}
        cases = (
            (
                "invalid_auth",
                {"ok": False, "invalid": True, "reason": "zero_token"},
                None,
                None,
            ),
            (
                "invalid_leak_probe",
                auth_ok,
                {"ok": False, "leaked": True, "needles": ["Owner block"]},
                None,
            ),
            ("timeout", auth_ok, leak_ok, (0, "", "", True)),
            ("backend_error", auth_ok, leak_ok, (2, "", "backend blew up", False)),
        )
        for expected_status, auth, leak, run_ret in cases:
            with self.subTest(status=expected_status):
                with tempfile.TemporaryDirectory(prefix="rp-smoke-fail-") as td:
                    runs = Path(td) / "runs"
                    runs.mkdir()
                    tracked = self.run_eval.tracked_b0_smoke_path(runs)
                    marker = b'{"status":"pass","keep":true}\n'
                    tracked.write_bytes(marker)
                    before_mtime = tracked.stat().st_mtime_ns
                    with self._patch_smoke_backend(
                        auth=auth, leak=leak, run_ret=run_ret
                    ):
                        rc = self.run_eval.production_path_smoke(
                            freeze_b0=False,
                            runs_dir=runs,
                            model="haiku",
                            timeout=5,
                            when=when,
                        )
                    self.assertNotEqual(rc, 0)
                    cands = self._smoke_candidate_records(runs)
                    self.assertEqual(len(cands), 1)
                    body = json.loads(cands[0].read_text(encoding="utf-8"))
                    self.assertEqual(body["status"], expected_status)
                    self.assertEqual(tracked.read_bytes(), marker)
                    self.assertEqual(tracked.stat().st_mtime_ns, before_mtime)

                with tempfile.TemporaryDirectory(prefix="rp-smoke-fail-fr-") as td2:
                    runs2 = Path(td2) / "runs"
                    with self._patch_smoke_backend(
                        auth=auth, leak=leak, run_ret=run_ret
                    ):
                        rc2 = self.run_eval.production_path_smoke(
                            freeze_b0=True,
                            runs_dir=runs2,
                            model="haiku",
                            timeout=5,
                            when=when,
                        )
                    self.assertNotEqual(rc2, 0)
                    self.assertFalse(
                        self.run_eval.tracked_b0_smoke_path(runs2).exists()
                    )
                    self.assertEqual(len(self._smoke_candidate_records(runs2)), 1)


if __name__ == "__main__":
    unittest.main()
