"""fn-88.4 — model-routing scaffold: template shape, probe-composition transform,
uninstall marker removal, and setup-ceremony prose contracts.

All deterministic (no LLM in the loop). The scaffold ships as prose the host
agent executes, so the tests lock the two *documented algorithms* — probe
composition (setup workflow.md) and marker removal (uninstall.md) — via a
reference implementation of each, and assert the canonical template + skill prose
carry the exact contract the algorithm depends on. Prose-only review is NOT
acceptable coverage for any of this (spec fn-88 R8).

Four groups:
  (a) template shape — `templates/model-routing-snippet.md` exists, well-formed
      marker pair, within the ≤ ~45 always-loaded-line budget, every CLI-dependent
      route line carries a probe sentinel, and no active CLI route sits OUTSIDE a
      sentinel line (structural enforcement of R10 — no silently active route to a
      missing binary).
  (b) probe composition — a reference line-transform (mirroring workflow.md
      steps 2) validated for all four HAVE_CODEX×HAVE_CURSOR states: a failing
      probe leaves NO active route to that CLI (its lines become inert install-note
      comments); a passing probe strips the sentinel to an active line.
  (c) uninstall removal — a reference marker-removal transform (mirroring
      uninstall.md): well-formed → removed inclusive; every damaged state
      (0/2 starts, 0/2 ends, out-of-order) → untouched. PLUS prose-contract
      assertions on `commands/flow-next/uninstall.md`.
  (d) workflow prose contracts on the setup skill (canonical AND Codex mirror):
      headless-skip rule, frozen option strings (as-built casing), never-pre-set
      `work.delegateConsent`, scaffold processing ordered after the Docs block.

Run:
    python3 -m unittest plugins.flow-next.tests.test_model_routing_scaffold -v
"""

from __future__ import annotations

import itertools
import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN = REPO_ROOT / "plugins" / "flow-next"

TEMPLATE = PLUGIN / "skills" / "flow-next-setup" / "templates" / "model-routing-snippet.md"
UNINSTALL = PLUGIN / "commands" / "flow-next" / "uninstall.md"
CANONICAL_WORKFLOW = PLUGIN / "skills" / "flow-next-setup" / "workflow.md"
MIRROR_WORKFLOW = PLUGIN / "codex" / "skills" / "flow-next-setup" / "workflow.md"

START = "<!-- flow-next:model-routing:start -->"
END = "<!-- flow-next:model-routing:end -->"
SENTINEL_RE = re.compile(r"^<!-- probe:(codex|cursor|grok) --> (.*)$")

# Active-CLI-route tokens: strings that only work if that CLI is installed.
# Model NAMES (`gpt-5.6-sol`, `composer-2.5`, `grok-4.5`) are deliberately NOT
# here — they name rows in the scores table and rules and are valid anywhere;
# only the binary / wiring invocations gate on a probe. (`grok-4.5-high` reached
# via `cursor-agent --model` is a CURSOR route, not a grok-binary route.)
CODEX_ROUTE_TOKENS = ("codex exec", "delegate:codex", "review.backend codex")
CURSOR_ROUTE_TOKENS = ("cursor-agent", "review.backend cursor")
GROK_ROUTE_TOKENS = ("grok -p",)
# Probe cli -> (binary name for the install note, route tokens gated on it).
PROBES = {
    "codex": ("codex", CODEX_ROUTE_TOKENS),
    "cursor": ("cursor-agent", CURSOR_ROUTE_TOKENS),
    "grok": ("grok", GROK_ROUTE_TOKENS),
}

# Budget: the block is always-loaded context in every future session of the
# target repo (spec R13, ≤ ~45 lines including markers + provenance).
LINE_BUDGET = 45


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_html_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith("<!--") and s.endswith("-->")


# ── Reference implementations of the two documented algorithms ────────────────


