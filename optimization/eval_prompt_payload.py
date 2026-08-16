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
  2. The blocks are INSERTED BEFORE `<review_instructions>`, exactly where the
     pre-fn-169 builder put them. Appending them after the rubric would move the
     experimental content to the end of the prompt and change recency alongside
     the variable under test, silently invalidating comparisons against earlier
     eval results (impl-review r3, P2).

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
    # impl-review r4 (P2): the identity rubric DECLARES `<diff_range>` and
    # `<changed_files>` and calls `<spec>` a path. In a harness none of that is
    # true — there is no repo and `<spec>` holds prose — so the prompt would tell
    # the reviewer it received things it did not. Correct the contract explicitly
    # rather than leaving the rubric lying about its own inputs.
    override = (
        "## HARNESS INPUT OVERRIDE — read first\n\n"
        "This is an offline evaluation run with NO repository access. The "
        "`Context Gathering` section below describes the production input shape; "
        "for this run it does not apply. You did NOT receive `<diff_range>` or "
        "`<changed_files>`, and `<spec>` holds the spec TEXT, not a path. "
        "Everything you need is embedded verbatim in the blocks that follow. Do "
        "not attempt to read files, run `git`, or resolve any path.\n\n---\n"
    )
    payload = override + "\n" + "\n\n".join(blocks)
    marker = "<review_instructions>"
    idx = prompt.find(marker)
    if idx == -1:
        # Standalone-shaped prompts have no instructions tag; the rubric is at the
        # top, so appending is already payload-before-nothing.
        return prompt + "\n\n" + payload
    return prompt[:idx] + payload + "\n\n" + prompt[idx:]

# Fix for issue #314: safe input handling
