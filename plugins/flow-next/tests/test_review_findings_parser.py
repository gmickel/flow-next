"""Deterministic parser and lineage contracts for review findings v1."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "plugins" / "flow-next" / "scripts"))
FLOWCTL_PATH = REPO / "plugins" / "flow-next" / "scripts" / "flowctl.py"
CORPUS = REPO / "optimization" / "reached-path" / "fixtures" / "review-findings" / "v1"
SPEC = importlib.util.spec_from_file_location("flowctl_findings_test", FLOWCTL_PATH)
assert SPEC and SPEC.loader
FLOWCTL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FLOWCTL)

BACKENDS = {"codex", "copilot", "cursor", "host", "rp", "export"}
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40


def parse(
    text: str,
    backend: str,
    *,
    receipt: str = "receipt-round-1",
    round_number: int = 1,
    prior: dict | None = None,
    supersedes: str | None = None,
    anchor_side: str | None = "head",
    **overrides,
):
    kwargs = {
        "source_receipt_id": receipt,
        "review_kind": "implementation",
        "backend": backend,
        "round_number": round_number,
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "supersedes_receipt_id": supersedes,
        "prior_findings": prior,
        "anchor_side": anchor_side,
    }
    kwargs.update(overrides)
    return FLOWCTL.parse_review_findings(text, **kwargs)


class ReviewFindingsParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads((CORPUS / "INDEX.json").read_text(encoding="utf-8"))

    def fixture(self, backend: str, case: str) -> str:
        return (CORPUS / backend / f"{case}.md").read_text(encoding="utf-8")

    def test_fixture_matrix_matches_normalized_oracle(self) -> None:
        for backend in BACKENDS:
            for case in ("no-findings-ship", "no-anchor", "catalog-sample"):
                with self.subTest(backend=backend, case=case):
                    result = parse(self.fixture(backend, case), backend)
                    expected = self.index["expectations"][backend][case]
                    self.assertIsNotNone(result)
                    self.assertEqual(result["schemaVersion"], 1)
                    self.assertEqual(result["sourceReceiptId"], "receipt-round-1")
                    self.assertEqual(result["reviewKind"], "implementation")
                    self.assertEqual(result["backend"], backend)
                    self.assertEqual(result["round"], 1)
                    self.assertEqual(result["baseSha"], BASE_SHA)
                    self.assertEqual(result["headSha"], HEAD_SHA)
                    self.assertEqual(
                        set(result),
                        {
                            "schemaVersion",
                            "sourceReceiptId",
                            "reviewKind",
                            "backend",
                            "round",
                            "baseSha",
                            "headSha",
                            "items",
                        },
                    )
                    self.assertEqual(len(result["items"]), len(expected["items"]))
                    for actual, wanted in zip(
                        result["items"], expected["items"], strict=True
                    ):
                        expected_keys = {
                            "id",
                            "ordinal",
                            "severity",
                            "confidence",
                            "classification",
                            "status",
                            "title",
                            "body",
                            "rIds",
                            "firstSeenReceiptId",
                            "lastSeenReceiptId",
                        }
                        fixture_text = self.fixture(backend, case)
                        if (
                            "Suggestion" in fixture_text
                            or "Suggested fix" in fixture_text
                        ):
                            expected_keys.add("suggestion")
                        for field in (
                            "severity",
                            "confidence",
                            "classification",
                            "status",
                        ):
                            self.assertEqual(actual[field], wanted[field])
                        if wanted["anchor"] is None:
                            self.assertNotIn("anchor", actual)
                        else:
                            expected_keys.add("anchor")
                            self.assertEqual(
                                actual["anchor"]["path"], wanted["anchor"]["path"]
                            )
                            self.assertEqual(
                                actual["anchor"]["startLine"],
                                wanted["anchor"]["startLine"],
                            )
                            self.assertEqual(actual["anchor"]["side"], "head")
                            self.assertEqual(actual["anchor"]["baseSha"], BASE_SHA)
                            self.assertEqual(actual["anchor"]["headSha"], HEAD_SHA)
                            self.assertEqual(
                                set(actual["anchor"]),
                                {
                                    "path",
                                    "side",
                                    "startLine",
                                    "baseSha",
                                    "headSha",
                                },
                            )
                        self.assertEqual(set(actual), expected_keys)

    def test_explicit_dash_file_line_means_no_anchor(self) -> None:
        result = parse(
            """
