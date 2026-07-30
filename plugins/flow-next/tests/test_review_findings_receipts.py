"""Receipt-write integration, currentness, and local-budget tests (fn-136.3)."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "plugins" / "flow-next" / "scripts"))
FLOWCTL_PATH = REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"
QA_WORKFLOW = (
    REPO
    / "plugins"
    / "flow-next"
    / "skills"
    / "flow-next-qa"
    / "workflow.md"
)
CORPUS = REPO / "optimization" / "reached-path" / "fixtures" / "review-findings" / "v1"
SPEC = importlib.util.spec_from_file_location("flowctl_findings_receipts", FLOWCTL_PATH)
assert SPEC and SPEC.loader
FLOWCTL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FLOWCTL
SPEC.loader.exec_module(FLOWCTL)

BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
FINDINGS_P95_BUDGET_MS = 50.0


def _fixture(backend: str, name: str = "catalog-sample") -> str:
    return (CORPUS / backend / f"{name}.md").read_text(encoding="utf-8")


def _container(
    *,
    receipt_id: str,
    backend: str = "codex",
    kind: str = "implementation",
    round_number: int = 1,
    head_sha: str = HEAD_SHA,
    prior: dict | None = None,
) -> dict:
    return FLOWCTL.parse_review_findings(
        _fixture(backend, "catalog-sample"),
        source_receipt_id=receipt_id,
        review_kind=kind,
        backend=backend,
        round_number=round_number,
        base_sha=BASE_SHA,
        head_sha=head_sha,
        supersedes_receipt_id=(
            prior["sourceReceiptId"] if prior is not None else None
        ),
        prior_findings=prior,
        anchor_side="head",
    )


def _review_text(review_type: str, backend: str) -> str:
    if review_type == "impl_review":
        return _fixture(backend)
    if review_type == "plan_review":
        return """## Issue
- **Severity**: Major
- **Confidence**: 100
- **Classification**: introduced
- **Location**: Task acceptance
- **Problem**: The acceptance is not testable.
- **Suggestion**: Add an executable assertion.
<verdict>NEEDS_WORK</verdict>
"""
    return """## Gap
