"""fn-169 R4 — the advertised eval harnesses still build a prompt.

impl-review r1 (P1, valid): the identity migration changed
``build_review_prompt``'s signature, and five harness entrypoints under
``optimization/`` still called it with embedded bodies and removed keywords. They
are documented, runnable tooling; a ``TypeError`` at import is a broken build
surface even when no eval is scheduled.

These harnesses have no repository for a reviewer to read from — the same position
as ``--review=export`` — so each now owns its own payload embedding via a local
``_embed_payload`` helper and calls the identity builder for the wording. This
suite asserts that arrangement holds by EXECUTING each entrypoint, not by
grepping for a call shape.

Run:
    python3 -m unittest test_eval_harness_prompt_api -v
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

# (module path, attribute to call, zero-arg callable?) — the entrypoints the
# harness READMEs and prior spec Quick commands point at.
ENTRYPOINTS = (
    ("optimization/review-prompt/reveval.py", "_base_prompt", ()),
    ("optimization/review-prompt/reveval_plan.py", "_plan_prompt", ()),
    ("optimization/reached-path/plan_review_real_eval.py", "build_prompt", ("SPEC BODY",)),
)


def _load(rel: str) -> Any:
    path = REPO_ROOT / rel
    if not path.is_file():
        raise unittest.SkipTest(f"harness missing: {rel}")
    # These scripts sit beside their own data files and siblings they import.
    sys.path.insert(0, str(path.parent))
    sys.path.insert(0, str(REPO_ROOT / "plugins/flow-next/scripts"))
    try:
        spec = importlib.util.spec_from_file_location(f"_harness_{path.stem}", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(REPO_ROOT / "plugins/flow-next/scripts"))
        sys.path.remove(str(path.parent))


class TestEvalHarnessesBuildPrompts(unittest.TestCase):
    def test_each_entrypoint_renders_a_prompt_with_its_payload(self):
        for rel, attr, args in ENTRYPOINTS:
            with self.subTest(harness=rel, entrypoint=attr):
                module = _load(rel)
                fn = getattr(module, attr, None)
                self.assertIsNotNone(fn, f"{rel} no longer exposes {attr}()")
                prompt = fn(*args)
                self.assertIsInstance(prompt, str)
                self.assertIn("<review_instructions>", prompt)
                # The harness embeds because it has no repo; that is the point.
                self.assertIn("<spec>", prompt)

    def test_harnesses_embed_locally_and_production_does_not(self):
        """The carve-out must stay confined to the harnesses.

        `_embed_payload` living in the harness — never in flowctl — is what keeps
        "the reviewer fetches it" true for every production path while these
        scripts stay runnable.
        """
        flowctl_src = (
            REPO_ROOT / "plugins/flow-next/scripts/flowctl.py"
        ).read_text(encoding="utf-8")
        for leaked in ("embed_payload", "eval_prompt_payload"):
            self.assertNotIn(
                leaked, flowctl_src,
                "the eval harness's embedding helper leaked into production — a "
                "production path using it would be re-adding embedding",
            )
        # Exactly one definition, under optimization/, imported by the harnesses.
        helper = REPO_ROOT / "optimization/eval_prompt_payload.py"
        self.assertTrue(helper.is_file(), "shared eval helper is missing")
        self.assertIn("def embed_payload(", helper.read_text(encoding="utf-8"))
        for rel, _attr, _args in ENTRYPOINTS:
            src = (REPO_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(harness=rel):
                self.assertIn("from eval_prompt_payload import", src)
                self.assertNotIn(
                    "def _embed_payload(", src,
                    "a local copy of the helper came back — impl-review r2 P3 "
                    "flagged exactly this duplication",
                )


if __name__ == "__main__":
    unittest.main()


class TestEvalPayloadPositionMatchesTheOldBuilder(unittest.TestCase):
    """fn-169 (impl-review r3, P2) — position is part of the prompt.

    The harnesses exist to compare WORDING across arms. Appending the payload
    after `<review_instructions>` would move the experimental spec/code to the end
    of the prompt and change recency at the same time as the variable under test,
    so deltas against earlier eval results would no longer be attributable. The
    pre-fn-169 builder put the payload BEFORE the rubric; so does the helper.
    """

    def _helper(self):
        import importlib.util as iu
        path = REPO_ROOT / "optimization/eval_prompt_payload.py"
        spec = iu.spec_from_file_location("_eval_payload_under_test", path)
        module = iu.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_payload_precedes_the_review_instructions_block(self):
        embed = self._helper().embed_payload
        prompt = "HEAD\n\n<review_instructions>\nRUBRIC\n</review_instructions>"
        out = embed(prompt, spec="SPEC_BODY", diff_content="DIFF_BODY")
        self.assertLess(
            out.index("DIFF_BODY"), out.index("<review_instructions>"),
            "payload landed after the rubric — recency changed alongside the "
            "variable under test",
        )
        self.assertLess(out.index("SPEC_BODY"), out.index("<review_instructions>"))
        # The old builder's block order: summary, diff, spec, tasks.
        out2 = embed(
            prompt, spec="SPEC_TOKEN", diff_summary="SUMMARY_TOKEN",
            diff_content="DIFF_TOKEN", task_specs="TASKS_TOKEN",
        )
        self.assertLess(out2.index("SUMMARY_TOKEN"), out2.index("DIFF_TOKEN"))
        self.assertLess(out2.index("DIFF_TOKEN"), out2.index("SPEC_TOKEN"))
        self.assertLess(out2.index("SPEC_TOKEN"), out2.index("TASKS_TOKEN"))
        self.assertLess(
            out2.index("TASKS_TOKEN"), out2.index("<review_instructions>")
        )

    def test_a_prompt_without_the_tag_appends(self):
        """Standalone-shaped prompts keep the rubric at the top, so append is fine."""
        embed = self._helper().embed_payload
        out = embed("RUBRIC AT TOP", diff_content="D")
        self.assertTrue(out.startswith("RUBRIC AT TOP"))
        self.assertIn("D", out)

    def test_no_payload_is_a_no_op(self):
        embed = self._helper().embed_payload
        self.assertEqual(embed("PROMPT"), "PROMPT")


class TestHarnessPromptIsInternallyTruthful(unittest.TestCase):
    """fn-169 (impl-review r4, P2) — a prompt must not lie about its own inputs.

    The identity rubric declares `<diff_range>` and `<changed_files>` and describes
    `<spec>` as a path to read. In an offline harness none of those hold, so the
    embedded-payload runs must correct the contract explicitly rather than shipping
    a rubric that describes inputs the reviewer never received.
    """

    def _helper(self):
        import importlib.util as iu
        path = REPO_ROOT / "optimization/eval_prompt_payload.py"
        spec = iu.spec_from_file_location("_eval_payload_truthful", path)
        module = iu.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_embedded_runs_override_the_identity_contract(self):
        embed = self._helper().embed_payload
        out = embed(
            "HEAD\n\n<review_instructions>\nContext Gathering\n</review_instructions>",
            spec="SPEC TEXT", diff_content="DIFF TEXT",
        )
        self.assertIn("HARNESS INPUT OVERRIDE", out)
        # It must name the specific slots the rubric wrongly promises.
        for slot in ("<diff_range>", "<changed_files>"):
            self.assertIn(slot, out)
        self.assertIn("does not apply", out)
        # And it must precede the rubric it is correcting.
        self.assertLess(
            out.index("HARNESS INPUT OVERRIDE"), out.index("<review_instructions>")
        )

    def test_the_override_never_reaches_a_production_prompt(self):
        for rel in (
            "plugins/flow-next/scripts/flowctl.py",
            "plugins/flow-next/skills/flow-next-impl-review/references/impl-review-prompt.md",
        ):
            src = (REPO_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(path=rel):
                self.assertNotIn("HARNESS INPUT OVERRIDE", src)