Severity: P1
Confidence: 100
Classification: introduced
File:Line: -
R-IDs: [R3]
Problem: The repository-wide invariant is not enforced.
Suggestion: Add the missing invariant.
<verdict>NEEDS_WORK</verdict>
""",
            "codex",
        )
        self.assertIsNotNone(result)
        item = result["items"][0]
        self.assertNotIn("anchor", item)
        self.assertEqual(item["rIds"], ["R3"])

    def test_requirements_coverage_does_not_leak_rids_into_last_finding(self) -> None:
        explicit = """
Severity: Major
Confidence: 100
Classification: introduced
R-IDs: [R1]
Problem: The R1 behavior regressed.

## Requirements coverage

| R-ID | Status | Evidence |
|---|---|---|
| R1 | met | Reviewed above. |
| R2 | met | Covered elsewhere. |

<verdict>NEEDS_WORK</verdict>
"""
        self.assertEqual(parse(explicit, "codex")["items"][0]["rIds"], ["R1"])

        fallback = explicit.replace("R-IDs: [R1]\n", "")
        self.assertEqual(parse(fallback, "codex")["items"][0]["rIds"], ["R1"])

    def test_ratchet_carries_ids_and_first_seen_receipt(self) -> None:
        for backend in BACKENDS:
            prior_text = self.fixture(backend, "catalog-sample")
            prior = parse(prior_text, backend)
            expected_statuses = self.index["expectations"][backend]["ratchet-only"][
                "ordered_prior_statuses"
            ]
            # The corpus contains two-status ratchets for some backends. Build a
            # second prior item without changing the lineage rules under test.
            if len(expected_statuses) == 2 and len(prior["items"]) == 1:
                second = dict(prior["items"][0])
                second["ordinal"] = 2
                second["id"] = FLOWCTL._review_finding_lineage_id(
                    prior["sourceReceiptId"], 2
                )
                prior["items"].append(second)
            with self.subTest(backend=backend):
                current = parse(
                    self.fixture(backend, "ratchet-only"),
                    backend,
                    receipt="receipt-round-2",
                    round_number=2,
                    prior=prior,
                    supersedes=prior["sourceReceiptId"],
                )
                self.assertIsNotNone(current)
                self.assertEqual(current["supersedesReceiptId"], "receipt-round-1")
                self.assertEqual(
                    [item["status"] for item in current["items"]],
                    expected_statuses,
                )
                for old, new in zip(
                    prior["items"], current["items"], strict=True
                ):
                    self.assertEqual(new["id"], old["id"])
                    self.assertEqual(
                        new["firstSeenReceiptId"], old["firstSeenReceiptId"]
                    )
                    self.assertEqual(new["lastSeenReceiptId"], "receipt-round-2")

    def test_new_round_finding_gets_new_identity(self) -> None:
        text = self.fixture("codex", "catalog-sample")
        prior = parse(text, "codex")
        current = parse(
            text,
            "codex",
            receipt="receipt-round-2",
            round_number=2,
            prior=prior,
            supersedes=prior["sourceReceiptId"],
        )
        new_items = [
            item
            for item in current["items"]
            if item["firstSeenReceiptId"] == "receipt-round-2"
        ]
        self.assertEqual(len(new_items), 1)
        self.assertNotEqual(new_items[0]["id"], prior["items"][0]["id"])

    def test_round_lineage_requires_root_one_and_contiguous_successors(self) -> None:
        text = self.fixture("codex", "catalog-sample")
        prior = parse(text, "codex")
        self.assertIsNone(parse(text, "codex", round_number=2))
        self.assertIsNone(parse(text, "codex", prior=prior))
        self.assertIsNone(
            parse(
                text,
                "codex",
                receipt="receipt-round-1-successor",
                round_number=1,
                prior=prior,
                supersedes=prior["sourceReceiptId"],
            )
        )
        self.assertIsNone(
            parse(
                text,
                "codex",
                receipt="receipt-round-3",
                round_number=3,
                prior=prior,
                supersedes=prior["sourceReceiptId"],
            )
        )

    def test_explicit_lineage_edge_is_preserved_for_new_identity(self) -> None:
        prior = parse(self.fixture("codex", "catalog-sample"), "codex")
        prior_id = prior["items"][0]["id"]
        text = f"""
