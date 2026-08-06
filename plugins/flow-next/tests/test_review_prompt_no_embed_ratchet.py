"""fn-169 R6 — the executable ratchet fn-74 omitted.

fn-74 made this exact decision, validated it with an eval, deleted the embedding
code, and wrote it in a CHANGELOG. fn-90 re-added the diff body; fn-159 re-added
it with a fitter. Each had a good local reason, and nothing failed when they did.

A CHANGELOG entry is not a constraint. This is: every non-`export` review prompt
must carry identities only. The failure message NAMES the offending tag so a
future regression explains itself instead of just going red.

Two deliberate exceptions, asserted here so they read as decisions rather than
oversights:

* `host` — no session by design ("every re-review is a fresh subagent"), so it
  always injects prior findings. It is not a flowctl prompt path at all; the
  host workflow owns its own dispatch.
* `export` / the eval harnesses — no repository for the reviewer to read from, so
  the payload is the only channel. `export` is a skill route through
  `flow-next-export-context`; the harnesses embed via
  `optimization/eval_prompt_payload.py`, never via flowctl.

Run:
    python3 -m unittest test_review_prompt_no_embed_ratchet -v
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _load_flowctl() -> Any:
    path = Path(__file__).resolve().parent.parent / "scripts" / "flowctl.py"
    spec = importlib.util.spec_from_file_location("flowctl_no_embed_ratchet", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


flowctl = _load_flowctl()

SPEC_PATH = ".flow/specs/fn-ratchet.md"
TASK_PATH = ".flow/tasks/fn-ratchet.1.md"
RANGE = "1111111..2222222"
SCOPE = "12\t3\tsrc/alpha.py\n4\t0\tsrc/beta.py"

# Bodies a regression would embed. Each is distinctive enough that finding it in a
# prompt is unambiguous, and long enough that a fitter would want to trim it.
DIFF_BODY = (
    "diff --git a/src/alpha.py b/src/alpha.py\n"
    "@@ -1,3 +1,4 @@\n+EMBEDDED_DIFF_BODY_SENTINEL = 1\n" * 40
)
SPEC_BODY = "# Spec\n\nEMBEDDED_SPEC_BODY_SENTINEL\n" * 40
PRIOR_ITEM_TITLE = "EMBEDDED_PRIOR_ITEM_SENTINEL"

# Payload tags no production prompt may frame. Named in the failure message.
FORBIDDEN_TAGS = ("<diff_content>", "<embedded_files>", "<requested_file_contents>")


def _prior_container() -> dict:
    return {
        "schemaVersion": 1,
        "sourceReceiptId": "receipt-1",
        "reviewKind": "implementation",
        "backend": "codex",
        "round": 1,
        "headSha": "a" * 40,
        "items": [
            {
                "id": flowctl._review_finding_lineage_id("receipt-1", 1),
                "ordinal": 1,
                "severity": "P1",
                "confidence": 100,
                "classification": "introduced",
                "status": "open",
                "title": PRIOR_ITEM_TITLE,
                "body": "Body.",
                "rIds": [],
                "firstSeenReceiptId": "receipt-1",
                "lastSeenReceiptId": "receipt-1",
            }
        ],
    }


class TestNoEmbedRatchet(unittest.TestCase):
    def _production_prompts(self) -> dict[str, str]:
        """Every prompt flowctl builds for a repo-capable backend."""
        return {
            "impl": flowctl.build_review_prompt(
                "impl", context_hints="hints", review_scope=SCOPE,
                diff_range=RANGE, spec_path=SPEC_PATH,
            ),
            "plan": flowctl.build_review_prompt(
                "plan", context_hints="hints", spec_path=SPEC_PATH,
                task_spec_paths=(TASK_PATH,),
            ),
            "standalone": flowctl.build_standalone_review_prompt(
                "main", "focus areas", SCOPE, RANGE,
            ),
            "completion": flowctl.build_completion_review_prompt(
                SPEC_PATH, (TASK_PATH,), SCOPE, RANGE,
            ),
        }

    def test_no_production_prompt_frames_a_payload_tag(self):
        for name, prompt in self._production_prompts().items():
            for tag in FORBIDDEN_TAGS:
                with self.subTest(prompt=name, tag=tag):
                    self.assertNotIn(
                        tag, prompt,
                        f"{name} review prompt frames {tag}. Review prompts carry "
                        "IDENTITIES — a base..head range and resolvable paths. The "
                        "reviewer has a shell and a checkout; it fetches. See "
                        "STRATEGY.md 'identities, not payloads' and the fn-74 -> "
                        "fn-90 -> fn-159 re-accretion history.",
                    )

    def test_no_production_prompt_carries_a_body(self):
        """Size, not just framing: an unframed body is the same regression."""
        for name, prompt in self._production_prompts().items():
            with self.subTest(prompt=name):
                for sentinel in (
                    "EMBEDDED_DIFF_BODY_SENTINEL",
                    "EMBEDDED_SPEC_BODY_SENTINEL",
                ):
                    self.assertNotIn(sentinel, prompt)
                # The identity IS present — this is not vacuously passing.
                # `standalone` is a branch review with no task context, so it
                # names a range and a scope map but no spec.
                identity = RANGE if name == "standalone" else SPEC_PATH
                self.assertIn(
                    identity, prompt,
                    f"{name} carries no identity for the reviewer to resolve",
                )

    def test_prompt_size_does_not_track_the_change_size(self):
        """The property a fitter would be needed for cannot arise.

        Rendering with a tiny scope and a large one differs only by the numstat
        block itself; no prompt grows with the diff, the spec, or the task count,
        so nothing can outgrow a transport and ask for a budget constant.
        """
        small = flowctl.build_review_prompt(
            "impl", review_scope="1\t0\ta.py", diff_range=RANGE,
            spec_path=SPEC_PATH,
        )
        wide = flowctl.build_review_prompt(
            "impl",
            review_scope="\n".join(f"9\t9\tsrc/f{n}.py" for n in range(400)),
            diff_range=RANGE, spec_path=SPEC_PATH,
        )
        # The ONLY growth is the scope map the reviewer resolves paths from.
        overhead = len(wide) - len(small)
        self.assertLess(
            overhead, 12000,
            "prompt grew by more than its scope map — something else is riding "
            "along with the change size",
        )
        self.assertLess(len(small), flowctl.CURSOR_ARGV_TRANSPORT_MAX)

    def test_ratchet_renders_priors_only_when_not_resumed(self):
        """R2's split, asserted at the ratchet: resumed carries no prior items.

        A resumed reviewer holds its own findings; re-rendering them is the
        payload class again. The injected fallback DOES carry them, because a
        reviewer cannot fetch its own prior verdict from the tree — that is the
        one payload with no identity, and it is why the renderer survives.
        """
        items = _prior_container()["items"]
        resumed = flowctl.build_convergence_ratchet_block(
            "prose", prior_items=items, review_type="implementation", resumed=True,
        )
        injected = flowctl.build_convergence_ratchet_block(
            "prose", prior_items=items, review_type="implementation",
        )
        self.assertNotIn(PRIOR_ITEM_TITLE, resumed)
        self.assertNotIn("<prior_findings>", resumed)
        self.assertIn(PRIOR_ITEM_TITLE, injected)
        self.assertIn("<prior_findings>", injected)

    def test_documented_exceptions_are_real_and_confined(self):
        """host and export must be deliberate, not accidental gaps."""
        flowctl._wire_backend_review_hooks()
        # host is a selection sentinel: it has no flowctl dispatch at all, which
        # is what makes "host always injects" structural rather than a branch.
        self.assertIsNone(flowctl.BACKEND_REGISTRY["host"].get("run_exec"))
        # export never reaches a flowctl prompt builder; it is a skill route.
        source = (Path(__file__).resolve().parents[1]
                  / "scripts" / "flowctl.py").read_text(encoding="utf-8")
        self.assertNotIn("embed_payload", source)


if __name__ == "__main__":
    unittest.main()
