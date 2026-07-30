"""PR cognitive-aid v1 validation, persistence, rendering, and budget tests."""

import hashlib
import json
import statistics
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SPEC_ID = "fn-136-cognitive-aid"
GOLDEN = (
    REPO_ROOT
    / "plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.json"
)
GOLDEN_META = GOLDEN.with_name("golden.meta.json")


def artifact(*, canonical_files: int = 2, churn: int = 40) -> dict:
    sources = [
        {"id": "spec", "kind": "spec", "ref": SPEC_ID},
        {"id": "task", "kind": "task", "ref": f"{SPEC_ID}.1"},
        {"id": "rid", "kind": "rid", "ref": "R6"},
        {"id": "diff", "kind": "diff_metadata", "ref": f"{BASE_SHA}..{HEAD_SHA}"},
        {"id": "commit", "kind": "commit", "ref": HEAD_SHA},
    ]
    files = []
    for index in range(canonical_files):
        files.append(
            {
                "path": f"src/change_{index}.py",
                "changeType": "modified",
                "attentionClass": "canonical",
                "summary": f"Implements bounded behavior {index}.",
                "additions": churn,
                "deletions": 0,
                "diffUrl": f"https://github.com/acme/repo/pull/1/files#diff-{index}",
                "sourceRefs": ["diff", "task", "rid"],
                "rIds": ["R6"],
                "taskIds": [f"{SPEC_ID}.1"],
            }
        )
    files.extend(
        [
            {
                "path": "plugins/flow-next/codex/generated.md",
                "changeType": "modified",
                "attentionClass": "generated",
                "summary": "Regenerated mirror.",
                "additions": 500,
                "deletions": 500,
                "sourceRefs": ["diff"],
                "rIds": [],
                "taskIds": [],
            },
            {
                "path": ".flow/bin/flowctl.py",
                "changeType": "modified",
                "attentionClass": "mechanical",
                "summary": "Byte-identical distribution copy.",
                "additions": 500,
                "deletions": 500,
                "sourceRefs": ["diff"],
                "rIds": [],
                "taskIds": [],
            },
        ]
    )
    return {
        "schemaVersion": 1,
        "artifactId": "aid-001",
        "specId": SPEC_ID,
        "baseSha": BASE_SHA,
        "headSha": HEAD_SHA,
        "generatedAt": "2026-07-30T12:00:00Z",
        "sources": sources,
        "changeWalkthrough": {
            "thesis": "Preserve one grounded, intent-ordered explanation.",
            "proof": [
                {
                    "label": "Head commit",
                    "value": HEAD_SHA[:7],
                    "sourceRefs": ["commit"],
                },
                {
                    "label": "Verification",
                    "value": "42 tests",
                    "sourceRefs": ["task"],
                },
            ],
            "groups": [
                {
                    "ordinal": 1,
                    "kind": "problem",
                    "title": "Why this changes",
                    "summary": "Free prose is not portable.",
                    "sourceRefs": ["spec", "rid"],
                    "rIds": ["R6"],
                    "taskIds": [],
                    "files": [],
                },
                {
                    "ordinal": 2,
                    "kind": "principle",
                    "title": "One source table",
                    "summary": "Every semantic claim resolves to evidence.",
                    "sourceRefs": ["spec"],
                    "rIds": [],
                    "taskIds": [],
                    "files": [],
                },
                {
                    "ordinal": 3,
                    "kind": "step",
                    "title": "Validate and render",
                    "summary": "Separate Git state from review attention.",
                    "sourceRefs": ["task", "rid"],
                    "rIds": ["R6"],
                    "taskIds": [f"{SPEC_ID}.1"],
                    "files": files,
                },
                {
                    "ordinal": 4,
                    "kind": "kept",
                    "title": "Tracker facade",
                    "summary": "PR creation still precedes tracker projection.",
                    "sourceRefs": ["spec"],
                    "rIds": [],
                    "taskIds": [],
                    "files": [],
                },
                {
                    "ordinal": 5,
                    "kind": "verify",
                    "title": "Verification and ship",
                    "summary": "Recorded task evidence remains authoritative.",
                    "sourceRefs": ["task"],
                    "rIds": [],
                    "taskIds": [f"{SPEC_ID}.1"],
                    "files": [],
                },
            ],
        },
    }