Severity: Major
Confidence: 100
Classification: introduced
Prior Finding ID: {prior_id}
Problem: The replacement finding has materially different scope.
"""
        current = parse(
            text,
            "codex",
            receipt="receipt-round-2",
            round_number=2,
            prior=prior,
            supersedes=prior["sourceReceiptId"],
        )
        item = next(
            candidate
            for candidate in current["items"]
            if candidate.get("priorFindingId") == prior_id
        )
        self.assertEqual(item["priorFindingId"], prior_id)
        self.assertNotEqual(item["id"], item["priorFindingId"])

    def test_explicit_lineage_edge_rejects_orphan_and_duplicate_parents(self) -> None:
        prior = parse(self.fixture("codex", "catalog-sample"), "codex")
        orphan = """
Severity: Major
Confidence: 100
Classification: introduced
Prior Finding ID: finding-orphan
Problem: The replacement references no prior item.
"""
        self.assertIsNone(
            parse(
                orphan,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=prior,
                supersedes=prior["sourceReceiptId"],
            )
        )
        prior_id = prior["items"][0]["id"]
        duplicate = f"""
Severity: Major
Confidence: 100
Classification: introduced
Prior Finding ID: {prior_id}
Problem: First replacement.

Severity: Major
Confidence: 100
Classification: introduced
Prior Finding ID: {prior_id}
Problem: Conflicting replacement.
"""
        self.assertIsNone(
            parse(
                duplicate,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=prior,
                supersedes=prior["sourceReceiptId"],
            )
        )

    def test_ratchet_requires_matching_explicit_receipt_lineage(self) -> None:
        prior = parse(self.fixture("codex", "catalog-sample"), "codex")
        ratchet = self.fixture("codex", "ratchet-only")
        second = dict(prior["items"][0])
        second["ordinal"] = 2
        second["id"] = FLOWCTL._review_finding_lineage_id(
            prior["sourceReceiptId"], 2
        )
        prior["items"].append(second)
        self.assertIsNone(
            parse(
                ratchet,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=prior,
            )
        )
        self.assertIsNone(
            parse(
                ratchet,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=prior,
                supersedes="different-receipt",
            )
        )

    def test_ratchet_statuses_require_line_records_and_lexical_boundaries(self) -> None:
        prior = parse(self.fixture("codex", "catalog-sample"), "codex")
        quoted = """
Severity: Minor
Confidence: 75
Classification: introduced
Problem: The prompt says "Prior finding 1 — fixed".
"""
        current = parse(
            quoted,
            "codex",
            receipt="receipt-round-2",
            round_number=2,
            prior=prior,
            supersedes="receipt-round-1",
        )
        self.assertEqual(len(current["items"]), 2)
        carried = next(
            item for item in current["items"] if item["id"] == prior["items"][0]["id"]
        )
        added = next(item for item in current["items"] if item["id"] != carried["id"])
        self.assertEqual(carried["status"], "open")
        self.assertEqual(added["firstSeenReceiptId"], "receipt-round-2")

        for suffix in ("fixed-ish", "fixedly", "withdrawnish"):
            with self.subTest(suffix=suffix):
                self.assertIsNone(
                    parse(
                        f"Prior finding 1 — {suffix}.",
                        "codex",
                        receipt="receipt-round-2",
                        round_number=2,
                        prior=prior,
                        supersedes="receipt-round-1",
                    )
                )

    def test_explicit_empty_rejects_unknown_prior_status(self) -> None:
        prior = parse(self.fixture("codex", "catalog-sample"), "codex")
        unknown = """
No findings.
Prior finding 1 — pending.
<verdict>SHIP</verdict>
"""
        self.assertIsNone(
            parse(
                unknown,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=prior,
                supersedes="receipt-round-1",
            )
        )

        valid_cases = (
            ("Prior finding 1 — fixed.", "fixed"),
            ("- Prior finding #1: not_fixed.", "not_fixed"),
        )
        for record, expected_status in valid_cases:
            with self.subTest(record=record):
                result = parse(
                    f"No findings.\n{record}\n<verdict>SHIP</verdict>",
                    "codex",
                    receipt="receipt-round-2",
                    round_number=2,
                    prior=prior,
                    supersedes="receipt-round-1",
                )
                self.assertEqual(result["items"][0]["status"], expected_status)

        quoted = """
