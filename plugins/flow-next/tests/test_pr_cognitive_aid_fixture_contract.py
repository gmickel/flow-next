"""Canonical v1 fixture, cross-render parity, vendoring, and image contracts."""

import hashlib
import json
import re
import struct
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flowctl  # noqa: E402


FIXTURE_DIR = (
    REPO_ROOT / "plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1"
)
GOLDEN = FIXTURE_DIR / "golden.json"
METADATA = FIXTURE_DIR / "golden.meta.json"
CONSUMER_DOC = REPO_ROOT / "plugins/flow-next/docs/pr-cognitive-aid.md"
HTML_DOC = REPO_ROOT / "plugins/flow-next/docs/html-artifacts.md"
HTML_REFERENCE = (
    REPO_ROOT / "plugins/flow-next/references/html-artifacts.md"
)
HTML_LENS = (
    REPO_ROOT / "plugins/flow-next/skills/flow-next-make-pr/html-lens.md"
)
SPEC = (
    REPO_ROOT
    / ".flow/specs/fn-136-structured-review-artifact-schema-in.md"
)
IMAGE_NAMES = (
    "change-walkthrough-overview.jpeg",
    "change-walkthrough-expanded-diff.jpeg",
    "change-walkthrough-grouped-files.jpeg",
)
GROUP_BADGES = {
    "problem": "WHY",
    "principle": "PRINCIPLE",
    "step": "STEP",
    "kept": "KEPT",
    "verify": "VERIFY",
}
CHANGE_BADGES = {
    "added": "NEW",
    "modified": "MODIFIED",
    "deleted": "DELETED",
    "renamed": "RENAMED",
    "copied": "COPIED",
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _jpeg_dimensions(path: Path) -> tuple[int, int]:
    """Read JPEG SOF dimensions without an image-library dependency."""
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            raise AssertionError(f"{path} is not a JPEG")
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                raise AssertionError(f"{path} has no JPEG SOF marker")
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            code = marker[0]
            if code in {0xD8, 0xD9} or 0xD0 <= code <= 0xD7:
                continue
            length_bytes = handle.read(2)
            if len(length_bytes) != 2:
                raise AssertionError(f"{path} has a truncated JPEG segment")
            length = struct.unpack(">H", length_bytes)[0]
            if code in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:
                payload = handle.read(length - 2)
                height, width = struct.unpack(">HH", payload[1:5])
                return width, height
            handle.seek(length - 2, 1)


def _relative_markdown_targets(path: Path) -> list[Path]:
    text = path.read_text(encoding="utf-8")
    targets = []
    for raw in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        target = raw.strip().split("#", 1)[0]
        if (
            not target
            or target.startswith(("#", "http://", "https://", "mailto:"))
            or "<" in target
        ):
            continue
        targets.append((path.parent / target).resolve())
    return targets


class _SemanticCarrierParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capturing = False
        self.payload = ""

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        self._capturing = (
            tag == "script"
            and values.get("id") == "flow-next-pr-cognitive-aid"
            and values.get("type") == "application/json"
        )

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self.payload += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._capturing = False


class FixtureMetadataTests(unittest.TestCase):
    def test_metadata_pins_exact_canonical_bytes(self) -> None:
        metadata = _read_json(METADATA)
        encoded = GOLDEN.read_bytes()
        self.assertEqual(metadata["schemaVersion"], 1)
        self.assertRegex(metadata["sourceCommit"], r"^[0-9a-f]{40}$")
        self.assertEqual(
            metadata["sourcePath"], GOLDEN.relative_to(REPO_ROOT).as_posix()
        )
        self.assertEqual(
            metadata["sha256"], hashlib.sha256(encoded).hexdigest()
        )
        self.assertEqual(
            metadata["performanceBudget"],
            {
                "operation": "validation-plus-markdown-render",
                "p95MillisecondsExclusive": 100,
                "warmRuns": 30,
            },
        )
        self.assertEqual(encoded[-1:], b"\n")
        source_bytes = subprocess.run(
            [
                "git",
                "show",
                f"{metadata['sourceCommit']}:{metadata['sourcePath']}",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(source_bytes, encoded)

    def test_fixture_is_valid_maximum_normal_v1(self) -> None:
        artifact = _read_json(GOLDEN)
        self.assertIs(flowctl.validate_pr_cognitive_aid(artifact), artifact)
        groups = artifact["changeWalkthrough"]["groups"]
        files = [item for group in groups for item in group["files"]]
        self.assertEqual(len(artifact["sources"]), 128)
        self.assertEqual(len(artifact["changeWalkthrough"]["proof"]), 16)
        self.assertEqual(len(groups), 11)
        self.assertEqual(len(files), 500)
        self.assertEqual(
            [group["kind"] for group in groups],
            ["problem", "principle", *(["step"] * 7), "kept", "verify"],
        )

    def test_consumer_doc_defines_offline_byte_pinned_vendoring(self) -> None:
        text = " ".join(
            CONSUMER_DOC.read_text(encoding="utf-8").split()
        )
        for phrase in (
            "byte-identical copies of both files",
            "pinned upstream `sha256`",
            "No Flow-Next checkout",
            "cross-repository network",
            "schema requires a new versioned fixture directory",
            "Never regenerate or pretty-print",
            "strict `<100 ms p95` over 30 warm runs",
            "`performanceBudget.p95MillisecondsExclusive` as an exclusive upper bound",
        ):
            self.assertIn(phrase, text)


class CrossRenderParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = _read_json(GOLDEN)
        cls.rendered = flowctl.render_pr_cognitive_aid_markdown(cls.artifact)

    def test_markdown_preserves_identity_and_currentness(self) -> None:
        artifact = self.artifact
        self.assertIn(
            f"| Artifact | `{artifact['artifactId']}` | artifact identity |",
            self.rendered,
        )
        self.assertIn(
            f"| Base commit | `{artifact['baseSha']}` | artifact currentness |",
            self.rendered,
        )
        self.assertIn(
            f"| Head commit | `{artifact['headSha']}` | artifact identity |",
            self.rendered,
        )

    def test_markdown_preserves_group_order_kinds_and_sources(self) -> None:
        positions = []
        for group in self.artifact["changeWalkthrough"]["groups"]:
            summary = (
                f"<summary><code>{GROUP_BADGES[group['kind']]}</code> "
                f"{group['ordinal']}. {group['title']} — {group['summary']}"
                "</summary>"
            )
            positions.append(self.rendered.index(summary))
            for source_ref in group["sourceRefs"]:
                self.assertIn(f"source:{source_ref}", self.rendered)
        self.assertEqual(positions, sorted(positions))

    def test_markdown_preserves_every_file_semantic(self) -> None:
        for group in self.artifact["changeWalkthrough"]["groups"]:
            for file_record in group["files"]:
                with self.subTest(path=file_record["path"]):
                    expected = flowctl._pr_aid_file_row(file_record)
                    self.assertEqual(self.rendered.count(expected), 1)
                    self.assertIn(
                        f"`{CHANGE_BADGES[file_record['changeType']]}`",
                        expected,
                    )
                    self.assertIn(
                        f"`{file_record['attentionClass'].upper()}`",
                        expected,
                    )
                    for rid in file_record["rIds"]:
                        self.assertIn(f"R-ID:{rid}", expected)
                    for task_id in file_record["taskIds"]:
                        self.assertIn(f"task:{task_id}", expected)

    def test_kept_and_verify_remain_first_class(self) -> None:
        self.assertIn("<code>KEPT</code> 10. Kept", self.rendered)
        self.assertIn("<code>VERIFY</code> 11. Verify", self.rendered)

    def test_optional_html_contract_consumes_same_validated_object(self) -> None:
        canonical = flowctl.validate_pr_cognitive_aid(_read_json(GOLDEN))
        carrier = flowctl.render_pr_cognitive_aid_html_input(canonical)
        parser = _SemanticCarrierParser()
        parser.feed(f"<!doctype html><html><body>{carrier}</body></html>")
        html_input = json.loads(parser.payload)
        self.assertEqual(html_input, canonical)
        self.assertEqual(
            [
                item["path"]
                for group in html_input["changeWalkthrough"]["groups"]
                for item in group["files"]
            ],
            [
                item["path"]
                for group in canonical["changeWalkthrough"]["groups"]
                for item in group["files"]
            ],
        )
        self.assertEqual(
            sum(
                len(group["files"])
                for group in html_input["changeWalkthrough"]["groups"]
            ),
            500,
        )
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (CONSUMER_DOC, HTML_DOC, HTML_REFERENCE, HTML_LENS)
        )
        for phrase in (
            "exact validated object",
            "artifact identity/currentness",
            "group order",
            "file membership",
            "changeType",
            "attentionClass",
            "file-level R-ID/task links",
            "deliberate non-changes",
            "verification",
            "never mixed",
            "flow-next-pr-cognitive-aid",
            "local-only",
        ):
            self.assertIn(phrase, combined)

    def test_optional_html_runs_after_aid_and_cannot_stale_current_input(self) -> None:
        workflow = (
            REPO_ROOT
            / "plugins/flow-next/skills/flow-next-make-pr/workflow.md"
        ).read_text(encoding="utf-8")
        aid_phase = workflow.index(
            "## Phase 1.5: Structured PR cognitive-aid"
        )
        html_phase = workflow.index(
            "## Phase 1.5b: HTML render lens"
        )
        self.assertLess(aid_phase, html_phase)
        lens = HTML_LENS.read_text(encoding="utf-8")
        current_branch = lens.split(
            'if [[ "$HTML_AID_STATUS" == "current" ]]; then', 1
        )[1].split(
            "elif git check-ignore --no-index -q", 1
        )[0]
        self.assertIn("LINK_MODE=local", current_branch)
        self.assertNotIn("git add", current_branch)
        self.assertNotIn("git commit", current_branch)


class ReferenceAssetTests(unittest.TestCase):
    def test_three_high_resolution_images_exist(self) -> None:
        image_dir = REPO_ROOT / ".flow/assets/pr-aid"
        self.assertEqual(
            sorted(path.name for path in image_dir.glob("*.jpeg")),
            sorted(IMAGE_NAMES),
        )
        for name in IMAGE_NAMES:
            with self.subTest(name=name):
                width, height = _jpeg_dimensions(image_dir / name)
                self.assertGreaterEqual(width, 1900)
                self.assertGreaterEqual(height, 1300)

    def test_spec_and_consumer_links_resolve_repository_relatively(self) -> None:
        for document in (SPEC, CONSUMER_DOC):
            with self.subTest(document=document.relative_to(REPO_ROOT)):
                targets = _relative_markdown_targets(document)
                self.assertTrue(targets)
                for target in targets:
                    self.assertTrue(
                        target.exists(),
                        f"{document.relative_to(REPO_ROOT)} -> {target}",
                    )
        spec_text = SPEC.read_text(encoding="utf-8")
        consumer_text = CONSUMER_DOC.read_text(encoding="utf-8")
        for name in IMAGE_NAMES:
            self.assertIn(name, spec_text)
            self.assertIn(name, consumer_text)
        self.assertIn(
            "normative interaction and information-architecture references",
            spec_text,
        )
        self.assertIn(
            "normative hierarchy and interaction", consumer_text
        )


if __name__ == "__main__":
    unittest.main()
