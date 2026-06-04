# Binary evals (4) — max score per run = 4

EVAL 1: Grounded
Question: Does EVERY `path:line` / `path` reference in the output point to a file that actually exists in the repo?
Pass: All cited paths resolve to real files (verified with `test -f`). Zero hallucinated paths.
Fail: Any cited path does not exist.

EVAL 2: Tagged
Question: Does every "Related Code" finding carry a `[VERIFIED]` or `[INFERRED]` confidence tag?
Pass: Every related-code bullet has exactly one tag.
Fail: Any related-code bullet is untagged.

EVAL 3: Lean (TOKEN LEVER)
Question: Is the total output <= 700 tokens (~525 words)?
Pass: word count * 4/3 <= 700.
Fail: over 700 tokens.

EVAL 4: Focused (no copy-paste bloat)
Question: Does the output obey the prompt's own Output Rule — signatures only, no code snippet > 10 lines, no complete function bodies?
Pass: No fenced code block exceeds 10 lines; no full function/method body reproduced.
Fail: Any snippet > 10 lines or a complete implementation pasted.