def compose_block(template: str, **have: bool) -> str:
    """Reference of the setup workflow.md step-2 probe line transform.

    Start from the template verbatim; for each probe-sentinel line either strip
    the sentinel prefix (probe passed → active route) or wrap the whole route in
    a single inert install-note HTML comment (probe failed → no active route).
    Keyword args are ``codex=``/``cursor=``/``grok=`` (default False when unset).
    """
    out = []
    for line in template.split("\n"):
        m = SENTINEL_RE.match(line)
        if not m:
            out.append(line)
            continue
        cli, text = m.group(1), m.group(2)
        binary = PROBES[cli][0]
        if have.get(cli, False):
            out.append(text)  # strip the `<!-- probe:<cli> --> ` prefix
        else:
            out.append(
                f"<!-- not detected on this machine — install {binary}, "
                f"then uncomment: {text} -->"
            )
    return "\n".join(out)


def remove_marker_block(text: str) -> tuple[str, bool]:
    """Reference of the uninstall.md deterministic damaged-marker algorithm.

    Exactly one start AND exactly one end AND start precedes end → remove the
    block inclusive and return (new_text, True). Any other marker state →
    return (text unchanged, False). Line-based; never parses fenced content.
    """
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines) if l.strip() == START]
    ends = [i for i, l in enumerate(lines) if l.strip() == END]
    if len(starts) == 1 and len(ends) == 1 and starts[0] < ends[0]:
        del lines[starts[0] : ends[0] + 1]
        return "\n".join(lines), True
    return text, False


# ── (a) template shape ────────────────────────────────────────────────────────


