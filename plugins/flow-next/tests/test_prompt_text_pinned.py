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


def _sha(text: str) -> str:
    # Normalise line endings so a Windows checkout does not fail the pin.
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


# Embedded prompt constants in flowctl.py (str-valued).
PROMPT_HASHES = {
    "CLASSIFICATION_RUBRIC_BLOCK":
        "fbde8f499ba3d82b50901b12a984912490b66c6e69f1b74c38edf80c28567a06",
    "COMPLETION_REVIEW_PROMPT_FALLBACK":
        "e539a47bb29fb078ea7dec52c8c227f8dd9f083347a634933945c3a1e5a9345f",
    "CONFIDENCE_RUBRIC_BLOCK":
        "b8cc9e9594a3fed35498040e222bc9000333f4407f48374464115a69c231ae15",
    "IMPL_REVIEW_PROMPT_FALLBACK":
        "ef9733a228a205528a558b6896efe38f4fa44bc0b1b900b34db3abbb460554a9",
    "PLAN_QUALITY_BLOCK":
        "0cfb49bfadf0be45e5c8036950d34698b5ae3bbccf24a90564983e13d0a1192f",
    "PLAN_REVIEW_PROMPT_FALLBACK":
        "250d7c46a2ae415bb98469ac90bce3573fddab4ee0a7fe9c092800d3009a9c69",
    "PROTECTED_ARTIFACTS_BLOCK":
        "e9b68af0cf36f6b2cb1b70c9bcc5ff67ccb86295f369d02ffcec4f25fd6f2d5e",
    "REVIEW_JSON_TALLY_BLOCK":
        "01b6b78ce0515285db7d7c20ae6ad1a04b6619f4fa429c1a4189375392cedf3c",
    "R_ID_COVERAGE_BLOCK":
        "51280cbdbe6fe1f570d221111b245e207aa6cdb9f07d0952b24f7029fa34ab80",
    "SMELL_BASELINE_BLOCK":
        "abf0284deeb387691bfa91f139e63d80c546f4c2b05403f821597465dcafdd5e",
    "SPEC_SKELETON_TEMPLATE":
        "181c5cd5cba913346dc8c1800871dd42d139321319f86b80a67248ca15063ead",
    "STANDALONE_REVIEW_PROMPT_FALLBACK":
        "1898a9b1c78a96c40752442b327f29df1a0ccb6009dafa871f6b5b1da5ce7280",
    # Condensation of validate-pass.md, NOT a copy of it (#118).
    "VALIDATOR_TEMPLATE_FALLBACK":
        "558ab25ab09ade0e315d924e72615c76f4ac8c9348cf60cfbfd761896664a36c",
    # Injected INTO the cursor reviewer prompt when the diff or body is too
    # large for argv. Reviewer-facing instructions, so: prompt text.
    "_CURSOR_DIFF_TRUNC_MARKER":
        "a8a988166e6c67d2813750be1fdd0c88bcae5acb6082e68ee44082356bcf9b26",
    "_CURSOR_DIFF_OMITTED_MARKER":
        "eaca7619b45629e1db6dac60bb1042718baff9c7ea85f317116848e62def44e7",
    "_CURSOR_PROMPT_TRUNC_MARKER":
        "623c116989917678074c110eb51c5e37bfe966bdcf09ad222b7801202ca5f740",
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
    "plugins/flow-next/skills/flow-next-impl-review/validate-pass.md":
        "eb39e0d69df44a5696d32844baf920d6cfa0440d9f918db2628b79c1d03ecb27",
    "plugins/flow-next/skills/flow-next-impl-review/deep-passes.md":
        "41f7aa18ca28c48ec6ab27fac0c3fd18224232a76e1fbc6cef631435370dfc58",
    "plugins/flow-next/skills/flow-next-impl-review/references/impl-review-prompt.md":
        "ef9733a228a205528a558b6896efe38f4fa44bc0b1b900b34db3abbb460554a9",
    "plugins/flow-next/skills/flow-next-impl-review/references/standalone-review-prompt.md":
        "1898a9b1c78a96c40752442b327f29df1a0ccb6009dafa871f6b5b1da5ce7280",
    "plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md":
        "250d7c46a2ae415bb98469ac90bce3573fddab4ee0a7fe9c092800d3009a9c69",
    "plugins/flow-next/skills/flow-next-spec-completion-review/references/completion-review-prompt.md":
        "e539a47bb29fb078ea7dec52c8c227f8dd9f083347a634933945c3a1e5a9345f",
    # Rendered by ralph.sh each autonomous loop - production prompts, and the
    # ones an unattended run depends on most.
    "plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_plan.md":
        "04683af76d3bf20bb5bb722ec1bc7aca0f3ba0841afcedc1cec2aa4061f7d72f",
    "plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_work.md":
        "ee541d3a1b17b45e732abe45353d629af50460804fe92245c2e4f0a9c70e0f3c",
    "plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_completion.md":
        "21731b3b8ead8c761061cddfbf1739ca1bfcdf2223692d82196d37ec89af2371",
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