No findings.
The prose mentions "Prior finding 1 — pending", but is not a status record.
<verdict>SHIP</verdict>
"""
        self.assertEqual(parse(quoted, "codex")["items"], [])

    def test_canonical_order_is_severity_confidence_then_ordinal(self) -> None:
        text = """
Severity: Minor
Confidence: 75
Classification: introduced
Problem: second by severity

Severity: Critical
Confidence: 75
Classification: introduced
Problem: first by severity

Severity: Minor
Confidence: 100
Classification: introduced
Problem: second severity but higher confidence

<verdict>NEEDS_WORK</verdict>
"""
        result = parse(text, "codex", anchor_side=None)
        self.assertEqual(
            [item["body"] for item in result["items"]],
            [
                "first by severity",
                "second severity but higher confidence",
                "second by severity",
            ],
        )
        self.assertEqual([item["ordinal"] for item in result["items"]], [2, 3, 1])

    def test_anchor_requires_explicit_side_and_both_shas(self) -> None:
        text = self.fixture("rp", "catalog-sample")
        self.assertNotIn("anchor", parse(text, "rp", anchor_side=None)["items"][0])
        self.assertNotIn(
            "anchor",
            parse(text, "rp", base_sha=None, anchor_side="head")["items"][0],
        )
        anchored = parse(text, "rp", anchor_side="base")["items"][0]["anchor"]
        self.assertEqual(anchored["side"], "base")

    def test_first_seen_id_pins_exact_sha256_byte_contract(self) -> None:
        result = parse(self.fixture("rp", "catalog-sample"), "rp")
        item = result["items"][0]
        digest = FLOWCTL.hashlib.sha256(
            b"flow-next-finding-v1\0receipt-round-1\0" + str(item["ordinal"]).encode()
        ).hexdigest()
        self.assertEqual(item["id"], f"finding-{digest[:32]}")
        self.assertEqual(item["firstSeenReceiptId"], "receipt-round-1")

    def test_unbound_anchor_omits_supplemental_metadata_before_validation(self) -> None:
        text = self.fixture("rp", "catalog-sample").replace(
            "Problem:",
            "Original Path: ../unsafe.py\nBlob OID: not-a-git-object\nProblem:",
            1,
        )
        result = parse(text, "rp", anchor_side=None)
        self.assertIsNotNone(result)
        self.assertNotIn("anchor", result["items"][0])

    def test_unbound_inverted_range_is_omitted_before_bound_range_validation(
        self,
    ) -> None:
        text = """
Severity: Major
Confidence: 100
Classification: introduced
File:Line: src/review.py:12-10
Problem: The range is inverted.
"""
        unbound = parse(text, "rp", anchor_side=None)
        self.assertIsNotNone(unbound)
        self.assertNotIn("anchor", unbound["items"][0])
        self.assertIsNone(parse(text, "rp", anchor_side="head"))

    def test_explicit_anchor_side_is_honored_and_conflicts_reject(self) -> None:
        text = """
Severity: Major
Confidence: 100
Classification: introduced
File:Line: src/review.py:12
Side: base
Problem: The base-side deletion is unsafe.
"""
        anchored = parse(text, "rp", anchor_side=None)["items"][0]["anchor"]
        self.assertEqual(anchored["side"], "base")
        self.assertIsNone(parse(text, "rp", anchor_side="head"))
        self.assertIsNone(parse(text.replace("Side: base", "Side: nearby"), "rp"))

    def test_rename_metadata_is_preserved_only_when_evidenced(self) -> None:
        text = """