def artifact_diff_files(value: dict) -> dict[str, tuple[str, int, int]]:
    return {
        item["path"]: (
            item["changeType"],
            item.get("additions"),
            item.get("deletions"),
        )
        for group in value["changeWalkthrough"]["groups"]
        for item in group["files"]
    }


class ValidationTests(unittest.TestCase):
    def test_valid_contract_preserves_separate_change_and_attention_dimensions(self) -> None:
        value = artifact()
        self.assertIs(flowctl.validate_pr_cognitive_aid(value), value)
        generated = value["changeWalkthrough"]["groups"][2]["files"][-2]
        self.assertEqual(generated["changeType"], "modified")
        self.assertEqual(generated["attentionClass"], "generated")

    def test_rejects_unsafe_ungrounded_and_unrelated_claims(self) -> None:
        cases = []
        unsafe = artifact()
        unsafe["changeWalkthrough"]["groups"][2]["files"][0]["path"] = "../secret"
        cases.append((unsafe, "traversal"))
        ungrounded = artifact()
        ungrounded["changeWalkthrough"]["groups"][2]["sourceRefs"] = []
        cases.append((ungrounded, "ground"))
        unrelated = artifact()
        unrelated["changeWalkthrough"]["groups"][2]["files"][0]["sourceRefs"] = [
            "diff"
        ]
        cases.append((unrelated, "same-record"))
        for value, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    flowctl.PrCognitiveAidValidationError, message
                ):
                    flowctl.validate_pr_cognitive_aid(value)

    def test_source_kinds_are_bound_to_artifact_identity(self) -> None:
        mutations = []
        wrong_spec = artifact()
        wrong_spec["sources"][0]["ref"] = "fn-999-other"
        mutations.append((wrong_spec, "artifact.specId"))
        wrong_task = artifact()
        wrong_task["sources"][1]["ref"] = "fn-999-other.1"
        mutations.append((wrong_task, "task of artifact.specId"))
        wrong_rid = artifact()
        wrong_rid["sources"][2]["ref"] = "requirement-six"
        mutations.append((wrong_rid, "canonical R-ID"))
        wrong_diff = artifact()
        wrong_diff["sources"][3]["ref"] = f"{BASE_SHA}..{'c' * 40}"
        mutations.append((wrong_diff, "baseSha..headSha"))
        wrong_commit = artifact()
        wrong_commit["sources"][4]["ref"] = "not-a-sha"
        mutations.append((wrong_commit, "Git SHA"))
        missing_diff = artifact()
        missing_diff["changeWalkthrough"]["groups"][2]["files"][0][
            "sourceRefs"
        ] = ["task", "rid"]
        mutations.append((missing_diff, "diff_metadata"))
        for value, message in mutations:
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    flowctl.PrCognitiveAidValidationError, message
                ):
                    flowctl.validate_pr_cognitive_aid(value)

    def test_file_membership_status_and_churn_match_bound_diff(self) -> None:
        value = artifact()
        expected = artifact_diff_files(value)
        flowctl.validate_pr_cognitive_aid(value, expected_diff_files=expected)
        mutations = []
        nonexistent = artifact()
        nonexistent["changeWalkthrough"]["groups"][2]["files"][0][
            "path"
        ] = "src/not-in-diff.py"
        mutations.append((nonexistent, "does not belong"))
        wrong_status = artifact()
        wrong_status["changeWalkthrough"]["groups"][2]["files"][0][
            "changeType"
        ] = "added"
        mutations.append((wrong_status, "do not match"))
        wrong_churn = artifact()
        wrong_churn["changeWalkthrough"]["groups"][2]["files"][0][
            "additions"
        ] += 1
        mutations.append((wrong_churn, "do not match"))
        for candidate, message in mutations:
            with self.subTest(message=message), self.assertRaisesRegex(
                flowctl.PrCognitiveAidValidationError, message
            ):
                flowctl.validate_pr_cognitive_aid(
                    candidate, expected_diff_files=expected
                )

    def test_raw_input_is_bounded_before_json_decode(self) -> None:
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(b" " * (flowctl.PR_COGNITIVE_AID_MAX_BYTES + 1))
            handle.flush()
            with redirect_stdout(StringIO()), self.assertRaises(SystemExit):
                flowctl._pr_aid_read_input(handle.name)

    def test_rejects_windows_reserved_artifact_filenames(self) -> None:
        for reserved in ("CON", "nul", "LPT1.json", "com9"):
            with self.subTest(reserved=reserved):
                value = artifact()
                value["artifactId"] = reserved
                with self.assertRaisesRegex(
                    flowctl.PrCognitiveAidValidationError,
                    "Windows reserved filename",
                ):
                    flowctl.validate_pr_cognitive_aid(value)

    def test_rejects_bounds_order_cardinality_and_oversize_without_truncation(self) -> None:
        no_step = artifact()
        no_step["changeWalkthrough"]["groups"] = [
            group
            for group in no_step["changeWalkthrough"]["groups"]
            if group["kind"] != "step"
        ]
        with self.assertRaisesRegex(
            flowctl.PrCognitiveAidValidationError, "1-7 step"
        ):
            flowctl.validate_pr_cognitive_aid(no_step)

        wrong_order = artifact()
        wrong_order["changeWalkthrough"]["groups"][0]["kind"] = "verify"
        with self.assertRaisesRegex(
            flowctl.PrCognitiveAidValidationError, "logical group order"
        ):
            flowctl.validate_pr_cognitive_aid(wrong_order)

        oversize = artifact()
        oversize["changeWalkthrough"]["thesis"] = "x" * (512 * 1024)
        with self.assertRaisesRegex(
            flowctl.PrCognitiveAidValidationError, "encoded payload exceeds"
        ):
            flowctl.validate_pr_cognitive_aid(oversize)
        self.assertEqual(
            len(oversize["changeWalkthrough"]["thesis"]), 512 * 1024
        )

    def test_collection_and_string_bounds_are_executable(self) -> None:
        mutations = []

        too_many_sources = artifact()
        source_template = too_many_sources["sources"][0]
        too_many_sources["sources"] = [
            {**source_template, "id": f"source-{index}"}
            for index in range(129)
        ]
        mutations.append((too_many_sources, "128"))

        too_many_proof = artifact()
        proof_template = too_many_proof["changeWalkthrough"]["proof"][0]
        too_many_proof["changeWalkthrough"]["proof"] = [
            {**proof_template, "label": f"proof-{index}"} for index in range(17)
        ]
        mutations.append((too_many_proof, "16"))

        too_many_refs = artifact()
        too_many_refs["changeWalkthrough"]["groups"][2]["sourceRefs"] = [
            "task"
        ] * 33
        mutations.append((too_many_refs, "32"))

        long_title = artifact()
        long_title["changeWalkthrough"]["groups"][2]["title"] = "x" * 161
        mutations.append((long_title, "160"))

        long_group_summary = artifact()
        long_group_summary["changeWalkthrough"]["groups"][2]["summary"] = (
            "x" * 1001
        )
        mutations.append((long_group_summary, "1000"))

        long_file_summary = artifact()
        long_file_summary["changeWalkthrough"]["groups"][2]["files"][0][
            "summary"
        ] = "x" * 501
        mutations.append((long_file_summary, "500"))

        unsafe_url = artifact()
        unsafe_url["changeWalkthrough"]["groups"][2]["files"][0][
            "diffUrl"
        ] = "http://example.test/diff"
        mutations.append((unsafe_url, "HTTPS"))

        legacy_field = artifact()
        legacy_field["legacyWalkthrough"] = {"summary": "parallel truth"}
        mutations.append((legacy_field, "unknown fields"))

        for value, message in mutations:
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    flowctl.PrCognitiveAidValidationError, message
                ):
                    flowctl.validate_pr_cognitive_aid(value)


