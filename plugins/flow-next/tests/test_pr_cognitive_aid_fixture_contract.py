"""Canonical v1 fixture, cross-render parity, vendoring, and image contracts."""

import hashlib
import json
import re
import struct
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "plugins" / "flow-next" / "scripts"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import flowctl  # noqa: E402


FIXTURE_DIR = (
    REPO_ROOT / "plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1"
)
GOLDEN = FIXTURE_DIR / "golden.json"
METADATA = FIXTURE_DIR / "golden.meta.json"
CONSUMER_DOC = REPO_ROOT / "plugins/flow-next/docs/pr-cognitive-aid.md"
SPEC = (
    REPO_ROOT
    / ".flow/specs/fn-136-structured-review-artifact-schema-in.md"
)
IMAGE_NAMES = (
    "change-walkthrough-overview.jpeg",
    "change-walkthrough-expanded-diff.jpeg",
    "change-walkthrough-grouped-files.jpeg",
)
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


class FixtureMetadataTests(unittest.TestCase):
    def test_metadata_pins_exact_canonical_bytes(self) -> None:
        metadata = _read_json(METADATA)
        encoded = GOLDEN.read_bytes()
        self.assertEqual(metadata["schemaVersion"], 1)
        self.assertRegex(metadata["sourceBlob"], r"^[0-9a-f]{40}$")
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
                "clock": "time.process_time",
                "operation": "validation-plus-markdown-render",
                "p95MillisecondsExclusive": 100,
                "warmRuns": 30,
            },
        )
        self.assertEqual(encoded[-1:], b"\n")
        source_bytes = subprocess.run(
            ["git", "cat-file", "blob", metadata["sourceBlob"]],
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


class CrossRenderParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = _read_json(GOLDEN)
        cls.rendered = flowctl.render_pr_cognitive_aid_markdown(cls.artifact)

    # fn-252 makes markdown a bounded briefing; the stored artifact stays the
    # lossless record, not visible per-file tables or provenance badges.
    def test_markdown_keeps_identity_in_one_comment(self) -> None:
        artifact = self.artifact
        self.assertEqual(re.findall(r"<!--.*?-->", self.rendered), [
            f"<!-- artifact={artifact['artifactId']} base={artifact['baseSha']} head={artifact['headSha']} -->"
        ])

    def test_maximum_fixture_renders_briefing(self) -> None:
        self.assertIn("## Why", self.rendered)
        self.assertIn("## Reading order", self.rendered)
        self.assertNotIn("<details", self.rendered)


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


if __name__ == "__main__":
    unittest.main()
