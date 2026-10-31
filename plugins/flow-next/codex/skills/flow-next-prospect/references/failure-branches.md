# Prospect: failure branches and the numbered fallback (gated reference)

> Read from workflow.md only when Phase 2 under-delivers, the critique rejects below the floor, or
> no plain-text numbered prompt is reachable at Phase 6.

## Under-volume

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

If fewer than `floor(GENERATION_TARGET_MIN * 0.7)` valid candidates survive validation, surface a plain-text numbered prompt:

```
Phase 2 produced only K valid candidates (target was M-N). Options:
  retry      — re-run Phase 2 with the same prompt
  loosen     — proceed with K candidates anyway (Phase 3 floor still applies)
  abort      — exit; no artifact written
```

The `loosen` path keeps the run going but flags the under-volume in the eventual artifact frontmatter (`generation_under_volume: true`) so downstream readers know the spread was narrow.

## Critique floor

If `rejection_rate < REJECTION_FLOOR`, surface a **plain-text numbered prompt** with the frozen options:

```
Critique rejected only X% (below the ≥Y% floor). Options:
  regenerate    — re-run Phase 2 + Phase 3 from scratch (new candidates)
  loosen-floor  — accept this critique result; ship survivors as-is
  ship-anyway   — same as loosen-floor; preserved for clarity in transcripts
```

Frozen string format (anchor — must match across backends): `regenerate | loosen-floor | ship-anyway`. Use `plain-text numbered prompt`. Validate the choice; reject anything outside the three options.

- `regenerate` → loop back to Phase 2 §2.3 with a fresh prompt invocation. Cap at **1 regeneration**; a second floor violation auto-routes to `loosen-floor` with a printed warning (avoids infinite loops on a model that genuinely can't reject).
- `loosen-floor` / `ship-anyway` → continue to Phase 4. Record `floor_violation: true` in the eventual artifact frontmatter.

## Numbered-options fallback

When plain text is the prompt mechanism (or the platform tool errors), print this **exact** string format. Do not paraphrase, re-order, or add commentary:

```
Saved: .flow/prospects/<artifact-id>.md

Promote a survivor to a spec?
  <position>) Promote #<position>: <title>
  ...
  s) Skip
  i) Refine (ask $flow-next-refine what to refine)

Enter choice [<position>|i|s]:
```

Number each survivor by its artifact position (the `#### <position>.` heading; positions can skip numbers), in artifact order. `s` is Skip; `i` is the alphabetic refine shortcut. (The frozen menu does not advertise chart; a typed `c`/`chart` reply still routes via 6.3.)
