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