Severity: Major
Confidence: 100
Classification: introduced
File:Line: src/new.py:10-12
Original Path: src/old.py
Blob OID: abcdef0123456789
Problem: Rename context must survive.
"""
        anchor = parse(text, "rp")["items"][0]["anchor"]
        self.assertEqual(anchor["originalPath"], "src/old.py")
        self.assertEqual(anchor["endLine"], 12)
        self.assertEqual(anchor["blobOid"], "abcdef0123456789")

    def test_unknown_enums_unsupported_version_and_unparseable_degrade(self) -> None:
        unknowns = (
            "Severity: Blocker\nConfidence: 100\nClassification: introduced\nProblem: x",
            "Severity: Major\nConfidence: 90\nClassification: introduced\nProblem: x",
            "Severity: Major\nConfidence: 100\nClassification: inherited\nProblem: x",
        )
        for text in unknowns:
            self.assertIsNone(parse(text, "codex"))
        for classification in (
            "true",
            "false",
            "introduced=true",
            "introduced=false",
        ):
            text = (
                "Severity: Major\nConfidence: 100\n"
                f"Classification: {classification}\nProblem: x"
            )
            self.assertIsNone(parse(text, "codex"))
        self.assertIsNone(parse("No findings.\n<verdict>SHIP</verdict>", "codex", schema_version=2))
        self.assertIsNone(
            parse(
                "No findings.\n<verdict>SHIP</verdict>",
                "codex",
                schema_version=True,
            )
        )
        self.assertIsNone(
            parse(
                "No findings.\n<verdict>SHIP</verdict>",
                "codex",
                schema_version=1.0,
            )
        )
        for backend in BACKENDS:
            self.assertIsNone(parse(self.fixture(backend, "unparseable"), backend))

    def test_mixed_host_table_and_labeled_findings_fail_closed(self) -> None:
        table = self.fixture("host", "catalog-sample")
        valid_block = """
Severity: Major
Confidence: 100
Classification: introduced
Problem: A second representation must not be silently dropped.
"""
        unknown_block = valid_block.replace("Major", "Blocker")
        self.assertIsNone(parse(f"{table}\n{valid_block}", "host"))
        self.assertIsNone(parse(f"{table}\n{unknown_block}", "host"))

    def test_inline_and_labeled_enums_must_be_semantically_equal(self) -> None:
        inline = "P2 · confidence 75 · introduced"
        equivalent = f"""
{inline}
Severity: Minor
Confidence: 75
Classification: introduced
Problem: Equivalent aliases describe one finding.
"""
        item = parse(equivalent, "host")["items"][0]
        self.assertEqual(
            (item["severity"], item["confidence"], item["classification"]),
            ("P2", 75, "introduced"),
        )
        conflicts = (
            equivalent.replace("Severity: Minor", "Severity: Major"),
            equivalent.replace("Severity: Minor", "Severity: Blocker"),
            equivalent.replace("Confidence: 75", "Confidence: 100"),
            equivalent.replace(
                "Classification: introduced",
                "Classification: pre_existing",
            ),
        )
        for text in conflicts:
            with self.subTest(text=text):
                self.assertIsNone(parse(text, "host"))

    def test_classic_compact_pre_existing_findings_are_preserved(self) -> None:
        text = """
Severity: Major
Confidence: 100
Classification: introduced
File:Line: src/new.py:10
Problem: The introduced finding remains blocking.

## Pre-existing issues (not blocking this verdict)

- [Minor, confidence 75, introduced=false] src/legacy.py:42 — Legacy issue remains visible. R7
Classification counts: 1 introduced, 1 pre_existing.
<verdict>NEEDS_WORK</verdict>
"""
        result = parse(text, "rp")
        self.assertIsNotNone(result)
        self.assertEqual(len(result["items"]), 2)
        compact = result["items"][1]
        self.assertEqual(compact["severity"], "P2")
        self.assertEqual(compact["confidence"], 75)
        self.assertEqual(compact["classification"], "pre_existing")
        self.assertEqual(compact["status"], "open")
        self.assertEqual(compact["body"], "Legacy issue remains visible. R7")
        self.assertEqual(compact["rIds"], ["R7"])
        self.assertEqual(compact["anchor"]["path"], "src/legacy.py")
        self.assertEqual(compact["anchor"]["startLine"], 42)

    def test_malformed_classic_compact_finding_fails_closed(self) -> None:
        cases = (
            "[P4, confidence 75, introduced=false] src/legacy.py:42 — bad severity",
            "[P2, confidence 90, introduced=false] src/legacy.py:42 — bad confidence",
            "[P2, confidence 75, introduced=maybe] src/legacy.py:42 — bad classification",
            "[P2, confidence 75, introduced=false] src/legacy.py:0 — bad line",
        )
        for compact in cases:
            text = f"No findings.\n{compact}\n<verdict>SHIP</verdict>"
            with self.subTest(compact=compact):
                self.assertIsNone(parse(text, "rp"))

    def test_explicit_empty_with_unknown_inline_enum_fails_closed(self) -> None:
        cases = (
            "P4 · confidence 100 · introduced",
            "P1 · confidence 90 · introduced",
            "P1 · confidence 100 · inherited",
        )
        for inline in cases:
            text = f"No findings.\n{inline}\n<verdict>SHIP</verdict>"
            with self.subTest(inline=inline):
                self.assertIsNone(parse(text, "host"))

    def test_distinct_inline_then_labeled_finding_remain_separate(self) -> None:
        text = """
