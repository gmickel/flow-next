"""Codex-mirror parity for the GitLab (fn-69.3) and Jira (fn-70.4) tracker adapters.

The Codex mirror at `plugins/flow-next/codex/` is a DERIVED artifact regenerated
by `scripts/sync-codex.sh`. A missing sync rule silently degrades Codex parity, so
this test pins the load-bearing invariants for the per-adapter references:

  * The canonical `references/<adapter>.md` is mirrored into the codex/ tree (the
    adapter reference must exist on the Codex side, not only Claude's).
  * The mirror's `<adapter>.md` is content-faithful to the canonical — every
    non-blank line of the canonical survives into the mirror modulo the sync
    script's leading-whitespace normalization inside fenced code blocks. (Neither
    gitlab.md nor jira.md carries `AskUserQuestion` prose, so no tool-name rewrite
    applies; a faithful copy is the contract.)
  * The mirror's tracker-sync `openai.yaml` `short_description` includes "GitLab"
    AND "Jira" (the registration metadata Codex surfaces).
  * The `scripts/sync-codex.sh` registration line for flow-next-tracker-sync names
    GitLab AND Jira (the single source the openai.yaml is generated from).
  * The transport-vocabulary rung (`glab` / `rest`) survives into the mirror's
    SKILL.md / steps.md / adapter-interface.md (the receipt `--transport` enum;
    Jira's REST rung reuses `rest`).

These guard the fn-69.3 / fn-70.4 acceptance: "the named parity test asserting the
canonical adapter reference is mirrored into codex/ AND openai.yaml includes the
tracker name."

Run:
    python3 -m unittest discover -s plugins/flow-next/tests -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]

TRACKER_SKILL = REPO_ROOT / "plugins" / "flow-next" / "skills" / "flow-next-tracker-sync"
TRACKER_MIRROR = REPO_ROOT / "plugins" / "flow-next" / "codex" / "skills" / "flow-next-tracker-sync"

CANON_GITLAB = TRACKER_SKILL / "references" / "gitlab.md"
MIRROR_GITLAB = TRACKER_MIRROR / "references" / "gitlab.md"

CANON_JIRA = TRACKER_SKILL / "references" / "jira.md"
MIRROR_JIRA = TRACKER_MIRROR / "references" / "jira.md"

MIRROR_OPENAI_YAML = TRACKER_MIRROR / "agents" / "openai.yaml"
SYNC_CODEX_SH = REPO_ROOT / "scripts" / "sync-codex.sh"


def _normalize(text: str) -> list[str]:
    """Content lines with ALL runs of whitespace collapsed to one space, blanks dropped.

    The sync script normalizes whitespace (it collapses the leading/internal
    indentation the canonical uses inside fenced code-block comments to a single
    space) and deliberately STRIPS the canonical's trailing "Codex mirror
    (sync-codex.sh)..." meta-note (the R4 no-meta-file-refs rule). So an exact byte
    compare is brittle by design. We collapse whitespace and compare *content*,
    which still catches any genuine content drift while tolerating those transforms.
    """
    out = []
    for ln in text.splitlines():
        collapsed = re.sub(r"\s+", " ", ln).strip()
        if collapsed:
            out.append(collapsed)
    return out


class GitlabMirrorExistsTestCase(unittest.TestCase):
    def test_canonical_gitlab_reference_exists(self) -> None:
        self.assertTrue(
            CANON_GITLAB.is_file(),
            f"canonical GitLab adapter reference missing: {CANON_GITLAB}",
        )

    def test_mirror_gitlab_reference_exists(self) -> None:
        self.assertTrue(
            MIRROR_GITLAB.is_file(),
            "canonical references/gitlab.md was not mirrored into codex/ — "
            "run `bash scripts/sync-codex.sh`",
        )


class GitlabMirrorContentParityTestCase(unittest.TestCase):
    def test_mirror_adds_no_fabricated_content(self) -> None:
        """Every mirror content line traces back to the canonical.

        The sync only transforms whitespace and drops the Codex-meta note — it
        never INVENTS content. So (whitespace-collapsed) the mirror's content-line
        set must be a subset of the canonical's. A mirror line with no canonical
        origin means the sync corrupted the file.
        """
        canon = set(_normalize(CANON_GITLAB.read_text(encoding="utf-8")))
        mirror = _normalize(MIRROR_GITLAB.read_text(encoding="utf-8"))
        orphans = [ln for ln in mirror if ln not in canon]
        self.assertEqual(
            [],
            orphans,
            "codex/ gitlab.md has content lines with no canonical origin "
            f"(sync corruption?): {orphans[:5]}",
        )

    def test_mirror_preserves_bulk_of_canonical(self) -> None:
        """Nearly all canonical content survives into the mirror.

        Only the single trailing Codex-meta bullet is deliberately stripped, so the
        mirror must retain the overwhelming bulk of canonical content. A large drop
        means the sync silently lost adapter prose — a real parity failure.
        """
        canon = _normalize(CANON_GITLAB.read_text(encoding="utf-8"))
        mirror = set(_normalize(MIRROR_GITLAB.read_text(encoding="utf-8")))
        missing = [ln for ln in canon if ln not in mirror]
        # The Codex-meta note spans ~2 collapsed lines; allow a tiny slack only.
        self.assertLessEqual(
            len(missing),
            4,
            f"codex/ gitlab.md dropped {len(missing)} canonical content lines "
            f"(stale mirror — run sync-codex.sh): e.g. {missing[:5]}",
        )

    def test_mirror_carries_load_bearing_gitlab_content(self) -> None:
        """The load-bearing GitLab adapter facts are present in the mirror."""
        mirror = MIRROR_GITLAB.read_text(encoding="utf-8")
        for marker in (
            "glab",
            "is_blocked_by",
            "CI_JOB_TOKEN",
            "access_level",
            "listOpenIssues",
            "/api/v4",
        ):
            self.assertIn(
                marker,
                mirror,
                f"mirror gitlab.md lost the load-bearing GitLab marker: {marker!r}",
            )


class JiraMirrorExistsTestCase(unittest.TestCase):
    def test_canonical_jira_reference_exists(self) -> None:
        self.assertTrue(
            CANON_JIRA.is_file(),
            f"canonical Jira adapter reference missing: {CANON_JIRA}",
        )

    def test_mirror_jira_reference_exists(self) -> None:
        self.assertTrue(
            MIRROR_JIRA.is_file(),
            "canonical references/jira.md was not mirrored into codex/ — "
            "run `bash scripts/sync-codex.sh`",
        )


class JiraMirrorContentParityTestCase(unittest.TestCase):
    def test_mirror_adds_no_fabricated_content(self) -> None:
        """Every mirror content line traces back to the canonical jira.md."""
        canon = set(_normalize(CANON_JIRA.read_text(encoding="utf-8")))
        mirror = _normalize(MIRROR_JIRA.read_text(encoding="utf-8"))
        orphans = [ln for ln in mirror if ln not in canon]
        self.assertEqual(
            [],
            orphans,
            "codex/ jira.md has content lines with no canonical origin "
            f"(sync corruption?): {orphans[:5]}",
        )

    def test_mirror_preserves_bulk_of_canonical(self) -> None:
        """Nearly all canonical jira.md content survives into the mirror."""
        canon = _normalize(CANON_JIRA.read_text(encoding="utf-8"))
        mirror = set(_normalize(MIRROR_JIRA.read_text(encoding="utf-8")))
        missing = [ln for ln in canon if ln not in mirror]
        # The Codex-meta note spans ~2 collapsed lines; allow a tiny slack only.
        self.assertLessEqual(
            len(missing),
            4,
            f"codex/ jira.md dropped {len(missing)} canonical content lines "
            f"(stale mirror — run sync-codex.sh): e.g. {missing[:5]}",
        )

    def test_mirror_carries_load_bearing_jira_content(self) -> None:
        """The load-bearing Jira adapter facts are present in the mirror."""
        mirror = MIRROR_JIRA.read_text(encoding="utf-8")
        for marker in (
            "/rest/api/",
            "ADF",
            "transition",
            "issueLink",
            "remotelink",
            "listOpenIssues",
            "authScheme",
        ):
            self.assertIn(
                marker,
                mirror,
                f"mirror jira.md lost the load-bearing Jira marker: {marker!r}",
            )


class TrackerSyncRegistrationIncludesGitlabTestCase(unittest.TestCase):
    def test_mirror_openai_yaml_names_gitlab(self) -> None:
        self.assertTrue(MIRROR_OPENAI_YAML.is_file(), f"missing {MIRROR_OPENAI_YAML}")
        text = MIRROR_OPENAI_YAML.read_text(encoding="utf-8")
        self.assertIn(
            "GitLab",
            text,
            "tracker-sync mirror openai.yaml short_description must include GitLab",
        )

    def test_mirror_openai_yaml_names_jira(self) -> None:
        self.assertTrue(MIRROR_OPENAI_YAML.is_file(), f"missing {MIRROR_OPENAI_YAML}")
        text = MIRROR_OPENAI_YAML.read_text(encoding="utf-8")
        self.assertIn(
            "Jira",
            text,
            "tracker-sync mirror openai.yaml short_description must include Jira",
        )

    def test_sync_codex_registration_line_names_gitlab(self) -> None:
        text = SYNC_CODEX_SH.read_text(encoding="utf-8")
        reg_lines = [
            ln for ln in text.splitlines() if "flow-next-tracker-sync" in ln and "generate_openai_yaml" in ln
        ]
        self.assertTrue(
            reg_lines,
            "no generate_openai_yaml registration line for flow-next-tracker-sync in sync-codex.sh",
        )
        self.assertTrue(
            any("GitLab" in ln for ln in reg_lines),
            "the flow-next-tracker-sync generate_openai_yaml registration line must name GitLab",
        )

    def test_sync_codex_registration_line_names_jira(self) -> None:
        text = SYNC_CODEX_SH.read_text(encoding="utf-8")
        reg_lines = [
            ln for ln in text.splitlines() if "flow-next-tracker-sync" in ln and "generate_openai_yaml" in ln
        ]
        self.assertTrue(
            reg_lines,
            "no generate_openai_yaml registration line for flow-next-tracker-sync in sync-codex.sh",
        )
        self.assertTrue(
            any("Jira" in ln for ln in reg_lines),
            "the flow-next-tracker-sync generate_openai_yaml registration line must name Jira",
        )


class TransportVocabularyMirroredTestCase(unittest.TestCase):
    """The GitLab transport rung (glab / rest) must survive into the mirror."""

    def test_mirror_skill_records_glab_rest_transport(self) -> None:
        text = (TRACKER_MIRROR / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r"glab\s*/\s*rest",
            "mirror SKILL.md transport-choice prose must include the glab / rest rung",
        )

    def test_mirror_steps_records_glab_rest_transport_enum(self) -> None:
        text = (TRACKER_MIRROR / "steps.md").read_text(encoding="utf-8")
        self.assertIn(
            "glab,rest",
            text,
            "mirror steps.md --transport enum must include glab,rest",
        )

    def test_mirror_adapter_interface_records_transport_enum(self) -> None:
        text = (TRACKER_MIRROR / "references" / "adapter-interface.md").read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r"--transport\s+mcp\|graphql\|gh\|glab\|rest\|none",
            "mirror adapter-interface.md must carry the full --transport enum incl. glab|rest",
        )


if __name__ == "__main__":
    unittest.main()