class TemplateShape(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(TEMPLATE.is_file(), f"missing template: {TEMPLATE}")
        self.text = _read(TEMPLATE)
        self.lines = self.text.split("\n")

    def test_marker_pair_well_formed(self) -> None:
        starts = [l for l in self.lines if l.strip() == START]
        ends = [l for l in self.lines if l.strip() == END]
        self.assertEqual(len(starts), 1, "exactly one start marker")
        self.assertEqual(len(ends), 1, "exactly one end marker")
        si = next(i for i, l in enumerate(self.lines) if l.strip() == START)
        ei = next(i for i, l in enumerate(self.lines) if l.strip() == END)
        self.assertLess(si, ei, "start must precede end")

    def test_within_line_budget(self) -> None:
        si = next(i for i, l in enumerate(self.lines) if l.strip() == START)
        ei = next(i for i, l in enumerate(self.lines) if l.strip() == END)
        block_lines = ei - si + 1  # marker-inclusive
        self.assertLessEqual(
            block_lines,
            LINE_BUDGET,
            f"scaffold block is {block_lines} lines — over the ≤ ~{LINE_BUDGET} "
            f"always-loaded budget (spec R13)",
        )

    def test_has_provenance_line(self) -> None:
        # Provenance so a reader knows the block is scaffolded + editable.
        self.assertIn("Scaffolded by", self.text)
        self.assertIn("re-run setup to regenerate", self.text)

    def test_every_cli_route_is_sentinel_tagged(self) -> None:
        # No active CLI route may sit OUTSIDE a probe-sentinel line (R10): a line
        # carrying a codex/cursor route token must begin with the matching
        # sentinel. Enforced structurally so composition can be a pure line
        # transform.
        for line in self.lines:
            sentinel = SENTINEL_RE.match(line)
            tagged = sentinel.group(1) if sentinel else None
            for cli, (_binary, tokens) in PROBES.items():
                if any(tok in line for tok in tokens):
                    self.assertEqual(
                        tagged,
                        cli,
                        f"{cli} route not behind a <!-- probe:{cli} --> sentinel:\n  {line}",
                    )

    def test_has_scores_table_and_rules(self) -> None:
        # The opinionated example: a cost/speed/intelligence/taste table + the
        # always-on escalation and graceful-degrade rules (spec R4).
        self.assertIn("| cost | speed | intelligence | taste |", self.text)
        self.assertIn("Graceful degrade", self.text)
        self.assertRegex(self.text, re.compile(r"escalate", re.IGNORECASE))


# ── (b) probe composition ─────────────────────────────────────────────────────


class ProbeComposition(unittest.TestCase):
    def setUp(self) -> None:
        self.template = _read(TEMPLATE)
        self.sentinels = {
            cli: sum(
                1
                for l in self.template.split("\n")
                if l.startswith(f"<!-- probe:{cli} -->")
            )
            for cli in PROBES
        }
        # The template must actually carry every probe family or the state
        # matrix below proves nothing.
        for cli, n in self.sentinels.items():
            self.assertGreater(n, 0, f"template carries no <!-- probe:{cli} --> line")

    def _active_lines(self, composed: str) -> list:
        return [l for l in composed.split("\n") if not _is_html_comment(l)]

    def _matrix(self):
        # Every on/off combination across all three probes.
        for combo in itertools.product((True, False), repeat=len(PROBES)):
            yield dict(zip(PROBES.keys(), combo))

    def test_no_sentinel_survives_composition(self) -> None:
        for have in self._matrix():
            composed = compose_block(self.template, **have)
            with self.subTest(**have):
                for cli in PROBES:
                    self.assertNotIn(f"<!-- probe:{cli} -->", composed)

    def test_failed_probe_leaves_no_active_route(self) -> None:
        for have in self._matrix():
            composed = compose_block(self.template, **have)
            active = self._active_lines(composed)
            with self.subTest(**have):
                for cli, (_binary, tokens) in PROBES.items():
                    cli_active = [l for l in active if any(t in l for t in tokens)]
                    if have[cli]:
                        # Probe passed → routes are live (sentinel stripped).
                        self.assertEqual(len(cli_active), self.sentinels[cli])
                    else:
                        # Probe failed → NO active route for that CLI survives.
                        self.assertEqual(cli_active, [])

    def test_failed_probe_emits_install_notes(self) -> None:
        # A commented-out route names the missing binary + how to re-enable.
        composed = compose_block(self.template)  # all probes default False
        for cli, (binary, _tokens) in PROBES.items():
            self.assertEqual(
                composed.count(f"install {binary}, then uncomment:"),
                self.sentinels[cli],
            )
        self.assertIn("not detected on this machine", composed)

    def test_both_probes_pass_is_fully_active(self) -> None:
        composed = compose_block(
            self.template, codex=True, cursor=True, grok=True
        )
        self.assertNotIn("not detected on this machine", composed)
        # Markers + provenance + scores table are untouched by the transform.
        self.assertIn(START, composed)
        self.assertIn(END, composed)


# ── (c) uninstall marker removal + prose contract ─────────────────────────────

_BLOCK = f"{START}\n## Picking models\n\n| model | cost |\n|-------|------|\n| x | 1 |\n{END}"
_SURROUND_HEAD = "# CLAUDE.md\n\nSome earlier content.\n\n"
_SURROUND_TAIL = "\n\nSome trailing content.\n"


class UninstallRemovalTransform(unittest.TestCase):
    def test_well_formed_removed_inclusive(self) -> None:
        text = _SURROUND_HEAD + _BLOCK + _SURROUND_TAIL
        out, removed = remove_marker_block(text)
        self.assertTrue(removed)
        self.assertNotIn(START, out)
        self.assertNotIn(END, out)
        self.assertNotIn("| model | cost |", out)  # fenced content gone too
        # Surrounding content survives.
        self.assertIn("Some earlier content.", out)
        self.assertIn("Some trailing content.", out)

    def test_zero_starts_untouched(self) -> None:
        text = _SURROUND_HEAD + f"## Picking models\n{END}" + _SURROUND_TAIL
        out, removed = remove_marker_block(text)
        self.assertFalse(removed)
        self.assertEqual(out, text)

    def test_zero_ends_untouched(self) -> None:
        text = _SURROUND_HEAD + f"{START}\n## Picking models\n" + _SURROUND_TAIL
        out, removed = remove_marker_block(text)
        self.assertFalse(removed)
        self.assertEqual(out, text)

    def test_two_starts_untouched(self) -> None:
        text = _SURROUND_HEAD + f"{START}\nfoo\n{START}\nbar\n{END}" + _SURROUND_TAIL
        out, removed = remove_marker_block(text)
        self.assertFalse(removed)
        self.assertEqual(out, text)

    def test_two_ends_untouched(self) -> None:
        text = _SURROUND_HEAD + f"{START}\nfoo\n{END}\nbar\n{END}" + _SURROUND_TAIL
        out, removed = remove_marker_block(text)
        self.assertFalse(removed)
        self.assertEqual(out, text)

    def test_out_of_order_untouched(self) -> None:
        # end precedes start → damaged; leave untouched.
        text = _SURROUND_HEAD + f"{END}\n## Picking models\n{START}" + _SURROUND_TAIL
        out, removed = remove_marker_block(text)
        self.assertFalse(removed)
        self.assertEqual(out, text)

    def test_no_markers_untouched(self) -> None:
        text = _SURROUND_HEAD + "## Picking models\nplain content\n" + _SURROUND_TAIL
        out, removed = remove_marker_block(text)
        self.assertFalse(removed)
        self.assertEqual(out, text)


class UninstallProseContract(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(UNINSTALL.is_file(), f"missing: {UNINSTALL}")
        self.text = _read(UNINSTALL)

    def test_both_marker_strings_present(self) -> None:
        self.assertIn(START, self.text)
        self.assertIn(END, self.text)

    def test_exactly_one_and_ordered_rule_stated(self) -> None:
        low = self.text.lower()
        self.assertIn("exactly one", low)
        # ordering: start precedes end.
        self.assertRegex(
            self.text,
            re.compile(r"start.{0,40}precede", re.IGNORECASE | re.DOTALL),
        )

    def test_damaged_report_and_untouched_stated(self) -> None:
        low = self.text.lower()
        self.assertIn("untouched", low)
        # any-other-state → report, don't guess.
        self.assertRegex(self.text, re.compile(r"any other state", re.IGNORECASE))

    def test_report_line_extended(self) -> None:
        # The "Cleaned up" report now names the model-routing block.
        self.assertRegex(
            self.text,
            re.compile(r"Cleaned up:.*model-routing", re.IGNORECASE | re.DOTALL),
        )


# ── (d) setup workflow prose contracts (canonical + mirror) ──────────────────


class WorkflowProseContract(unittest.TestCase):
    """The ceremony prose that the deterministic transforms above depend on —
    locked on the canonical file AND the Codex mirror (sync-codex.sh must not
    drop the frozen strings or the ordering)."""

    def _assert_contract(self, path: pathlib.Path) -> None:
        self.assertTrue(path.is_file(), f"missing: {path}")
        text = _read(path)
        # Headless / non-interactive setup skips the question silently.
        self.assertIn("skipped SILENTLY", text, path)
        self.assertIn("ROUTING_ASK", text, path)
        # Frozen option set — as-built casing.
        self.assertIn("`Scaffold` / `Scaffold + enable codex delegation` / `Skip`", text, path)
        self.assertIn("Scaffold + enable codex delegation", text, path)
        # Never pre-set the consent gate (R9).
        self.assertIn("work.delegateConsent", text, path)
        self.assertRegex(
            text,
            re.compile(r"NEVER\b.{0,60}work\.delegateConsent", re.DOTALL),
            path,
        )
        # Scaffold processing runs AFTER the Docs block (markdown may bold
        # "after": `**after** the Docs block above`).
        self.assertRegex(
            text,
            re.compile(r"after\*{0,2} the Docs block above", re.IGNORECASE),
            path,
        )

    def test_canonical_workflow(self) -> None:
        self._assert_contract(CANONICAL_WORKFLOW)

    def test_mirror_workflow(self) -> None:
        self._assert_contract(MIRROR_WORKFLOW)


if __name__ == "__main__":
    unittest.main()
