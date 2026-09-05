"""Tripwire: no refactor may change prompt text as a side effect.

Prompts are the product. A lint rule, an autofix, a rename sweep, or a
well-meaning "keep these in sync" cleanup must never alter a single byte of
what a reviewer model receives - and if one does, that has to surface as a
loud failure rather than as a line buried in a 40-file diff.

This pins every embedded prompt constant in ``flowctl.py`` plus every on-disk
prompt template by SHA-256. It is deliberately dumb: it asserts nothing about
what the prompts SAY, only that nobody changed them without meaning to.

Written after a ruff-adoption pass (#244/#245) rewrote two embedded fallbacks
while presenting itself as a code-quality change. The lint work was fine; the
prompt edits rode along unnoticed because nothing was watching.

**Changing a prompt on purpose is expected and fine.** When you do, update the
hash here in the SAME commit, and say in the commit message what changed and
why. A hash update with no prompt rationale in the message is the smell this
file exists to catch.

Note the intentional asymmetry: IMPL/STANDALONE/PLAN/COMPLETION fallbacks share
a hash with their template (byte-identical by the fn-112.3 rule), while
VALIDATOR_TEMPLATE_FALLBACK and DEEP_PASSES_FALLBACK do NOT - those are
hand-written condensations authored that way in #118. Both facts are pinned, so
neither can be "corrected" into the other by accident.

Run:
    python3 -m unittest plugins.flow-next.tests.test_prompt_text_pinned -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parent.parent.parent.parent


def _load_flowctl() -> Any:
    flowctl_path = HERE.parent.parent / "scripts" / "flowctl.py"
    if not flowctl_path.is_file():
        raise RuntimeError(f"flowctl.py not found at {flowctl_path}")
    spec = importlib.util.spec_from_file_location("flowctl_prompt_pin", flowctl_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


flowctl = _load_flowctl()

_FIX_HINT = (
    "If you changed this prompt ON PURPOSE, update the hash in this file in the "
    "same commit and explain the wording change in the commit message. If you "
    "did NOT mean to change it, revert - a lint, format, or refactor pass must "
    "never rewrite prompt text."
)


DELETED_FITTER_MARKERS = (
    # fn-169 R4. Each was the visible half of a content fitter; a
    # reappearance is a fitter reappearing, which is the regression this
    # spec exists to prevent.
    "_CURSOR_DIFF_TRUNC_MARKER",
    "_CURSOR_DIFF_OMITTED_MARKER",
    "_CURSOR_PROMPT_TRUNC_MARKER",
)


def _sha(text: str) -> str:
    # Normalise line endings so a Windows checkout does not fail the pin.
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


# Embedded prompt constants in flowctl.py (str-valued).
PROMPT_HASHES = {
    # fn-215 R1: fan-out axis lenses — one line added per parallel draw.
    "CONTRACTS_AXIS_PROMPT_LINE":
        "892dc66aad2f1e3f7ac1ff71c77a442e9b17cb7c1d5a640536642ea12bda8e42",
    "CORRECTNESS_AXIS_PROMPT_LINE":
        "48e2c1a2cdfb44c461d8cffcfc4152ea0309f2da5efe12f08fe35152a9195f8b",
    "CLASSIFICATION_RUBRIC_BLOCK":
        "fbde8f499ba3d82b50901b12a984912490b66c6e69f1b74c38edf80c28567a06",
    "COMPLETION_REVIEW_PROMPT_FALLBACK":
        "a4b3105a7a8a3a56ba21d035d89dfc5cc62a496f4e1317b00fa89b01e197aafc",
    "CONFIDENCE_RUBRIC_BLOCK":
        "b8cc9e9594a3fed35498040e222bc9000333f4407f48374464115a69c231ae15",
    # fn-210.1: comment-as-alibi finding class (workaround-justifying comments
    # flag the underlying code; keep-list copied from the worker authoring rule).
    "INTEGRATION_AXIS_PROMPT_LINE":
        "0569edc1e9220bb2a29fb431f589baa2df2f04cd8c059f5eaade7dc5f54170cf",
    "IMPL_REVIEW_PROMPT_FALLBACK":
        "461c1e1fbe62eb8da5a26bef9542d956a18347d75a79cf00552c9540e126da2d",
    "PLAN_QUALITY_BLOCK":
        "0cfb49bfadf0be45e5c8036950d34698b5ae3bbccf24a90564983e13d0a1192f",
    "PLAN_REVIEW_PROMPT_FALLBACK":
        "dfef7509111bbaac438d85149a84ee3fc85bf407b3e499605d554bad9a8664fb",
    "PROTECTED_ARTIFACTS_BLOCK":
        "e9b68af0cf36f6b2cb1b70c9bcc5ff67ccb86295f369d02ffcec4f25fd6f2d5e",
    "REVIEW_JSON_TALLY_BLOCK":
        "01b6b78ce0515285db7d7c20ae6ad1a04b6619f4fa429c1a4189375392cedf3c",
    "R_ID_COVERAGE_BLOCK":
        "51280cbdbe6fe1f570d221111b245e207aa6cdb9f07d0952b24f7029fa34ab80",
    # fn-208.2: baseline gains the Middle Man / pass-through smell the
    # quality-auditor already carries but impl-review was blind to.
    "SMELL_BASELINE_BLOCK":
        "0fcf594a970ca41958003e4a41f99f0b8d590704d9c1ef32e47cd80722c68db9",
    # fn-220: SPEC_SKELETON_TEMPLATE deleted; the scaffold is templates/spec.md, rendered by spec_skeleton_text().
    # fn-210.1: same comment-as-alibi finding class as impl-review.
    "STANDALONE_REVIEW_PROMPT_FALLBACK":
        "beedb8d647f78d782b3e58ebdeb8cbace8ae7dcb5b9e432359a6627a9a255963",
    # Condensation of validate-pass.md, NOT a copy of it (#118).
    "VALIDATOR_TEMPLATE_FALLBACK":
        "558ab25ab09ade0e315d924e72615c76f4ac8c9348cf60cfbfd761896664a36c",
    # fn-169 R4 DELETED the three cursor shortening markers
    # (_CURSOR_DIFF_TRUNC_MARKER, _CURSOR_DIFF_OMITTED_MARKER,
    # _CURSOR_PROMPT_TRUNC_MARKER). They were reviewer-facing apologies for
    # evidence the prompt had shortened - "read the changed files from disk
    # for full context" - printed because the payload did not fit argv. The
    # prompt carries no payload now, so there is nothing to shorten and no
    # apology to make. Their absence is ASSERTED below rather than merely
    # unpinned: a marker reappearing means a content fitter came back with it.
    # Completion-review criteria injection wrapper (fn-137.2). Rendered only
    # when .flow/criteria.md exists; empty otherwise.
    "_GLOBAL_CRITERIA_BLOCK_TEMPLATE":
        "58eece8cecd3cfb56f6a3a2105bf1c9287258a25950d37a3e541f1cf8cdaabdd",
    # fn-181 R1: printed on plain `show`/`list` when the runtime state store
    # is absent. Agents read it and decide whether to trust the status they
    # were just given, so its wording is deliberate-change territory.
    "STATUS_SOURCE_ABSENT_NOTE":
        "0f6697e1ed3d099666d5be48252bacfb5172871dd4e2e4bfc1d2e99268e6ac24",
    # fn-192 R3 / #346: printed on stderr when done/block dirty a tracked
    # task file. Agents read it and decide whether to stage the receipt, so
    # its wording is deliberate-change territory.
    "TRACKED_WRITE_DIRTY_NOTE":
        "eca66532a7ea6812b5c23d8f1af1312a6d099dd39ad908d4117a5b4231321d38",
    # Lands in the receipt `note` field and on stdout; agents read receipts.
    "HOST_JUDGES_NOTE":
        "47b75b60635754b4267077dc782a7b026af6dce3669619c4ffca6ec920c5d878",
}

# Module-level strings the discovery heuristic matches that are NOT prompt text.
# Every entry needs a reason - this list is how a non-prompt opts out, and it is
# the only way to keep the heuristic wide without it crying wolf.
NOT_PROMPT_TEXT = {
    # Relative filesystem paths, not prose. If one changes, the template simply
    # fails to load and the loader/extraction tests catch it.
    "IMPL_REVIEW_PROMPT_TEMPLATE_REL",
    "STANDALONE_REVIEW_PROMPT_TEMPLATE_REL",
    "PLAN_REVIEW_PROMPT_TEMPLATE_REL",
    "COMPLETION_REVIEW_PROMPT_TEMPLATE_REL",
    "VALIDATOR_TEMPLATE_REL",
    "DEEP_PASSES_TEMPLATE_REL",
    # fn-159.3: a machine terminal marker (one string, two emit sites), not
    # prompt text. No agent is instructed by it; hosts and ralph.sh match on
    # it, and those matchers are covered by their own tests.
    "NEEDS_HUMAN_ESCALATION_MARKER",
}

# Condensations of the deep-passes.md blocks, NOT copies of them (#118).
DEEP_PASS_HASHES = {
    "adversarial":
        "7df43e62445aa27be54ae9d827389d5897474f3ca7d622bf14e8fd28c215218c",
    "performance":
        "bcad7eaaa88816949ddba23f72be41361aba3a08c5a045579bfc7d7381c942df",
    "security":
        "0903c970511257b10bab21a69166fd204536f709e3f0da8479fc5fbabc0606d5",
}

# On-disk prompt templates. These are what real installs actually read.
TEMPLATE_HASHES = {
    # fn-220: the spec scaffold `flowctl spec create` / `spec skeleton` render.
    # This pin is the R22 byte-for-byte baseline the deleted
    # SPEC_SKELETON_TEMPLATE constant used to carry: a scaffold edit is a
    # deliberate bump with a rationale in the commit message, never silent.
    "plugins/flow-next/templates/spec.md":
        "5032758a08e0d8180d062f3e4fe2c4a9309301cb5f932a9eb6549aae59a536f5",
    "plugins/flow-next/skills/flow-next-impl-review/validate-pass.md":
        "eb39e0d69df44a5696d32844baf920d6cfa0440d9f918db2628b79c1d03ecb27",
    "plugins/flow-next/skills/flow-next-impl-review/deep-passes.md":
        "41f7aa18ca28c48ec6ab27fac0c3fd18224232a76e1fbc6cef631435370dfc58",
    "plugins/flow-next/skills/flow-next-impl-review/references/impl-review-prompt.md":
        "461c1e1fbe62eb8da5a26bef9542d956a18347d75a79cf00552c9540e126da2d",
    "plugins/flow-next/skills/flow-next-impl-review/references/standalone-review-prompt.md":
        "beedb8d647f78d782b3e58ebdeb8cbace8ae7dcb5b9e432359a6627a9a255963",
    "plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md":
        "dfef7509111bbaac438d85149a84ee3fc85bf407b3e499605d554bad9a8664fb",
    "plugins/flow-next/skills/flow-next-spec-completion-review/references/completion-review-prompt.md":
        "a4b3105a7a8a3a56ba21d035d89dfc5cc62a496f4e1317b00fa89b01e197aafc",
    # Rendered by ralph.sh each autonomous loop - production prompts, and the
    # ones an unattended run depends on most. fn-159.6 clarifies that a review
    # call's tag set differs from the step's return set: NEEDS_WORK loops
    # in-step, while only terminal tags return control to Ralph.
    "plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_plan.md":
        "1204f37761d6ea6820b909f0b4e3fa95bee8b83e21c8e8c254b0fcdc5ff3c57a",
    "plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_work.md":
        "248442c76588028224774c67f7f0ebb466182e2934e6443ec7d30ece387f2a3f",
    "plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_completion.md":
        "f99bd8e419557c66c6346c581a49a4f8a741bada251988a4a79d37e75cd35e0c",
}


class TestEmbeddedPromptsPinned(unittest.TestCase):
    def test_prompt_constants_unchanged(self) -> None:
        for name, expected in PROMPT_HASHES.items():
            with self.subTest(constant=name):
                value = getattr(flowctl, name, None)
                self.assertIsInstance(
                    value, str, f"{name} is missing or no longer a string. {_FIX_HINT}"
                )
                self.assertEqual(
                    _sha(value), expected, f"{name} prompt text changed. {_FIX_HINT}"
                )

    def test_every_deep_pass_fallback_is_pinned(self) -> None:
        """A 4th deep pass must be pinned too, not just structurally present.

        The value loop below only visits keys already in DEEP_PASS_HASHES, so a
        new pass added to both DEEP_PASSES and DEEP_PASSES_FALLBACK would sail
        past unpinned and its later wording changes would go unnoticed (#245
        review). Same rot as the constant-discovery hole, one container down.
        """
        self.assertEqual(
            set(DEEP_PASS_HASHES), set(flowctl.DEEP_PASSES_FALLBACK),
            "DEEP_PASS_HASHES and DEEP_PASSES_FALLBACK disagree - pin every "
            "deep-pass fallback, or drop the hash for a removed one.",
        )

    def test_deep_pass_fallbacks_unchanged(self) -> None:
        for name, expected in DEEP_PASS_HASHES.items():
            with self.subTest(deep_pass=name):
                self.assertEqual(
                    _sha(flowctl.DEEP_PASSES_FALLBACK[name]), expected,
                    f"DEEP_PASSES_FALLBACK[{name!r}] prompt text changed. {_FIX_HINT}",
                )

    def test_no_unpinned_prompt_constant_appears(self) -> None:
        """A new prompt constant must be pinned too, or this file rots.

        The first version of this check matched only names ending in
        ``_FALLBACK`` / ``_BLOCK`` / ``_TEMPLATE``, and review caught that it
        therefore ignored ``_CURSOR_*_MARKER`` - prompt text injected into the
        cursor reviewer prompt - while the module docstring claimed full
        coverage. A naming convention is not a guarantee.

        So the heuristic is deliberately WIDE and anything it catches must be
        either pinned or listed in NOT_PROMPT_TEXT with a reason. Adding a
        prompt-bearing constant under any new naming style now fails here
        rather than sliding in unwatched.
        """
        keywords = (
            "PROMPT", "MARKER", "TEMPLATE", "BLOCK", "RUBRIC", "INSTRUCTION",
            "GUIDANCE", "NOTE", "HINT", "BANNER", "PREAMBLE", "FALLBACK",
        )
        found = {
            n for n in dir(flowctl)
            if re.match(r"^_?[A-Z][A-Z0-9_]*$", n)
            and isinstance(getattr(flowctl, n), str)
            and len(getattr(flowctl, n)) >= 25
            and any(k in n for k in keywords)
        }
        unaccounted = found - set(PROMPT_HASHES) - NOT_PROMPT_TEXT
        self.assertEqual(
            unaccounted, set(),
            f"prompt-bearing constant(s) {sorted(unaccounted)} are neither "
            f"pinned in PROMPT_HASHES nor declared in NOT_PROMPT_TEXT. Pin it "
            f"if agents read it; declare it (with a reason) if they do not.",
        )


class TestOnDiskTemplatesPinned(unittest.TestCase):
    def test_template_files_unchanged(self) -> None:
        for rel, expected in TEMPLATE_HASHES.items():
            with self.subTest(template=rel):
                path = REPO_ROOT / rel
                self.assertTrue(path.is_file(), f"prompt template missing: {rel}")
                self.assertEqual(
                    _sha(path.read_text(encoding="utf-8")), expected,
                    f"{rel} prompt text changed. {_FIX_HINT}",
                )


if __name__ == "__main__":
    unittest.main()


class TestFitterMarkersStayDeleted(unittest.TestCase):
    """fn-169 R4 - no prompt may tell a reviewer its evidence was shortened."""

    def test_no_fitter_marker_returns(self) -> None:
        for name in DELETED_FITTER_MARKERS:
            with self.subTest(constant=name):
                self.assertFalse(
                    hasattr(flowctl, name),
                    f"{name} is back - a content fitter returned with it. "
                    "The review prompt carries identities, not payloads; "
                    "nothing should need to shorten the evidence a verdict "
                    "rests on.",
                )