- **Severity**: Critical
- **Requirement**: R1 receipt integration
- **Status**: Partial
- **Confidence**: 100
- **Classification**: introduced
- **Evidence**: The QA writer is not integrated.
<verdict>NEEDS_WORK</verdict>
"""


def _qa_review_renderer_script() -> str:
    source = QA_WORKFLOW.read_text(encoding="utf-8")
    marker = '$PY - "$QA_REVIEW_FILE" "${PRIOR_RECEIPT:-}" <<\'PY\'\n'
    return source.split(marker, 1)[1].split("\nPY\n", 1)[0]


class ReviewFindingsReceiptIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.repo,
            check=True,
        )
        (self.repo / "tracked.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.repo, check=True)
        self.previous_cwd = Path.cwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        os.chdir(self.previous_cwd)
        self.temp.cleanup()

    def test_shared_writer_attaches_every_backend_and_review_kind(self) -> None:
        type_to_kind = {
            "impl_review": "implementation",
            "plan_review": "plan",
            "completion_review": "completion",
        }
        for backend in ("codex", "copilot", "cursor"):
            for review_type, review_kind in type_to_kind.items():
                with self.subTest(backend=backend, review_type=review_type):
                    receipt = self.repo / f"{backend}-{review_type}.json"
                    FLOWCTL._write_backend_review_receipt(
                        str(receipt),
                        review_type=review_type,
                        review_id="fn-136.3",
                        backend=backend,
                        verdict="NEEDS_WORK",
                        session_id="session",
                        effective_model="model",
                        effective_effort="high",
                        resolved_spec=FLOWCTL.BackendSpec(backend, "model", "high"),
                        review_text=_review_text(review_type, backend),
                        include_effort=True,
                        base_branch="HEAD",
                    )
                    data = json.loads(receipt.read_text(encoding="utf-8"))
                    findings = data["findings"]
                    self.assertEqual(findings["reviewKind"], review_kind)
                    self.assertEqual(findings["backend"], backend)
                    self.assertEqual(findings["round"], 1)
                    self.assertEqual(findings["headSha"], findings["baseSha"])
                    self.assertTrue(FLOWCTL.validate_review_receipt_findings(data))

    def test_shared_writer_carries_explicit_supersedes_lineage(self) -> None:
        receipt = self.repo / "receipt.json"
        kwargs = dict(
            receipt_path=str(receipt),
            review_type="impl_review",
            review_id="fn-136.3",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            include_effort=True,
            base_branch="HEAD",
        )
        FLOWCTL._write_backend_review_receipt(
            review_text=_fixture("codex"), **kwargs
        )
        first = json.loads(receipt.read_text(encoding="utf-8"))["findings"]
        FLOWCTL._write_backend_review_receipt(
            review_text="Prior finding 1 — fixed.\n<verdict>SHIP</verdict>\n",
            **kwargs,
        )
        second = json.loads(receipt.read_text(encoding="utf-8"))["findings"]
        self.assertEqual(second["round"], 2)
        self.assertEqual(second["supersedesReceiptId"], first["sourceReceiptId"])
        self.assertEqual(
            second["items"][0]["firstSeenReceiptId"],
            first["items"][0]["firstSeenReceiptId"],
        )
        self.assertEqual(second["items"][0]["status"], "fixed")
        generations = FLOWCTL.load_review_receipt_generations(receipt)
        self.assertIsNotNone(generations)
        self.assertEqual(len(generations), 2)
        current = FLOWCTL.select_current_review_findings(
            generations,
            current_head_sha=second["headSha"],
            review_kind="implementation",
            backend="codex",
        )
        self.assertEqual(current["sourceReceiptId"], second["sourceReceiptId"])
        self.assertTrue(
            any(
                item["sourceReceiptId"] == first["sourceReceiptId"]
                for item in (entry["findings"] for entry in generations)
            )
        )

    def test_reused_path_does_not_cross_review_ids(self) -> None:
        receipt = self.repo / "receipt.json"
        common = dict(
            receipt_path=str(receipt),
            review_type="impl_review",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            review_text=_fixture("codex"),
            include_effort=True,
            base_branch="HEAD",
        )
        FLOWCTL._write_backend_review_receipt(review_id="fn-1.1", **common)
        FLOWCTL._write_backend_review_receipt(review_id="fn-2.1", **common)
        findings = json.loads(receipt.read_text(encoding="utf-8"))["findings"]
        self.assertEqual(findings["round"], 1)
        self.assertNotIn("supersedesReceiptId", findings)
        generations = FLOWCTL.load_review_receipt_generations(receipt)
        self.assertEqual(len(generations), 1)
        current = FLOWCTL.select_current_review_findings(
            generations,
            current_head_sha=findings["headSha"],
            review_kind="implementation",
            backend="codex",
        )
        self.assertEqual(current["sourceReceiptId"], findings["sourceReceiptId"])

    def test_writer_uses_pre_dispatch_literal_snapshot(self) -> None:
        receipt = self.repo / "receipt.json"
        FLOWCTL._write_backend_review_receipt(
            str(receipt),
            review_type="impl_review",
            review_id="fn-136.3",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            review_text=_fixture("codex"),
            include_effort=True,
            base_branch="HEAD",
            reviewed_base_sha=BASE_SHA,
            reviewed_head_sha=HEAD_SHA,
        )
        findings = json.loads(receipt.read_text(encoding="utf-8"))["findings"]
        self.assertEqual(findings["baseSha"], BASE_SHA)
        self.assertEqual(findings["headSha"], HEAD_SHA)

    def test_direct_writer_attach_uses_prior_before_atomic_replace(self) -> None:
        for backend in ("rp", "host"):
            with self.subTest(backend=backend):
                receipt = self.repo / f"{backend}.json"
                recovery = self.repo / f"{backend}-recovery.json"
                response = self.repo / f"{backend}-review.md"
                base_input = self.repo / f"{backend}-base.json"
                response.write_text(_fixture(backend), encoding="utf-8")
                base_input.write_text(
                    json.dumps(
                        {
                            "type": "impl_review",
                            "id": "fn-136.3",
                            "mode": backend,
                            "verdict": "NEEDS_WORK",
                        }
                    ),
                    encoding="utf-8",
                )
                args = argparse.Namespace(
                    input=str(base_input),
                    receipt=str(receipt),
                    review_file=str(response),
                    prior=None,
                    head="HEAD",
                    base="HEAD",
                    recovery=str(recovery),
                    json=True,
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    FLOWCTL.cmd_review_findings_attach(args)
                first = json.loads(
                    receipt.read_text(encoding="utf-8")
                )["findings"]

                response.write_text(
                    "Prior finding 1 — fixed.\n<verdict>SHIP</verdict>\n",
                    encoding="utf-8",
                )
                with contextlib.redirect_stdout(io.StringIO()):
                    FLOWCTL.cmd_review_findings_attach(args)
                second = json.loads(
                    receipt.read_text(encoding="utf-8")
                )["findings"]
                self.assertEqual(second["round"], 2)
                self.assertEqual(
                    second["supersedesReceiptId"], first["sourceReceiptId"]
                )
                self.assertEqual(
                    json.loads(
                        recovery.read_text(encoding="utf-8")
                    )["findings"],
                    second,
                )
                generations = FLOWCTL.load_review_receipt_generations(receipt)
                self.assertEqual(
                    [entry["findings"]["round"] for entry in generations],
                    [1, 2],
                )

    def test_completion_direct_routes_serialize_concurrent_advancement(self) -> None:
        for backend in ("rp", "host"):
            with self.subTest(backend=backend):
                receipt = self.repo / f"{backend}-completion.json"
                recovery = self.repo / f"{backend}-completion-recovery.json"

                def attach(
                    index: int,
                    *,
                    route: str = backend,
                    terminal: Path = receipt,
                    recovery_copy: Path = recovery,
                ) -> None:
                    base_input = self.repo / f"{route}-input-{index}.json"
                    invocation_review = (
                        self.repo / f"{route}-review-{index}.md"
                    )
                    invocation_review.write_text(
                        f"""## Gap {index}