1. P1 · confidence 100 · introduced
Problem: First inline finding.

2. Finding: Second labeled finding.
Severity: Major
Confidence: 100
Classification: introduced
Problem: Second labeled finding.
"""
        result = parse(text, "host")
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(
            [item["body"] for item in result["items"]],
            ["First inline finding.", "Second labeled finding."],
        )

    def test_textual_aliases_accept_equal_values_and_reject_conflicts(self) -> None:
        equivalent = """
Severity: Major
Confidence: 100
Classification: introduced
Problem: Preserve one body.
Finding: Preserve one body.
Suggestion: Apply one fix.
Suggested fix: Apply one fix.
"""
        item = parse(equivalent, "codex")["items"][0]
        self.assertEqual(item["body"], "Preserve one body.")
        self.assertEqual(item["suggestion"], "Apply one fix.")
        conflicts = (
            equivalent.replace(
                "Finding: Preserve one body.",
                "Finding: Conflicting body.",
            ),
            equivalent.replace(
                "Suggested fix: Apply one fix.",
                "Suggested fix: Conflicting fix.",
            ),
        )
        for text in conflicts:
            with self.subTest(text=text):
                self.assertIsNone(parse(text, "codex"))

    def test_equivalent_anchor_representations_accept_only_equal_values(self) -> None:
        equivalent = """
Severity: Major
Confidence: 100
Classification: introduced
File:Line: src/new.py:10-12
Path: src/new.py
Line: 10-12
Original Path: src/old.py
Original File: src/old.py
Problem: Equivalent anchor aliases describe one location.
"""
        anchor = parse(equivalent, "rp")["items"][0]["anchor"]
        self.assertEqual(anchor["path"], "src/new.py")
        self.assertEqual(anchor["startLine"], 10)
        self.assertEqual(anchor["endLine"], 12)
        self.assertEqual(anchor["originalPath"], "src/old.py")
        conflicts = (
            equivalent.replace("Path: src/new.py", "Path: src/other.py"),
            equivalent.replace("Line: 10-12", "Line: 11-12"),
            equivalent.replace("Original File: src/old.py", "Original File: src/older.py"),
        )
        for text in conflicts:
            with self.subTest(text=text):
                self.assertIsNone(parse(text, "rp"))

    def test_multiple_host_finding_tables_fail_closed(self) -> None:
        valid = self.fixture("host", "catalog-sample")
        second_valid = valid.replace(
            "Currentness ignores the reviewed head.",
            "A second valid table must not be silently ignored.",
        )
        second_invalid = valid.replace("| P1 | 100 |", "| Blocker | 100 |")
        for text in (
            f"{valid}\n\nAdditional findings\n\n{second_valid}",
            f"{valid}\n\nAdditional findings\n\n{second_invalid}",
        ):
            with self.subTest(text=text):
                self.assertIsNone(parse(text, "host"))

    def test_explicit_empty_with_malformed_host_table_fails_closed(self) -> None:
        text = """
No findings.

| # | Sev | Confidence | Classification | Finding | Disposition |
| malformed separator |
| 1 | Blocker | 100 | introduced | Hidden unknown finding. | OPEN |

<verdict>SHIP</verdict>
"""
        self.assertIsNone(parse(text, "host"))

    def test_explicit_empty_with_partial_host_table_header_fails_closed(self) -> None:
        headers = (
            "| # | Sev | Confidence | Classification | Finding |",
            "| # | Sev | Confidence | Classification | Finding | Dispositon |",
        )
        for header in headers:
            with self.subTest(header=header):
                separator = "|" + "|".join("---" for _ in header.strip("|").split("|")) + "|"
                text = f"""
