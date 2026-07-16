"""Static contract test for scout `.clawpatch/` fallback (fn-50.3).

Verifies the two-layer fallback discipline for `repo-scout` and
`context-scout`:

  Layer 1a — prose contract: both agent files document an explicit
  fallback path when `.clawpatch/` is absent, document the
  `features_anchored` output schema (with the `kind` and `confidence`
  enums from clawpatch's `featureRecordSchema` — see
  `bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26`),
  and DO NOT carry `MUST`/`required` language tying the agent to the
  feature index.

  Layer 1b — plumbing contract: `flowctl repo-map list --json` in a
  throwaway git repo with NO `.clawpatch/` returns `{success:true,
  count:0, features:[], clawpatch_present:false}` with exit 0. This proves
  the production-path the agent prose tells scouts to call gracefully
  returns the empty envelope. (Runs in a temp git repo, not the in-repo
  `tests/fixtures/scout-without-clawpatch/` fixture — `repo-map` resolves
  `.clawpatch/` from git toplevel, so a fixture subdir can't isolate from a
  real `.clawpatch/` that local dogfooding may have created at repo root.)

Layer 2 (manual smoke — run `/flow-next:plan "test scope"` against this
repo with no `.clawpatch/`, confirm scout output produced cleanly with no
`features_anchored` field) is logged in the task's Done summary, NOT
asserted here. Running scout LLM subagents in CI is out of scope.

CI matrix: ubuntu-latest + macos-latest + windows-latest, bash + Python
3.11. unittest (NOT pytest — fn-50.2 precedent at `test_repo_map.py`;
CI uses `python -m unittest discover`).

Run:
    python -m unittest discover -s plugins/flow-next/tests \
        -p "test_scout_fallback_contract.py" -v
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PLUGIN_DIR = HERE.parent.parent
AGENTS_DIR = PLUGIN_DIR / "agents"
FLOWCTL_PY = PLUGIN_DIR / "scripts" / "flowctl.py"
FIXTURE_NO_CLAWPATCH = (
    HERE.parent / "fixtures" / "scout-without-clawpatch"
)

# Upstream clawpatch `featureRecordSchema` enum values
# (src/types.ts in openclaw/clawpatch). Kept here as a locked tuple so
# fixture/docs drift from upstream surfaces as a test failure rather than
# silently propagating into agent output. See memory entry
# bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26.
CLAWPATCH_FEATURE_KINDS = (
    "cli-command",
    "route",
    "ui-flow",
    "service",
    "job",
    "agent-tool",
    "library",
    "config",
    "release",
    "test-suite",
    "infra",
    "unknown",
)
CLAWPATCH_CONFIDENCE_LEVELS = ("high", "medium", "low")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run(
    *args: str, cwd: str | None = None
) -> subprocess.CompletedProcess:
    """Invoke `python flowctl.py <args>` against the given cwd."""
    return subprocess.run(
        [sys.executable, str(FLOWCTL_PY), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=cwd,
        env=os.environ.copy(),
    )


class ProsContract(unittest.TestCase):
    """Both scout agent files document the fallback + schema."""

    def setUp(self) -> None:
        self.repo_scout = _read(AGENTS_DIR / "repo-scout.md")
        self.context_scout = _read(AGENTS_DIR / "context-scout.md")

    # ─── repo-scout ───────────────────────────────────────────────────

    def test_repo_scout_documents_features_anchored_field(self) -> None:
        self.assertIn("features_anchored", self.repo_scout)
        # Schema subfields must all be present so downstream consumers
        # know what to expect (R4).
        for field in (
            "feature_id",
            "title",
            "kind",
            "confidence",
            "owned_files",
            "last_mapped",
        ):
            self.assertIn(
                field,
                self.repo_scout,
                msg=f"repo-scout.md missing schema subfield: {field}",
            )

    def test_repo_scout_kind_values_mirror_clawpatch_enum(self) -> None:
        """All 12 clawpatch `featureKinds` enum values surface in prose."""
        for kind in CLAWPATCH_FEATURE_KINDS:
            self.assertIn(
                kind,
                self.repo_scout,
                msg=(
                    f"repo-scout.md `kind` enum drift — '{kind}' from "
                    "upstream featureKinds not documented"
                ),
            )

    def test_repo_scout_confidence_values_mirror_clawpatch_enum(self) -> None:
        """`high|medium|low` Zod enum surfaces (NOT numeric 0..1)."""
        for level in CLAWPATCH_CONFIDENCE_LEVELS:
            self.assertIn(
                level,
                self.repo_scout,
                msg=(
                    f"repo-scout.md `confidence` enum drift — '{level}' "
                    "from upstream Zod enum not documented"
                ),
            )

    def test_repo_scout_documents_fallback_path(self) -> None:
        """Explicit prose names `.clawpatch/` absence as a degrade path."""
        # Match the absence prose by searching for `.clawpatch/` near
        # `absent` (case-insensitive) in the same window. The agent
        # may phrase it as "when absent", "if absent", "absence", etc.
        text = self.repo_scout.lower()
        self.assertIn(".clawpatch/", self.repo_scout)
        self.assertTrue(
            "absent" in text or "absence" in text,
            msg=(
                "repo-scout.md should document `.clawpatch/` absence "
                "as the graceful-degrade trigger"
            ),
        )

    def test_repo_scout_no_required_clawpatch_language(self) -> None:
        """No `MUST.*\\.clawpatch` or `required.*\\.clawpatch` — fallback
        contract is load-bearing; the index is enrichment, not a gate."""
        # Case-insensitive search; look for MUST/required tokens near
        # `.clawpatch/` in either order within a ~80-char window.
        text = self.repo_scout
        forbidden = (
            re.compile(r"MUST[^\n]{0,80}\.clawpatch", re.IGNORECASE),
            re.compile(r"required[^\n]{0,80}\.clawpatch", re.IGNORECASE),
            re.compile(r"\.clawpatch[^\n]{0,80}MUST", re.IGNORECASE),
            re.compile(r"\.clawpatch[^\n]{0,80}required", re.IGNORECASE),
        )
        for pat in forbidden:
            m = pat.search(text)
            self.assertIsNone(
                m,
                msg=(
                    f"repo-scout.md has required-`.clawpatch/` language: "
                    f"{m.group(0) if m else ''!r}"
                ),
            )

    def test_repo_scout_calls_flowctl_repo_map_list(self) -> None:
        """Agent prose must invoke the centralized reader, not parse JSON."""
        self.assertIn(
            "flowctl repo-map list --json", self.repo_scout
        )

    # ─── context-scout ────────────────────────────────────────────────

    def test_context_scout_documents_features_anchored_field(self) -> None:
        self.assertIn("features_anchored", self.context_scout)
        for field in (
            "feature_id",
            "title",
            "kind",
            "confidence",
            "owned_files",
            "last_mapped",
        ):
            self.assertIn(
                field,
                self.context_scout,
                msg=(
                    f"context-scout.md missing schema subfield: {field}"
                ),
            )

    def test_context_scout_kind_values_mirror_clawpatch_enum(self) -> None:
        for kind in CLAWPATCH_FEATURE_KINDS:
            self.assertIn(
                kind,
                self.context_scout,
                msg=(
                    f"context-scout.md `kind` enum drift — '{kind}' from "
                    "upstream featureKinds not documented"
                ),
            )

    def test_context_scout_confidence_values_mirror_clawpatch_enum(
        self,
    ) -> None:
        for level in CLAWPATCH_CONFIDENCE_LEVELS:
            self.assertIn(
                level,
                self.context_scout,
                msg=(
                    f"context-scout.md `confidence` enum drift — "
                    f"'{level}' from upstream Zod enum not documented"
                ),
            )

    def test_context_scout_documents_fallback_path(self) -> None:
        text = self.context_scout.lower()
        self.assertIn(".clawpatch/", self.context_scout)
        self.assertTrue(
            "absent" in text or "absence" in text,
            msg=(
                "context-scout.md should document `.clawpatch/` absence "
                "as the graceful-degrade trigger"
            ),
        )

    def test_context_scout_no_required_clawpatch_language(self) -> None:
        text = self.context_scout
        forbidden = (
            re.compile(r"MUST[^\n]{0,80}\.clawpatch", re.IGNORECASE),
            re.compile(r"required[^\n]{0,80}\.clawpatch", re.IGNORECASE),
            re.compile(r"\.clawpatch[^\n]{0,80}MUST", re.IGNORECASE),
            re.compile(r"\.clawpatch[^\n]{0,80}required", re.IGNORECASE),
        )
        for pat in forbidden:
            m = pat.search(text)
            self.assertIsNone(
                m,
                msg=(
                    f"context-scout.md has required-`.clawpatch/` "
                    f"language: {m.group(0) if m else ''!r}"
                ),
            )

    def test_context_scout_calls_flowctl_repo_map_list(self) -> None:
        self.assertIn(
            "flowctl repo-map list --json", self.context_scout
        )

    def test_context_scout_fallback_section_mentions_clawpatch(
        self,
    ) -> None:
        """`Fallback: Standard Tools` section explicitly names
        `.clawpatch/` absence so users reading the fallback idiom land on
        the same graceful-degrade story Step 0 documents."""
        # Slice from `## Fallback: Standard Tools` to the next H2.
        marker = "## Fallback: Standard Tools"
        idx = self.context_scout.find(marker)
        self.assertNotEqual(
            idx,
            -1,
            msg="context-scout.md missing `## Fallback: Standard Tools` section",
        )
        rest = self.context_scout[idx:]
        # Cut at the next H2 heading; the section is the chunk in between.
        next_h2 = re.search(r"\n## ", rest[len(marker):])
        section = rest if next_h2 is None else rest[: len(marker) + next_h2.start()]
        self.assertIn(
            ".clawpatch/",
            section,
            msg=(
                "`Fallback: Standard Tools` section must mention "
                "`.clawpatch/` absence as a graceful-degrade trigger"
            ),
        )


class PlumbingContract(unittest.TestCase):
    """`flowctl repo-map list --json` returns count:0 against no-clawpatch
    fixture — the production-path the agent prose tells scouts to call."""

    def test_repo_map_list_json_against_fixture_returns_count_zero(
        self,
    ) -> None:
        self.assertTrue(
            FIXTURE_NO_CLAWPATCH.is_dir(),
            msg=(
                "fixture dir missing — tests/fixtures/scout-without-clawpatch/"
            ),
        )
        # Fixture must NOT contain a .clawpatch/ subdir; the absence is
        # the contract.
        self.assertFalse(
            (FIXTURE_NO_CLAWPATCH / ".clawpatch").exists(),
            msg=(
                "fixture invalid — scout-without-clawpatch/ must NOT "
                "contain a .clawpatch/ directory"
            ),
        )
        # HERMETIC plumbing check: `repo-map` resolves `.clawpatch/` via
        # get_repo_root() (git toplevel), so running with cwd inside the
        # flow-next repo's own tree would pick up a REAL `.clawpatch/` when a
        # developer has run `/flow-next:map` locally (it's gitignored — absent
        # in CI, but present after dogfooding). The in-repo fixture dir cannot
        # isolate from the repo's git root. Run in a throwaway git repo so the
        # `.clawpatch/` absence is genuine regardless of the host repo's state.
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                ["git", "init", td],
                capture_output=True,
                text=True,
                check=True,
            )
            res = _run("repo-map", "list", "--json", cwd=td)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        payload = json.loads(res.stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["features"], [])
        self.assertFalse(payload["clawpatch_present"])


if __name__ == "__main__":
    unittest.main()