- **Severity**: Major
- **Confidence**: 100
- **Classification**: introduced
- **Problem**: attempt-{index} metadata must stay with this review.
<verdict>NEEDS_WORK</verdict>
""",
                        encoding="utf-8",
                    )
                    base_input.write_text(
                        json.dumps(
                            {
                                "type": "completion_review",
                                "id": "fn-136",
                                "mode": route,
                                "verdict": "NEEDS_WORK",
                                "attempt_timestamp": f"attempt-{index}",
                            }
                        ),
                        encoding="utf-8",
                    )
                    FLOWCTL.cmd_review_findings_attach(
                        argparse.Namespace(
                            input=str(base_input),
                            receipt=str(terminal),
                            review_file=str(invocation_review),
                            prior=None,
                            head="HEAD",
                            base="HEAD",
                            recovery=str(recovery_copy),
                            json=True,
                        )
                    )

                with contextlib.redirect_stdout(io.StringIO()):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        list(pool.map(attach, (1, 2)))
                generations = FLOWCTL.load_review_receipt_generations(receipt)
                self.assertEqual(
                    sorted(
                        entry["findings"]["round"] for entry in generations
                    ),
                    [1, 2],
                )
                self.assertEqual(
                    json.loads(
                        recovery.read_text(encoding="utf-8")
                    )["findings"]["round"],
                    2,
                )
                for generation in generations:
                    attempt = generation["attempt_timestamp"]
                    self.assertIn(
                        attempt,
                        generation["findings"]["items"][-1]["body"],
                    )

    def test_qa_ratchet_preserves_identity_and_resolves_absent_findings(self) -> None:
        first = FLOWCTL.parse_review_findings(
            """### qa-login
- **Severity**: P1
- **Confidence**: 100
- **Classification**: introduced
- **Title**: qa-login
- **Problem**: Login is broken.
<verdict>NEEDS_WORK</verdict>
""",
            source_receipt_id="qa-round-1",
            review_kind="qa",
            backend="interactive",
            round_number=1,
            head_sha=HEAD_SHA,
        )
        repeated = FLOWCTL.parse_review_findings(
            "Prior finding 1 — not_fixed.\n<verdict>NEEDS_WORK</verdict>\n",
            source_receipt_id="qa-round-2",
            review_kind="qa",
            backend="interactive",
            round_number=2,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="qa-round-1",
            prior_findings=first,
        )
        resolved = FLOWCTL.parse_review_findings(
            "Prior finding 1 — fixed.\n<verdict>SHIP</verdict>\n",
            source_receipt_id="qa-round-3",
            review_kind="qa",
            backend="interactive",
            round_number=3,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="qa-round-2",
            prior_findings=repeated,
        )
        self.assertEqual(repeated["items"][0]["id"], first["items"][0]["id"])
        self.assertEqual(len(repeated["items"]), 1)
        self.assertEqual(resolved["items"][0]["id"], first["items"][0]["id"])
        self.assertEqual(resolved["items"][0]["status"], "fixed")

        blocked = FLOWCTL.parse_review_findings(
            "Prior finding 1 — not_fixed.\n<verdict>NEEDS_WORK</verdict>\n",
            source_receipt_id="qa-round-blocked",
            review_kind="qa",
            backend="interactive",
            round_number=2,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="qa-round-1",
            prior_findings=first,
        )
        self.assertEqual(blocked["items"][0]["id"], first["items"][0]["id"])
        self.assertEqual(blocked["items"][0]["status"], "not_fixed")

    def test_qa_workflow_renderer_repeats_blocks_and_resolves_identity(self) -> None:
        first = FLOWCTL.parse_review_findings(
            """### qa-login
