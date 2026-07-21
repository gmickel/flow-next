"""fn-121 R16 - pre-check mode contract across every carrier skill.

Asserts, for every skill carrying the fn-95 setup-version pre-check:
- blocking carriers (FLOW_SETUP_ASK) gained the plugin-mode branch: a
  ``setup_mode`` read, the CLAUDE.md sentinel compare against the plugin's
  expected snippet schema version, and the ``FLOW_SNIPPET_ASK`` emit;
- each variant's autonomy-suppression markers are preserved inside the
  plugin-mode branch (mode:autofix carriers keep that token; tracker-sync
  keeps DISPATCH=forked);
- the copy-mode path (the original version compare + FLOW_SETUP_ASK emit)
  is retained unchanged;
- ralph-init is EXEMPT: no plugin-mode silence (its scripts/ralph copies
  genuinely drift), so it must NOT contain the plugin branch;
- notice-only carriers (pilot, land, map) skip their stale notice in
  plugin mode via the ``"$SETUP_MODE" != "plugin"`` guard;
- the slim snippet template carries the exact engine markers, the internal
  sentinel matching flowctl's SNIPPET_SCHEMA_VERSION, and no ``.flow/bin/``
  path;
- the version literal in every pre-check block matches flowctl.py's
  SNIPPET_SCHEMA_VERSION (single-source enforcement).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
FLOWCTL_PY = ROOT / "scripts" / "flowctl.py"
PLUGIN_TEMPLATE = SKILLS / "flow-next-setup" / "templates" / "claude-md-snippet-plugin.md"

BLOCKING = [
    "flow-next-audit",
    "flow-next-capture",
    "flow-next-interview",
    "flow-next-make-pr",
    "flow-next-memory-migrate",
    "flow-next-plan",
    "flow-next-prime",
    "flow-next-prospect",
    "flow-next-qa",
    "flow-next-resolve-pr",
    "flow-next-strategy",
    "flow-next-sync",
    "flow-next-tracker-sync",
    "flow-next-work",
]
AUTOFIX_VARIANT = {"flow-next-audit", "flow-next-capture", "flow-next-memory-migrate"}
NOTICE_ONLY = ["flow-next-pilot", "flow-next-land", "flow-next-map"]
EXEMPT = "flow-next-ralph-init"

SETUP_MODE_READ = "SETUP_MODE=$(jq -r '.setup_mode // empty' .flow/meta.json 2>/dev/null)"
PLUGIN_BRANCH = 'if [[ "$SETUP_MODE" == "plugin" ]]; then'
SENTINEL_GREP = "grep -m1 -o 'flow-next:snippet:v[0-9]*' CLAUDE.md"
SNIPPET_ASK = "FLOW_SNIPPET_ASK"
SETUP_ASK = "FLOW_SETUP_ASK"
NOTICE_GUARD = 'if [[ "$SETUP_MODE" != "plugin" && -n "$SETUP_VER"'


def _flowctl_schema_version() -> int:
    m = re.search(
        r"^SNIPPET_SCHEMA_VERSION = (\d+)$",
        FLOWCTL_PY.read_text(encoding="utf-8"),
        re.M,
    )
    assert m, "SNIPPET_SCHEMA_VERSION missing from flowctl.py"
    return int(m.group(1))


def _skill_text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


class PrecheckModeContractTest(unittest.TestCase):
    def test_blocking_carriers_have_plugin_branch(self) -> None:
        for name in BLOCKING:
            with self.subTest(skill=name):
                text = _skill_text(name)
                self.assertIn(SETUP_MODE_READ, text)
                self.assertIn(PLUGIN_BRANCH, text)
                self.assertIn(SENTINEL_GREP, text)
                self.assertIn(SNIPPET_ASK, text)
                # copy-mode path retained
                self.assertIn(SETUP_ASK, text)
                self.assertIn(
                    'elif [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown"',
                    text,
                )

    def test_plugin_branch_preserves_variant_autonomy_markers(self) -> None:
        for name in BLOCKING:
            with self.subTest(skill=name):
                text = _skill_text(name)
                branch = text[text.index(PLUGIN_BRANCH):text.index("elif [[")]
                for marker in ("FLOW_RALPH", "REVIEW_RECEIPT_PATH", "FLOW_AUTONOMOUS"):
                    self.assertIn(marker, branch, f"{name}: {marker} lost")
                if name in AUTOFIX_VARIANT:
                    self.assertIn("mode:autofix", branch, name)
                if name == "flow-next-tracker-sync":
                    self.assertIn('"${DISPATCH:-}" == "forked"', branch)
                self.assertIn('"$SNIP_ACK" == "1"', branch)

    def test_version_literal_matches_flowctl_constant(self) -> None:
        expected = _flowctl_schema_version()
        for name in BLOCKING:
            with self.subTest(skill=name):
                text = _skill_text(name)
                self.assertIn(
                    '"${SNIP_VER:-missing}" != "%d"' % expected,
                    text,
                    f"{name}: pre-check literal drifted from SNIPPET_SCHEMA_VERSION",
                )

    def test_ralph_init_is_exempt(self) -> None:
        text = _skill_text(EXEMPT)
        self.assertNotIn(PLUGIN_BRANCH, text)
        self.assertNotIn(SNIPPET_ASK, text)
        # its copy-refresh version ask must survive in both modes
        self.assertIn(SETUP_ASK, text)

    def test_notice_only_carriers_skip_in_plugin_mode(self) -> None:
        for name in NOTICE_ONLY:
            with self.subTest(skill=name):
                text = _skill_text(name)
                self.assertIn(SETUP_MODE_READ, text)
                self.assertIn(NOTICE_GUARD, text)
                self.assertNotIn(SNIPPET_ASK, text)

    def test_slim_template_shape(self) -> None:
        text = PLUGIN_TEMPLATE.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertEqual(lines[0], "<!-- BEGIN FLOW-NEXT -->")
        self.assertEqual(lines[-1], "<!-- END FLOW-NEXT -->")
        expected = _flowctl_schema_version()
        self.assertEqual(lines[1], "<!-- flow-next:snippet:v%d -->" % expected)
        self.assertNotIn(".flow/bin", text)
        self.assertNotIn("TodoWrite or", text)  # guard against accidental dilution
        self.assertIn("flowctl usage", text)
        self.assertIn("Orchestration & model steering", text)
        # the not-found fallback line
        self.assertIn("/flow-next:setup", text)


if __name__ == "__main__":
    unittest.main()