class PersistenceAndCurrentnessTests(unittest.TestCase):
    def test_immutable_generations_form_a_materialized_supersedes_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            first = artifact()
            first_path = flowctl.write_pr_cognitive_aid(
                flow_dir,
                first,
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
            )
            second = artifact()
            second["artifactId"] = "aid-002"
            second["generatedAt"] = "2026-07-30T12:01:00Z"
            second["supersedesArtifactId"] = "aid-001"
            second_path = flowctl.write_pr_cognitive_aid(
                flow_dir,
                second,
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
            )
            self.assertTrue(first_path.is_file())
            self.assertTrue(second_path.is_file())
            current = flowctl.select_current_pr_cognitive_aid(
                flow_dir, SPEC_ID, base_sha=BASE_SHA, head_sha=HEAD_SHA
            )
            self.assertEqual(current["status"], "current")
            self.assertEqual(current["artifact"]["artifactId"], "aid-002")
            with self.assertRaisesRegex(
                flowctl.PrCognitiveAidValidationError, "already exists"
            ):
                flowctl.write_pr_cognitive_aid(
                    flow_dir,
                    second,
                    spec_id=SPEC_ID,
                    base_sha=BASE_SHA,
                    head_sha=HEAD_SHA,
                )

    def test_stale_or_invalid_artifact_never_supplies_current_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            flowctl.write_pr_cognitive_aid(
                flow_dir,
                artifact(),
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
            )
            stale = flowctl.select_current_pr_cognitive_aid(
                flow_dir, SPEC_ID, base_sha="c" * 40, head_sha=HEAD_SHA
            )
            self.assertEqual(stale["status"], "stale")
            self.assertIsNone(stale["artifact"])

    def test_newer_stale_chain_tip_invalidates_older_matching_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            first = artifact()
            flowctl.write_pr_cognitive_aid(
                flow_dir,
                first,
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
            )
            second = artifact()
            second.update(
                {
                    "artifactId": "aid-002",
                    "generatedAt": "2026-07-30T12:01:00Z",
                    "supersedesArtifactId": "aid-001",
                    "headSha": "c" * 40,
                }
            )
            second["sources"][3]["ref"] = f"{BASE_SHA}..{'c' * 40}"
            flowctl.write_pr_cognitive_aid(
                flow_dir,
                second,
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha="c" * 40,
            )
            current = flowctl.select_current_pr_cognitive_aid(
                flow_dir, SPEC_ID, base_sha=BASE_SHA, head_sha=HEAD_SHA
            )
            self.assertEqual(current["status"], "stale")
            self.assertIsNone(current["artifact"])
            self.assertEqual(current["latestArtifactId"], "aid-002")

    def test_current_tip_diff_validation_does_not_revalidate_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            first = artifact(canonical_files=2, churn=40)
            flowctl.write_pr_cognitive_aid(
                flow_dir,
                first,
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
                expected_diff_files=artifact_diff_files(first),
            )

            next_head_sha = "c" * 40
            second = artifact(canonical_files=1, churn=17)
            second.update(
                {
                    "artifactId": "aid-002",
                    "generatedAt": "2026-07-30T12:01:00Z",
                    "supersedesArtifactId": "aid-001",
                    "headSha": next_head_sha,
                }
            )
            second["sources"][3]["ref"] = f"{BASE_SHA}..{next_head_sha}"
            second["sources"][4]["ref"] = next_head_sha
            second["changeWalkthrough"]["proof"][0]["value"] = next_head_sha[:7]
            second_diff = artifact_diff_files(second)
            flowctl.write_pr_cognitive_aid(
                flow_dir,
                second,
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=next_head_sha,
                expected_diff_files=second_diff,
            )

            current = flowctl.select_current_pr_cognitive_aid(
                flow_dir,
                SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=next_head_sha,
                expected_diff_files=second_diff,
            )
            self.assertEqual(current["status"], "current")
            self.assertEqual(current["artifact"]["artifactId"], "aid-002")

    def test_invalid_or_unsupported_home_never_projects_current_data(self) -> None:
        cases = {}
        malformed = artifact()
        malformed["artifactId"] = "aid-002"
        malformed["supersedesArtifactId"] = "missing"
        cases["dangling"] = (malformed, "invalid")

        unsupported = artifact()
        unsupported["schemaVersion"] = 2
        unsupported["artifactId"] = "aid-002"
        unsupported["supersedesArtifactId"] = "aid-001"
        cases["unsupported"] = (unsupported, "unsupported")

        for name, (second, expected_status) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                flow_dir = Path(tmp) / ".flow"
                home = flowctl._pr_cognitive_aid_home(flow_dir, SPEC_ID)
                home.mkdir(parents=True)
                first = artifact()
                (home / "aid-001.json").write_text(
                    flowctl._pr_aid_serialized_text(first), encoding="utf-8"
                )
                (home / "aid-002.json").write_text(
                    flowctl._pr_aid_serialized_text(second), encoding="utf-8"
                )
                current = flowctl.select_current_pr_cognitive_aid(
                    flow_dir, SPEC_ID, base_sha=BASE_SHA, head_sha=HEAD_SHA
                )
                self.assertEqual(current["status"], expected_status)
                self.assertIsNone(current["artifact"])

    def test_chain_forks_cycles_and_filename_mismatches_are_invalid(self) -> None:
        def write(home: Path, name: str, value: dict) -> None:
            (home / name).write_text(
                flowctl._pr_aid_serialized_text(value), encoding="utf-8"
            )

        for case in ("fork", "cycle", "filename"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                flow_dir = Path(tmp) / ".flow"
                home = flowctl._pr_cognitive_aid_home(flow_dir, SPEC_ID)
                home.mkdir(parents=True)
                first = artifact()
                if case == "filename":
                    write(home, "wrong-name.json", first)
                elif case == "fork":
                    write(home, "aid-001.json", first)
                    for suffix in ("002", "003"):
                        child = artifact()
                        child["artifactId"] = f"aid-{suffix}"
                        child["supersedesArtifactId"] = "aid-001"
                        write(home, f"aid-{suffix}.json", child)
                else:
                    first["supersedesArtifactId"] = "aid-002"
                    second = artifact()
                    second["artifactId"] = "aid-002"
                    second["supersedesArtifactId"] = "aid-001"
                    write(home, "aid-001.json", first)
                    write(home, "aid-002.json", second)
                result = flowctl.select_current_pr_cognitive_aid(
                    flow_dir, SPEC_ID, base_sha=BASE_SHA, head_sha=HEAD_SHA
                )
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["artifact"])

    def test_oversize_persisted_generation_is_rejected_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            home = flowctl._pr_cognitive_aid_home(flow_dir, SPEC_ID)
            home.mkdir(parents=True)
            (home / "oversize.json").write_bytes(
                b" " * (flowctl.PR_COGNITIVE_AID_MAX_BYTES + 1)
            )
            result = flowctl.select_current_pr_cognitive_aid(
                flow_dir, SPEC_ID, base_sha=BASE_SHA, head_sha=HEAD_SHA
            )
            self.assertEqual(result["status"], "invalid")
            self.assertIsNone(result["artifact"])
            self.assertIn("encoded payload exceeds", result["rejected"][0])

    def test_selection_serializes_with_concurrent_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".flow"
            first = artifact()
            flowctl.write_pr_cognitive_aid(
                flow_dir,
                first,
                spec_id=SPEC_ID,
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
            )
            second = artifact()
            second["artifactId"] = "aid-002"
            second["supersedesArtifactId"] = "aid-001"
            second["generatedAt"] = "2026-07-30T12:01:00Z"
            entered_publish = threading.Event()
            release_publish = threading.Event()
            selected: list[dict] = []
            original_atomic_create = flowctl.atomic_create

            def blocked_create(path: Path, content: str) -> None:
                entered_publish.set()
                self.assertTrue(release_publish.wait(timeout=2))
                original_atomic_create(path, content)

            with mock.patch.object(
                flowctl, "atomic_create", side_effect=blocked_create
            ):
                writer = threading.Thread(
                    target=flowctl.write_pr_cognitive_aid,
                    kwargs={
                        "flow_dir": flow_dir,
                        "artifact": second,
                        "spec_id": SPEC_ID,
                        "base_sha": BASE_SHA,
                        "head_sha": HEAD_SHA,
                    },
                )
                reader = threading.Thread(
                    target=lambda: selected.append(
                        flowctl.select_current_pr_cognitive_aid(
                            flow_dir,
                            SPEC_ID,
                            base_sha=BASE_SHA,
                            head_sha=HEAD_SHA,
                        )
                    )
                )
                writer.start()
                self.assertTrue(entered_publish.wait(timeout=2))
                reader.start()
                time.sleep(0.05)
                self.assertFalse(selected)
                release_publish.set()
                writer.join(timeout=2)
                reader.join(timeout=2)
            self.assertEqual(selected[0]["artifact"]["artifactId"], "aid-002")