- **Severity**: P1
- **Confidence**: 100
- **Classification**: introduced
- **Title**: qa-login
- **Problem**: Login is broken.
<verdict>NEEDS_WORK</verdict>
""",
            source_receipt_id="qa-workflow-1",
            review_kind="qa",
            backend="interactive",
            round_number=1,
            head_sha=HEAD_SHA,
        )
        prior_path = self.repo / "qa-prior.json"
        prior_path.write_text(
            json.dumps(
                {
                    "type": "qa_verdict",
                    "id": "fn-136",
                    "mode": "interactive",
                    "findings": first,
                }
            ),
            encoding="utf-8",
        )
        renderer = _qa_review_renderer_script()
        current_finding = {
            "id": "qa-login",
            "severity": "P1",
            "confidence": 100,
            "classification": "introduced",
            "reason": "Login is broken.",
            "file": "login",
        }

        def render(outcome: str, findings: list[dict]) -> str:
            output_path = self.repo / f"qa-{outcome}.md"
            env = {
                **os.environ,
                "QA_TYPE": "qa_verdict",
                "QA_ID": "fn-136",
                "QA_MODE": "interactive",
                "QA_OUTCOME": outcome,
                "QA_VERDICT": (
                    "SHIP" if outcome in {"SHIP", "NA"} else "NEEDS_WORK"
                ),
                "QA_FINDINGS": json.dumps(findings),
            }
            subprocess.run(
                [
                    sys.executable,
                    "-",
                    str(output_path),
                    str(prior_path),
                ],
                input=renderer,
                text=True,
                env=env,
                check=True,
            )
            return output_path.read_text(encoding="utf-8")

        repeated = FLOWCTL.parse_review_findings(
            render("NEEDS_WORK", [current_finding]),
            source_receipt_id="qa-workflow-2",
            review_kind="qa",
            backend="interactive",
            round_number=2,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="qa-workflow-1",
            prior_findings=first,
        )
        blocked = FLOWCTL.parse_review_findings(
            render("BLOCKED", []),
            source_receipt_id="qa-workflow-blocked",
            review_kind="qa",
            backend="interactive",
            round_number=2,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="qa-workflow-1",
            prior_findings=first,
        )
        resolved = FLOWCTL.parse_review_findings(
            render("SHIP", []),
            source_receipt_id="qa-workflow-resolved",
            review_kind="qa",
            backend="interactive",
            round_number=2,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="qa-workflow-1",
            prior_findings=first,
        )
        self.assertEqual(len(repeated["items"]), 1)
        self.assertEqual(repeated["items"][0]["id"], first["items"][0]["id"])
        self.assertEqual(blocked["items"][0]["status"], "not_fixed")
        self.assertEqual(resolved["items"][0]["status"], "fixed")

    def test_direct_attach_rejects_stale_explicit_prior_snapshot(self) -> None:
        receipt = self.repo / "qa.json"
        response = self.repo / "qa-review.md"
        base_input = self.repo / "qa-input.json"
        response.write_text(_fixture("host"), encoding="utf-8")
        base_input.write_text(
            json.dumps(
                {
                    "type": "qa_verdict",
                    "id": "fn-136",
                    "mode": "interactive",
                    "verdict": "NEEDS_WORK",
                }
            ),
            encoding="utf-8",
        )
        initial = argparse.Namespace(
            input=str(base_input),
            receipt=str(receipt),
            review_file=str(response),
            prior=None,
            head="HEAD",
            base=None,
            recovery=None,
            require_prior_current=False,
            json=True,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            FLOWCTL.cmd_review_findings_attach(initial)
        prior_one = self.repo / "prior-one.json"
        prior_two = self.repo / "prior-two.json"
        prior_one.write_bytes(receipt.read_bytes())
        prior_two.write_bytes(receipt.read_bytes())
        response.write_text(
            "Prior finding 1 — not_fixed.\n<verdict>NEEDS_WORK</verdict>\n",
            encoding="utf-8",
        )

        def advance(prior: Path) -> bool:
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    FLOWCTL.cmd_review_findings_attach(
                        argparse.Namespace(
                            **{
                                **vars(initial),
                                "prior": str(prior),
                                "require_prior_current": True,
                            }
                        )
                    )
            except FLOWCTL.ReviewReceiptHistoryError:
                return False
            return True

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(advance, (prior_one, prior_two)))
        self.assertEqual(sorted(results), [False, True])
        generations = FLOWCTL.load_review_receipt_generations(receipt)
        self.assertEqual(
            sorted(entry["findings"]["round"] for entry in generations),
            [1, 2],
        )

    def test_legacy_and_unparseable_receipts_remain_valid(self) -> None:
        legacy = {
            "type": "impl_review",
            "id": "fn-136.3",
            "verdict": "SHIP",
        }
        self.assertTrue(FLOWCTL.validate_review_receipt_findings(legacy))
        invalid = dict(legacy, findings={"schemaVersion": 99})
        self.assertFalse(FLOWCTL.validate_review_receipt_findings(invalid))

    def test_receipt_validation_binds_container_kind_and_backend(self) -> None:
        findings = _container(receipt_id="round-1")
        valid = {
            "type": "impl_review",
            "id": "fn-136.3",
            "mode": "codex",
            "findings": findings,
        }
        self.assertTrue(FLOWCTL.validate_review_receipt_findings(valid))
        self.assertFalse(
            FLOWCTL.validate_review_receipt_findings(
                dict(valid, type="plan_review")
            )
        )
        self.assertFalse(
            FLOWCTL.validate_review_receipt_findings(dict(valid, mode="rp"))
        )

    def test_failure_cleanup_archives_latest_success(self) -> None:
        receipt = self.repo / "receipt.json"
        FLOWCTL._write_backend_review_receipt(
            str(receipt),
            review_type="impl_review",
            review_id="fn-136.3",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            review_text=_fixture("codex"),
            include_effort=True,
            base_branch="HEAD",
        )
        latest = json.loads(receipt.read_text(encoding="utf-8"))["findings"]
        FLOWCTL._clear_stale_review_receipt(str(receipt))
        self.assertFalse(receipt.exists())
        generations = FLOWCTL.load_review_receipt_generations(receipt)
        self.assertEqual(len(generations), 1)
        self.assertEqual(
            generations[0]["findings"]["sourceReceiptId"],
            latest["sourceReceiptId"],
        )

    def test_receipt_lock_lives_outside_reviewed_repository(self) -> None:
        lock_path = FLOWCTL._review_receipt_lock_path(
            self.repo / ".flow" / "receipts" / "impl.json"
        )
        self.assertFalse(lock_path.is_relative_to(self.repo))
        self.assertEqual(lock_path.parent.name, "review-receipt-locks")

    def test_successful_retry_recovers_unique_history_tip(self) -> None:
        receipt = self.repo / "receipt.json"
        kwargs = dict(
            receipt_path=str(receipt),
            review_type="impl_review",
            review_id="fn-136.3",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            include_effort=True,
            base_branch="HEAD",
        )
        FLOWCTL._write_backend_review_receipt(
            review_text=_fixture("codex"), **kwargs
        )
        first = json.loads(receipt.read_text(encoding="utf-8"))["findings"]
        FLOWCTL._clear_stale_review_receipt(str(receipt))

        FLOWCTL._write_backend_review_receipt(
            review_text="Prior finding 1 — fixed.\n<verdict>SHIP</verdict>\n",
            **kwargs,
        )
        second = json.loads(receipt.read_text(encoding="utf-8"))["findings"]
        self.assertEqual(second["round"], 2)
        self.assertEqual(
            second["supersedesReceiptId"], first["sourceReceiptId"]
        )
        self.assertEqual(second["items"][0]["status"], "fixed")

    def test_missing_pointer_rejects_ambiguous_history_tips(self) -> None:
        receipt = self.repo / "receipt.json"
        kwargs = dict(
            receipt_path=str(receipt),
            review_type="impl_review",
            review_id="fn-136.3",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            include_effort=True,
            base_branch="HEAD",
        )
        FLOWCTL._write_backend_review_receipt(
            review_text=_fixture("codex"), **kwargs
        )
        first_receipt = json.loads(receipt.read_text(encoding="utf-8"))
        FLOWCTL._clear_stale_review_receipt(str(receipt))
        other_receipt = dict(first_receipt)
        other_receipt["findings"] = _container(receipt_id="other-root")
        other_id = other_receipt["findings"]["sourceReceiptId"]
        other_path = FLOWCTL._review_receipt_history_dir(receipt) / (
            f"{FLOWCTL.hashlib.sha256(other_id.encode()).hexdigest()}.json"
        )
        FLOWCTL.atomic_write_json(other_path, other_receipt)

        with self.assertRaises(FLOWCTL.ReviewReceiptHistoryError):
            FLOWCTL._write_backend_review_receipt(
                review_text="Prior finding 1 — fixed.\n<verdict>SHIP</verdict>\n",
                **kwargs,
            )
        self.assertFalse(receipt.exists())

    def test_missing_pointer_rejects_corrupt_or_cross_scope_history(self) -> None:
        receipt = self.repo / "receipt.json"
        kwargs = dict(
            receipt_path=str(receipt),
            review_type="impl_review",
            review_id="fn-136.3",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            review_text=_fixture("codex"),
            include_effort=True,
            base_branch="HEAD",
        )
        FLOWCTL._write_backend_review_receipt(**kwargs)
        FLOWCTL._clear_stale_review_receipt(str(receipt))
        history_path = next(
            FLOWCTL._review_receipt_history_dir(receipt).glob("*.json")
        )
        valid_bytes = history_path.read_bytes()
        history_path.write_text("{malformed", encoding="utf-8")
        with self.assertRaises(FLOWCTL.ReviewReceiptHistoryError):
            FLOWCTL._write_backend_review_receipt(**kwargs)
        self.assertFalse(receipt.exists())

        history_path.write_bytes(valid_bytes)
        with self.assertRaises(FLOWCTL.ReviewReceiptHistoryError):
            FLOWCTL._write_backend_review_receipt(
                **dict(kwargs, review_id="fn-999.1")
            )
        self.assertFalse(receipt.exists())

    def test_corrupt_history_never_allows_latest_loss(self) -> None:
        receipt = self.repo / "receipt.json"
        kwargs = dict(
            receipt_path=str(receipt),
            review_type="impl_review",
            review_id="fn-136.3",
            backend="codex",
            verdict="NEEDS_WORK",
            session_id="session",
            effective_model="model",
            effective_effort="high",
            resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
            review_text=_fixture("codex"),
            include_effort=True,
            base_branch="HEAD",
        )
        FLOWCTL._write_backend_review_receipt(**kwargs)
        before = receipt.read_bytes()
        findings = json.loads(before)["findings"]
        history_dir = FLOWCTL._review_receipt_history_dir(receipt)
        history_dir.mkdir(parents=True)
        history_path = history_dir / (
            f"{FLOWCTL.hashlib.sha256(findings['sourceReceiptId'].encode()).hexdigest()}.json"
        )
        history_path.write_text("{malformed", encoding="utf-8")

        FLOWCTL._clear_stale_review_receipt(str(receipt))
        self.assertEqual(receipt.read_bytes(), before)
        with self.assertRaises(FLOWCTL.ReviewReceiptHistoryError):
            FLOWCTL._write_backend_review_receipt(**kwargs)
        self.assertEqual(receipt.read_bytes(), before)
        history_path.write_text(json.dumps({"conflict": True}), encoding="utf-8")
        with self.assertRaises(FLOWCTL.ReviewReceiptHistoryError):
            FLOWCTL._write_backend_review_receipt(**kwargs)
        self.assertEqual(receipt.read_bytes(), before)

    def test_concurrent_writers_materialize_every_generation(self) -> None:
        receipt = self.repo / "receipt.json"

        def write(index: int) -> None:
            FLOWCTL._write_backend_review_receipt(
                str(receipt),
                review_type="impl_review",
                review_id="fn-136.3",
                backend="codex",
                verdict="NEEDS_WORK",
                session_id=f"session-{index}",
                effective_model="model",
                effective_effort="high",
                resolved_spec=FLOWCTL.BackendSpec("codex", "model", "high"),
                review_text=_fixture("codex"),
                include_effort=True,
                base_branch="HEAD",
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(write, (1, 2)))
        generations = FLOWCTL.load_review_receipt_generations(receipt)
        self.assertEqual(len(generations), 2)
        self.assertEqual(
            sorted(entry["findings"]["round"] for entry in generations),
            [1, 2],
        )

    def test_direct_workflow_contracts_require_parser_complete_fields(self) -> None:
        skill_root = REPO / "plugins" / "flow-next" / "skills"
        plan_rp = (
            skill_root / "flow-next-plan-review" / "workflow-rp.md"
        ).read_text(encoding="utf-8")
        completion_rp = (
            skill_root / "flow-next-spec-completion-review" / "workflow-rp.md"
        ).read_text(encoding="utf-8")
        completion_host = (
            skill_root / "flow-next-spec-completion-review" / "workflow-host.md"
        ).read_text(encoding="utf-8")
        impl_host = (
            skill_root / "flow-next-impl-review" / "workflow-host.md"
        ).read_text(encoding="utf-8")
        qa = (skill_root / "flow-next-qa" / "workflow.md").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(plan_rp.count("Confidence"), 2)
        self.assertGreaterEqual(plan_rp.count("Classification"), 2)
        self.assertGreaterEqual(completion_rp.count("Severity"), 2)
        for field in ("Severity", "Confidence", "Classification"):
            self.assertIn(field, completion_host)
        self.assertIn('DIFF_BASE="${BASE_COMMIT:-main}"', completion_host)
        self.assertIn('DIFF_BASE="${BASE_COMMIT:-main}"', impl_host)
        impl_rp = (
            skill_root / "flow-next-impl-review" / "workflow-rp.md"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(
            impl_rp.count('REVIEW_HEAD_SHA="$(git rev-parse HEAD)"'), 2
        )
        self.assertGreaterEqual(
            completion_rp.count('REVIEW_HEAD_SHA="$(git rev-parse HEAD)"'), 2
        )
        self.assertIn('QA_FINDINGS="${QA_FINDINGS:-[]}"', qa)
        self.assertIn('RECEIPT_HISTORY_DIR="${RECEIPT_PATH}.history"', qa)


class ReviewFindingsCurrentnessTest(unittest.TestCase):
    def test_only_unambiguous_current_chain_tip_projects(self) -> None:
        first = _container(receipt_id="round-1")
        second = _container(receipt_id="round-2", round_number=2, prior=first)
        receipts = [{"findings": first}, {"findings": second}]
        snapshot = json.loads(json.dumps(receipts))
        current = FLOWCTL.select_current_review_findings(
            receipts,
            current_head_sha=HEAD_SHA,
            review_kind="implementation",
            backend="codex",
        )
        self.assertEqual(current["sourceReceiptId"], "round-2")
        self.assertEqual(receipts, snapshot, "projection must preserve stale evidence")

    def test_stale_tip_broken_chain_duplicates_and_ambiguity_fail_closed(self) -> None:
        first = _container(receipt_id="round-1")
        stale_tip = _container(
            receipt_id="round-2",
            round_number=2,
            head_sha="c" * 40,
            prior=first,
        )
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": stale_tip}],
                current_head_sha=HEAD_SHA,
            )
        )

        broken = json.loads(json.dumps(stale_tip))
        broken["headSha"] = HEAD_SHA
        broken["supersedesReceiptId"] = "missing"
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": broken}],
                current_head_sha=HEAD_SHA,
            )
        )
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": first}],
                current_head_sha=HEAD_SHA,
            )
        )
        other_root = _container(receipt_id="other-root")
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": other_root}],
                current_head_sha=HEAD_SHA,
            )
        )

    def test_semantically_incomplete_stale_sibling_does_not_invalidate_current(
        self,
    ) -> None:
        first = _container(receipt_id="round-1")
        current = _container(receipt_id="current-tip", round_number=2, prior=first)
        stale = _container(
            receipt_id="stale-tip",
            round_number=2,
            head_sha="c" * 40,
            prior=first,
        )
        stale["items"] = stale["items"][1:]
        selected = FLOWCTL.select_current_review_findings(
            [
                {"findings": first},
                {"findings": stale},
                {"findings": current},
            ],
            current_head_sha=HEAD_SHA,
        )
        self.assertEqual(selected["sourceReceiptId"], "current-tip")

    def test_anchor_and_cross_receipt_references_fail_closed(self) -> None:
        first = _container(receipt_id="round-1")
        bad_anchor = json.loads(json.dumps(first))
        bad_anchor["items"][0]["anchor"]["headSha"] = "d" * 40
        self.assertFalse(FLOWCTL._review_findings_container_valid(bad_anchor))

        second = _container(receipt_id="round-2", round_number=2, prior=first)
        bad_first_seen = json.loads(json.dumps(second))
        bad_first_seen["items"][0]["firstSeenReceiptId"] = "missing"
        bad_first_seen["items"][0]["id"] = FLOWCTL._review_finding_lineage_id(
            "missing", bad_first_seen["items"][0]["ordinal"]
        )
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": bad_first_seen}],
                current_head_sha=HEAD_SHA,
            )
        )

    def test_omitted_open_finding_remains_current_until_explicit_resolution(self) -> None:
        first = _container(receipt_id="round-1")
        second = FLOWCTL.parse_review_findings(
            "No findings.\n<verdict>SHIP</verdict>\n",
            source_receipt_id="round-2",
            review_kind="implementation",
            backend="codex",
            round_number=2,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="round-1",
            prior_findings=first,
            anchor_side="head",
        )
        self.assertIsNotNone(second)
        self.assertEqual(len(second["items"]), len(first["items"]))
        self.assertTrue(all(item["status"] == "open" for item in second["items"]))
        current = FLOWCTL.select_current_review_findings(
            [{"findings": first}, {"findings": second}],
            current_head_sha=HEAD_SHA,
        )
        self.assertEqual(current["sourceReceiptId"], "round-2")
        self.assertTrue(all(item["status"] == "open" for item in current["items"]))

    def test_repeated_prior_edge_tracks_same_durable_item_across_generations(
        self,
    ) -> None:
        first = _container(receipt_id="round-1")
        prior_id = first["items"][0]["id"]
        finding = f"""### Replacement finding
