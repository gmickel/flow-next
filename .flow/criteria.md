# Global acceptance criteria

Standing criteria judged by spec-completion-review on every spec. Grammar: one
`- **G<N>:** <criterion>` bullet per criterion; never renumber.

- **G1:** Prompt-prose growth is justified, not silently accumulated. When a change grows an always-loaded skill surface (SKILL.md, workflow/phases files) or an embedded prompt template, the spec or PR states what the added prose buys and why it earns its context cost; pure restatement, defensive hedging, or duplicated instructions are rejected in review. Frozen char-count ceilings are not the instrument - reviewer judgment against this criterion is.
- **G2:** Tests assert behavior or contract, never prose quality. A new or modified test may pin the smallest distinctive token (a verdict line, a field name, a heading, a count, a parity/byte relation) or drive a real code path; it may not assert prose sentences, paragraph wording or order, char counts, or frozen size/hash baselines of live files. Prompt quality is judged by evals and G1 review; deliberate-change detection lives in test_prompt_text_pinned.py alone.
