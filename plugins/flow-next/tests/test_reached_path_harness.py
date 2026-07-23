"""fn-130.1: reached-path harness self-tests (CI).

Exercises the actual optimization/reached-path modules — character algorithm,
ratchet policy, privacy scrub, isolation tripwires, and trace parsing —
including at least one active direct-reference activation and one cold
forbidden-reference non-read (deterministic trace fixture, no live model).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

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
        """Nonempty temp target without INDEX refuses; contents unchanged before HEAD."""
        with tempfile.TemporaryDirectory(prefix="rp-freeze-nonempty-") as td:
            out = Path(td) / "b0"
            out.mkdir()
            leftover = out / "plan" / "p1-flow-native.json"
            leftover.parent.mkdir(parents=True)
            marker = b'{"leftover": true}\n'
            leftover.write_bytes(marker)
            # Do not monkeypatch HEAD — nonempty guard must fire first.
            resolve_calls: list[object] = []
            real_resolve = self.run_eval.resolve_git_head

            def _track_head(*args, **kwargs):
                resolve_calls.append((args, kwargs))
                return real_resolve(*args, **kwargs)

            self.run_eval.resolve_git_head = _track_head  # type: ignore[method-assign]
            try:
                rc = self.run_eval.freeze_b0(output_dir=out)
            finally:
                self.run_eval.resolve_git_head = real_resolve  # type: ignore[method-assign]
            self.assertEqual(rc, 1)
            self.assertEqual(resolve_calls, [], "nonempty guard must precede HEAD resolve")
            self.assertFalse((out / "INDEX.json").exists())
            self.assertEqual(leftover.read_bytes(), marker)
            # No extra freeze artifacts beside the leftover tree.
            written = sorted(p for p in out.rglob("*") if p.is_file())
            self.assertEqual(written, [leftover])

    def test_freeze_b0_refuses_head_mismatch_before_writes(self) -> None:
        """HEAD != BASELINE_COMMIT refuses bootstrap; temp output stays empty."""
        with tempfile.TemporaryDirectory(prefix="rp-freeze-") as td:
            out = Path(td) / "b0"
            # Seam: absent output + wrong HEAD must not create INDEX or dirs.
            real_resolve = self.run_eval.resolve_git_head

            def _wrong_head(_repo_root=None):
                return "0" * 40

            self.run_eval.resolve_git_head = _wrong_head  # type: ignore[method-assign]
            try:
                rc = self.run_eval.freeze_b0(output_dir=out)
            finally:
                self.run_eval.resolve_git_head = real_resolve  # type: ignore[method-assign]
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())
            self.assertFalse((out / "INDEX.json").exists())

    def test_freeze_b0_bootstraps_absent_temp_at_exact_baseline(self) -> None:
        """Temp seam: exact baseline + absent dir bootstraps from git-show sources."""
        with tempfile.TemporaryDirectory(prefix="rp-freeze-ok-") as td:
            out = Path(td) / "b0"
            real_resolve = self.run_eval.resolve_git_head
            baseline = self.run_eval.BASELINE_COMMIT

            def _baseline_head(_repo_root=None):
                return baseline

            self.run_eval.resolve_git_head = _baseline_head  # type: ignore[method-assign]
            try:
                rc = self.run_eval.freeze_b0(output_dir=out)
            finally:
                self.run_eval.resolve_git_head = real_resolve  # type: ignore[method-assign]
            self.assertEqual(rc, 0)
            self.assertTrue((out / "INDEX.json").is_file())
            index = json.loads((out / "INDEX.json").read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