- **Severity**: Major
- **Confidence**: 100
- **Classification**: introduced
- **Prior finding ID**: {prior_id}
- **Problem**: The replacement carries explicit lineage.
<verdict>NEEDS_WORK</verdict>
"""
        second = FLOWCTL.parse_review_findings(
            finding,
            source_receipt_id="round-2",
            review_kind="implementation",
            backend="codex",
            round_number=2,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="round-1",
            prior_findings=first,
            anchor_side="head",
        )
        third = FLOWCTL.parse_review_findings(
            "Prior finding 1 — not_fixed.\n<verdict>NEEDS_WORK</verdict>\n",
            source_receipt_id="round-3",
            review_kind="implementation",
            backend="codex",
            round_number=3,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="round-2",
            prior_findings=second,
            anchor_side="head",
        )
        replacement_id = next(
            item["id"] for item in second["items"] if item.get("priorFindingId")
        )
        self.assertTrue(
            any(
                item["id"] == replacement_id
                and item["priorFindingId"] == prior_id
                for item in third["items"]
            )
        )
        current = FLOWCTL.select_current_review_findings(
            [{"findings": first}, {"findings": second}, {"findings": third}],
            current_head_sha=HEAD_SHA,
        )
        self.assertEqual(current["sourceReceiptId"], "round-3")

    def test_conflicting_prior_edge_ownership_fails_closed(self) -> None:
        first = _container(receipt_id="round-1")
        prior_id = first["items"][0]["id"]
        finding = f"""### Replacement finding
