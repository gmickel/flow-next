# capture — duplicate / prior-capture branch (loaded on demand)

> Loaded ONLY when Phase 0.2 found **≥2 strong spec-title matches** with `REWRITE_TARGET` empty, or
> Phase 0.6 spotted a **prior-capture artifact id** in the conversation. A clean capture (0-1 strong
> matches, no prior artifact) never reads this file. Detection itself is inline in workflow.md — this
> file is only the branch handling.

## 0.5 — Branch on duplicate (interactive only)

When 0.2 detected ≥2 strong matches AND `REWRITE_TARGET` is empty:

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Format the question via `plain-text numbered prompt`:

- **header**: `Duplicate?`
- **body**: `Found <N> potentially overlapping spec(s): <spec-1> "<title-1>", <spec-2> "<title-2>". Recommended: <extend|proceed-anyway> — <one-sentence rationale>. Confidence: [<tier>].`
- **options** (frozen labels, no recommendation marker on the option itself):
  - `extend <spec-id>` — add criteria to the existing spec (capture exits; skill suggests `--rewrite <id>` rerun)
  - `supersede <spec-id>` — close the old spec and capture this one fresh (capture proceeds; the user closes the old one manually after capture lands)
  - `proceed-anyway` — accept that two specs will live alongside each other (capture proceeds)
  - `abort` — exit cleanly, no write

Recommendation logic:

| Strong match count | Recommended | Confidence |
|--------------------|-------------|------------|
| 3+ | `extend <strongest-id>` | `[high]` |
| 2 | `proceed-anyway` | `[judgment-call]` |

If the user picks `extend`, exit 0 with: `Re-run with --rewrite <spec-id> to overwrite the existing spec, or invoke /flow-next:interview <spec-id> to refine via Q&A.`

If `supersede` or `proceed-anyway`, store the choice and continue to Phase 1.

In **autofix mode**, when 0.2 detected ≥2 strong matches AND `REWRITE_TARGET` is empty:

```text
Error: <N> potentially overlapping spec(s) detected: <spec-1>, <spec-2>.
Capture cannot resolve duplicates in autofix mode.

Options:
  - Re-run with --rewrite <spec-id> to overwrite a specific spec.
  - Re-run interactively (drop mode:autofix) to choose extend / supersede / proceed-anyway.
```

Exit 2.

## 0.6 — Prior-capture artifact detected (R8, `REWRITE_TARGET` empty)

When the visible conversation carries prior-capture artifact references — patterns like `Spec captured at .flow/specs/<id>.md` from earlier turns:

- **Interactive:** ask via `plain-text numbered prompt` whether the user wants to (a) `--rewrite <id>` (re-run with the flag), (b) `proceed` (create a new spec anyway, accepting that two specs result), (c) `abort`.
- **Autofix:** exit 2 with: `Error: prior capture artifact <id> detected in conversation. Re-run with --rewrite <id> to overwrite, or interactively to choose. Pass --yes only after picking a path.`

Silent overwrite is never an option on either branch — idempotency requires `--rewrite <spec-id>` (R8).

## Downstream consequence — Phase 3 must-ask case (c)

Picking `supersede` or `proceed-anyway` here arms Phase 3's scope-conflict must-ask: if the new spec's drafted scope still substantively overlaps the old spec's on a load-bearing axis, case (c) fires (interactive asks how to carve up the boundary; autofix exits 2).