class MarkdownAndBudgetTests(unittest.TestCase):
    def test_compact_form_uses_only_canonical_files(self) -> None:
        rendered = flowctl.render_pr_cognitive_aid_markdown(
            artifact(canonical_files=2, churn=20)
        )
        self.assertIn("## The change, top to bottom", rendered)
        self.assertIn("src/change_0.py", rendered)
        self.assertNotIn("generated.md", rendered)
        self.assertNotIn("**Legend:**", rendered)

    def test_full_form_has_complete_legend_groups_and_collapsed_noise(self) -> None:
        rendered = flowctl.render_pr_cognitive_aid_markdown(
            artifact(canonical_files=6, churn=1)
        )
        for badge in (
            "WHY",
            "PRINCIPLE",
            "STEP",
            "KEPT",
            "VERIFY",
            "NEW",
            "MODIFIED",
            "DELETED",
            "RENAMED",
            "COPIED",
            "CANONICAL",
            "GENERATED",
            "MECHANICAL",
        ):
            self.assertIn(f"`{badge}`", rendered)
        self.assertEqual(rendered.count("<details open>"), 1)
        self.assertIn("<summary>Generated/mechanical files (2)</summary>", rendered)
        self.assertIn("Tracker facade", rendered)
        self.assertIn("Verification and ship", rendered)
        self.assertNotIn("@@", rendered)

    def test_badges_order_provenance_metrics_and_plain_text_are_deterministic(self) -> None:
        value = artifact(canonical_files=6, churn=1)
        files = value["changeWalkthrough"]["groups"][2]["files"]
        files[0]["changeType"] = "added"
        files[0]["summary"] = "</summary>`[misleading](https://bad.test)"
        files.insert(0, files.pop(-2))
        rendered = flowctl.render_pr_cognitive_aid_markdown(value)
        self.assertIn("| `NEW` |", rendered)
        self.assertIn("Human-review lines", rendered)
        self.assertIn("Canonical files", rendered)
        self.assertIn("Total files", rendered)
        self.assertIn("source:diff", rendered)
        self.assertIn("R-ID:R6", rendered)
        self.assertIn("task:fn-136-cognitive-aid.1", rendered)
        self.assertIn("&lt;/summary&gt;", rendered)
        self.assertIn("&#96;", rendered)
        self.assertLess(rendered.index("generated.md"), rendered.index("change_0.py"))

    def test_thesis_cannot_inject_markdown_block_structure(self) -> None:
        cases = {
            "heading": "## Review plan",
            "list": "- claimed verification",
            "ordered": "1. fake evidence",
            "rule": "---",
            "fence": "```python",
        }
        for name, thesis in cases.items():
            with self.subTest(name=name):
                value = artifact()
                value["changeWalkthrough"]["thesis"] = thesis
                rendered = flowctl.render_pr_cognitive_aid_markdown(value)
                first_body_line = rendered.splitlines()[2]
                self.assertNotEqual(first_body_line, thesis)

    def test_html_input_is_lossless_and_script_safe(self) -> None:
        value = artifact()
        value["changeWalkthrough"]["thesis"] = "</script><script>alert('&')</script>"
        carrier = flowctl.render_pr_cognitive_aid_html_input(value)
        self.assertNotIn("</script><script>", carrier)
        self.assertIn("\\u003c/script\\u003e", carrier)
        encoded = carrier.split(">", 1)[1].rsplit("</script>", 1)[0]
        self.assertEqual(json.loads(encoded), value)

    def test_validation_plus_render_p95_under_100_ms_for_30_warm_runs(self) -> None:
        maximum_normal = json.loads(GOLDEN.read_text(encoding="utf-8"))
        metadata = json.loads(GOLDEN_META.read_text(encoding="utf-8"))
        encoded = GOLDEN.read_bytes()
        groups = maximum_normal["changeWalkthrough"]["groups"]
        files = [item for group in groups for item in group["files"]]
        self.assertEqual(len(maximum_normal["sources"]), 128)
        self.assertEqual(len(maximum_normal["changeWalkthrough"]["proof"]), 16)
        self.assertEqual(len(groups), 11)
        self.assertEqual(len(files), 500)
        self.assertLessEqual(len(encoded), flowctl.PR_COGNITIVE_AID_MAX_BYTES)
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), metadata["sha256"])
        self.assertEqual(metadata["schemaVersion"], 1)
        self.assertEqual(metadata["sourcePath"], GOLDEN.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(
            metadata["performanceBudget"],
            {
                "operation": "validation-plus-markdown-render",
                "p95MillisecondsExclusive": 100,
                "warmRuns": 30,
            },
        )
        for _ in range(5):
            flowctl.render_pr_cognitive_aid_markdown(maximum_normal)
        durations_ms = []
        for _ in range(30):
            started = time.perf_counter()
            flowctl.render_pr_cognitive_aid_markdown(maximum_normal)
            durations_ms.append((time.perf_counter() - started) * 1000)
        p95 = statistics.quantiles(durations_ms, n=20, method="inclusive")[18]
        self.assertLess(
            p95,
            metadata["performanceBudget"]["p95MillisecondsExclusive"],
            f"p95={p95:.3f} ms",
        )


class MakePrIntegrationTests(unittest.TestCase):
    def test_artifact_precedes_body_and_tracker_pr_url_boundary_is_unchanged(self) -> None:
        workflow = (
            REPO_ROOT
            / "plugins/flow-next/skills/flow-next-make-pr/workflow.md"
        ).read_text(encoding="utf-8")
        artifact_reference = (
            REPO_ROOT
            / "plugins/flow-next/skills/flow-next-make-pr/pr-cognitive-aid.md"
        ).read_text(encoding="utf-8")
        finalize = (
            REPO_ROOT
            / "plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md"
        ).read_text(encoding="utf-8")
        self.assertLess(
            workflow.index("## Phase 1.5: Structured PR cognitive-aid"),
            workflow.index("## Phase 1.5b: HTML render lens"),
        )
        self.assertLess(
            workflow.index("## Phase 1.5b: HTML render lens"),
            workflow.index("## Phase 2: Render body header sections"),
        )
        self.assertIn(
            "This phase ends before PR creation", artifact_reference
        )
        self.assertNotIn("skill: flow-next-tracker-sync", artifact_reference)
        self.assertIn('PR_URL=""', finalize)
        self.assertIn("--pr-url \"$PR_URL\"", finalize)
        self.assertIn("--op reconcile", finalize)
        self.assertIn("sync check", finalize)
        self.assertIn("Retro-fire", finalize)


if __name__ == "__main__":
    unittest.main()