- **Severity**: Major
- **Confidence**: 100
- **Classification**: introduced
- **Prior finding ID**: {prior_id}
- **Problem**: The replacement carries explicit lineage.
<verdict>NEEDS_WORK</verdict>
"""
        second = FLOWCTL.parse_review_findings(
            finding,
            source_receipt_id="round-2",
            review_kind="implementation",
            backend="codex",
            round_number=2,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="round-1",
            prior_findings=first,
            anchor_side="head",
        )
        third = FLOWCTL.parse_review_findings(
            finding.replace("Replacement finding", "Conflicting replacement"),
            source_receipt_id="round-3",
            review_kind="implementation",
            backend="codex",
            round_number=3,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="round-2",
            prior_findings=second,
            anchor_side="head",
        )
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": second}, {"findings": third}],
                current_head_sha=HEAD_SHA,
            )
        )

    def test_unparseable_rereview_does_not_advance_prior_snapshot(self) -> None:
        first = _container(receipt_id="round-1")
        second = FLOWCTL.parse_review_findings(
            "Looks good after another pass.\n<verdict>SHIP</verdict>\n",
            source_receipt_id="round-2",
            review_kind="implementation",
            backend="codex",
            round_number=2,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="round-1",
            prior_findings=first,
            anchor_side="head",
        )
        self.assertIsNone(second)

    def test_valid_ratchet_still_advances_prior_snapshot(self) -> None:
        first = _container(receipt_id="round-1")
        second = FLOWCTL.parse_review_findings(
            "Prior finding 1 — fixed.\n<verdict>SHIP</verdict>\n",
            source_receipt_id="round-2",
            review_kind="implementation",
            backend="codex",
            round_number=2,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            supersedes_receipt_id="round-1",
            prior_findings=first,
            anchor_side="head",
        )
        self.assertEqual(second["items"][0]["status"], "fixed")
        self.assertEqual(second["items"][0]["lastSeenReceiptId"], "round-2")

    def test_incomplete_snapshot_and_forged_first_seen_fail_closed(self) -> None:
        first = _container(receipt_id="round-1")
        second = _container(receipt_id="round-2", round_number=2, prior=first)
        omitted = json.loads(json.dumps(second))
        omitted["items"] = [
            item for item in omitted["items"] if item["id"] != first["items"][0]["id"]
        ]
        self.assertTrue(FLOWCTL._review_findings_container_valid(omitted))
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": omitted}],
                current_head_sha=HEAD_SHA,
            )
        )

        forged = json.loads(json.dumps(second))
        forged_item = next(
            item for item in forged["items"] if item["firstSeenReceiptId"] == "round-2"
        )
        forged_item["firstSeenReceiptId"] = "round-1"
        forged_item["id"] = FLOWCTL._review_finding_lineage_id(
            "round-1", forged_item["ordinal"]
        )
        self.assertTrue(FLOWCTL._review_findings_container_valid(forged))
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": forged}],
                current_head_sha=HEAD_SHA,
            )
        )

        skipped_round = json.loads(json.dumps(second))
        skipped_round["round"] = 3
        self.assertIsNone(
            FLOWCTL.select_current_review_findings(
                [{"findings": first}, {"findings": skipped_round}],
                current_head_sha=HEAD_SHA,
            )
        )


class ReviewFindingsLocalBudgetTest(unittest.TestCase):
    def test_maximum_item_fixture_parse_and_validate_p95_under_budget(self) -> None:
        text = "\n".join(
            f"""### Finding {index}
- **Severity**: Minor
- **Confidence**: 75
- **Classification**: introduced
- **Problem**: Finding {index} demonstrates bounded successful parsing."""
            for index in range(1, FLOWCTL._FINDINGS_MAX_ITEMS + 1)
        ) + "\n<verdict>NEEDS_WORK</verdict>\n"
        backend = "codex"

        def run_once() -> None:
            findings = FLOWCTL.parse_review_findings(
                text,
                source_receipt_id="benchmark-receipt",
                review_kind="implementation",
                backend=backend,
                round_number=1,
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
                anchor_side="head",
            )
            self.assertIsNotNone(findings)
            self.assertTrue(FLOWCTL._review_findings_container_valid(findings))

        for _ in range(5):
            run_once()
        timings_ms = []
        for _ in range(30):
            started = time.perf_counter()
            run_once()
            timings_ms.append((time.perf_counter() - started) * 1000)
        p95_ms = sorted(timings_ms)[28]
        self.assertLess(
            p95_ms,
            FINDINGS_P95_BUDGET_MS,
            f"maximum-item fixture p95={p95_ms:.3f}ms",
        )


if __name__ == "__main__":
    unittest.main()
