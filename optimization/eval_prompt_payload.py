"""Eval-harness-only payload embedding (fn-169 R4).

`flowctl.build_review_prompt` and friends carry IDENTITIES — repo-relative spec
paths and a commit range — because a production reviewer runs inside the
repository and fetches what it needs. The eval harnesses in this tree are in the
opposite position, and deliberately so:

  * their experimental variable IS the spec/code content, varied per arm;
  * there is no repository for a reviewer to read those arms from.

That is the same situation as the `--review=export` mode, where the payload is
the only channel available. So the harnesses append their own payload blocks
after calling the identity builder, and this is the single place that does it.

Two rules keep the carve-out from leaking:

  1. This helper lives under `optimization/`, never in `flowctl.py`. A production
     path that wanted it would be re-adding embedding.
  2. The block ORDER matches the pre-fn-169 production builder, so a variant-to-
     variant delta in an eval stays attributable to the wording under test rather
     than to a prompt-layout change.

`plugins/flow-next/tests/test_eval_harness_prompt_api.py` executes the harness
entrypoints and asserts both rules.
"""

from __future__ import annotations


def embed_payload(
    prompt: str,
    *,
    spec: str = "",
    diff_summary: str = "",
    diff_content: str = "",
    task_specs: str = "",
) -> str:
    """Append the payload blocks the identity builder no longer emits."""
    blocks = []
    if diff_summary:
        blocks.append(f"<diff_summary>\n{diff_summary}\n</diff_summary>")
    if diff_content:
        blocks.append(f"<diff_content>\n{diff_content}\n</diff_content>")
    if spec:
        blocks.append(f"<spec>\n{spec}\n</spec>")
    if task_specs:
        blocks.append(f"<task_specs>\n{task_specs}\n</task_specs>")
    if not blocks:
        return prompt
    return prompt + "\n\n" + "\n\n".join(blocks)