No findings.

{header}
{separator}
| 1 | Blocker | 100 | introduced | Hidden unknown finding. | OPEN |

<verdict>SHIP</verdict>
"""
                self.assertIsNone(parse(text, "host"))

    def test_duplicate_singleton_labels_fail_closed(self) -> None:
        cases = (
            """
Severity: Blocker
Severity: Major
Confidence: 100
Classification: introduced
Problem: An earlier unknown severity must not be overwritten.
""",
            """
Severity: Major
Confidence: 100
Classification: pre_existing
Classification: introduced
Problem: Conflicting canonical classifications must not be order-dependent.
""",
            """
Severity: Major
Confidence: 100
Classification: inherited
Classification: introduced
Problem: An earlier unknown classification must not be overwritten.
""",
            """
Severity: Major
Confidence: 100
Classification: introduced
Problem: First body.
Problem: Conflicting second body.
""",
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertIsNone(parse(text, "codex"))

    def test_duplicate_host_table_headers_fail_closed(self) -> None:
        cases = (
            """
| # | Sev | Confidence | Classification | Classification | Finding | Disposition |
|---|-----|------------|----------------|----------------|---------|-------------|
| 1 | P1 | 100 | inherited | introduced | Hidden unknown classification. | OPEN |
""",
            """
| # | Sev | Confidence | Classification | Classification | Finding | Disposition |
|---|-----|------------|----------------|----------------|---------|-------------|
| 1 | P1 | 100 | pre_existing | introduced | Conflicting classifications. | OPEN |
""",
        )
        for table in cases:
            with self.subTest(table=table):
                self.assertIsNone(parse(table, "host"))

    def test_all_bounds_reject_without_truncation(self) -> None:
        base = self.fixture("codex", "catalog-sample")
        self.assertIsNone(parse("x" * (1024 * 1024 + 1), "codex"))
        self.assertIsNone(parse(base, "x" * 161))
        self.assertIsNone(parse(base, "codex", receipt="x" * 161))
        self.assertIsNone(
            parse(
                "Severity: Major\nConfidence: 100\n"
                f"Classification: introduced\nProblem: {'x' * 4001}",
                "codex",
            )
        )
        self.assertIsNone(
            parse(
                "Severity: Major\nConfidence: 100\nClassification: introduced\n"
                f"Title: {'x' * 241}\nProblem: bounded body",
                "codex",
            )
        )
        self.assertIsNone(
            parse(
                "Severity: Major\nConfidence: 100\nClassification: introduced\n"
                f"Problem: bounded body\nSuggestion: {'x' * 4001}",
                "codex",
            )
        )
        self.assertIsNone(
            parse(
                "Severity: Major\nConfidence: 100\nClassification: introduced\n"
                f"File:Line: {'x' * 1025}:1\nProblem: bounded body",
                "codex",
            )
        )

        too_many = "\n\n".join(
            f"Severity: Minor\nConfidence: 75\nClassification: introduced\nProblem: item {number}"
            for number in range(201)
        )
        self.assertIsNone(parse(too_many, "codex"))
        too_many_ratchets = "\n".join(
            f"Prior finding {number} — fixed."
            for number in range(1, 202)
        )
        self.assertIsNone(parse(too_many_ratchets, "codex"))
        too_many_unknown_ratchets = "\n".join(
            f"Prior finding {number} — pending."
            for number in range(1, 202)
        )
        self.assertIsNone(parse(too_many_unknown_ratchets, "codex"))

        oversized_items = "\n\n".join(
            "Severity: Minor\nConfidence: 75\nClassification: introduced\n"
            f"Title: item {number}\nProblem: {'x' * 3900}"
            for number in range(70)
        )
        self.assertLess(len(oversized_items.encode("utf-8")), 1024 * 1024)
        self.assertIsNone(parse(oversized_items, "codex"))
        self.assertIsNone(parse(base, "codex", round_number=0))
        self.assertIsNone(parse(base, "codex", review_kind="unknown"))
        self.assertIsNone(parse(base, "codex", head_sha=""))
        self.assertIsNone(parse(base, "codex", base_sha="x" * 161))
        self.assertIsNone(parse(base, "codex", supersedes="x" * 161))
        self.assertIsNone(parse(base, "codex", supersedes="receipt-round-1"))

    def test_rid_array_limit_rejects_and_no_duplicate_ids(self) -> None:
        rids = " ".join(f"R{number}" for number in range(1, 34))
        text = (
            "Severity: Minor\nConfidence: 75\nClassification: introduced\n"
            f"Problem: references {rids}"
        )
        self.assertIsNone(parse(text, "codex"))

    def test_prior_container_is_bounded_and_strictly_validated_before_reuse(self) -> None:
        prior = parse(self.fixture("codex", "catalog-sample"), "codex")
        ratchet = "Prior finding 1 — fixed.\n<verdict>SHIP</verdict>"
        oversized = json.loads(json.dumps(prior))
        oversized["items"] = [
            {
                **oversized["items"][0],
                "id": f"finding-{number}",
                "ordinal": number,
            }
            for number in range(1, 202)
        ]
        self.assertIsNone(
            parse(
                ratchet,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=oversized,
                supersedes="receipt-round-1",
            )
        )

        for field, value in (
            ("id", "finding-forged"),
            ("firstSeenReceiptId", "receipt-forged"),
            ("lastSeenReceiptId", "receipt-forged"),
        ):
            corrupt = json.loads(json.dumps(prior))
            corrupt["items"][0][field] = value
            self.assertIsNone(
                parse(
                    ratchet,
                    "codex",
                    receipt="receipt-round-2",
                    round_number=2,
                    prior=corrupt,
                    supersedes="receipt-round-1",
                ),
                field,
            )

        for anchor_update in (
            {"endLine": "12"},
            {"endLine": 1},
            {"originalPath": "../outside.py"},
            {"blobOid": "not-a-blob"},
            {"path": 123},
        ):
            corrupt = json.loads(json.dumps(prior))
            corrupt["items"][0]["anchor"].update(anchor_update)
            self.assertIsNone(
                parse(
                    ratchet,
                    "codex",
                    receipt="receipt-round-2",
                    round_number=2,
                    prior=corrupt,
                    supersedes="receipt-round-1",
                ),
                anchor_update,
            )

        extra = json.loads(json.dumps(prior))
        extra["items"][0]["unknown"] = "field"
        self.assertIsNone(
            parse(
                ratchet,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=extra,
                supersedes="receipt-round-1",
            )
        )

        for field, value in (
            ("schemaVersion", True),
            ("reviewKind", ["implementation"]),
        ):
            corrupt = json.loads(json.dumps(prior))
            corrupt[field] = value
            self.assertIsNone(
                parse(
                    ratchet,
                    "codex",
                    receipt="receipt-round-2",
                    round_number=2,
                    prior=corrupt,
                    supersedes="receipt-round-1",
                ),
                field,
            )
        boolean_confidence = json.loads(json.dumps(prior))
        boolean_confidence["items"][0]["confidence"] = False
        self.assertIsNone(
            parse(
                ratchet,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=boolean_confidence,
                supersedes="receipt-round-1",
            )
        )

        oversized_bytes = json.loads(json.dumps(prior))
        oversized_bytes["items"] = [
            {
                **oversized_bytes["items"][0],
                "id": f"finding-{number}",
                "ordinal": number,
                "title": f"item {number}",
                "body": "x" * 3900,
            }
            for number in range(1, 71)
        ]
        encoded = json.dumps(
            oversized_bytes,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.assertGreater(len(encoded), 256 * 1024)
        self.assertIsNone(
            parse(
                ratchet,
                "codex",
                receipt="receipt-round-2",
                round_number=2,
                prior=oversized_bytes,
                supersedes="receipt-round-1",
            )
        )

    def test_arbitrary_text_never_raises(self) -> None:
        samples = [
            "",
            "\x00\udcff",
            object(),
            None,
            {"unexpected": "mapping"},
            ["unexpected", "list"],
        ]
        for sample in samples:
            with self.subTest(sample=type(sample).__name__):
                self.assertIsNone(parse(sample, "codex"))


if __name__ == "__main__":
    unittest.main()
