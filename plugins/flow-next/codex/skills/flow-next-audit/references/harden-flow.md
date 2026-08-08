# Phase 4.7: Harden flow (gated reference — interactive only)

> **Loaded only after an explicit Harden accept in Phase 3.** In `mode:autofix`
> no gate artifact is written and no entry is demoted — candidates go straight
> to the Phase-5 Recommended bucket, so an autofix run never reads this file.
> An interactive run with no accepted Harden candidate never reads it either.
> The decision-shaping rules (verification is a hard precondition of demotion;
> `<rule-id>` must be a literal substring; never `git rm` on Harden) also live
> in the always-loaded phases.md §Harden.

### 4.7 — Harden flow (interactive only — autofix never applies)

**Autofix stops here.** In `mode:autofix` no gate artifact is written and no entry is demoted; candidates go straight to the Phase-5 Recommended bucket. Everything below runs only after an explicit accept in Phase 3.

Process Harden candidates **one at a time, sequentially** — each one edits shared repo infrastructure and each needs its own verification run.

1. **Write the artifact** to the accepted surface via Edit / Write — exactly the draft the user accepted, nothing more. Lint and CI edits are surgical (one rule, one step); instruction-file edits stay 1-2 lines and never restructure the file.
2. **Verify the gate actually fires.** This is a hard precondition of demotion, not a formality — writing config is not enforcing a rule, and a gate that does not fire is strictly worse than no gate: it retires the only working copy of the lesson while enforcing nothing. By gate type:
 - **lint** — run the linter and confirm the new rule is active in the **resolved** config: not merely present as text in a file the tool does not read, and not neutralized by a later `ignore` / disable entry.
 - **CI** — confirm the step parses and sits in a workflow AND a job that actually run on the relevant trigger, not a disabled, unreferenced, or manual-only one.
 - **instruction file** — confirm the rule landed in the substantive file the agents actually read (same discovery as Phase 6 §6.1), not an `@`-including stub.
3. **Verification failed** → **stop**. The entry stays `active`, `mark-hardened` is NOT called, and the artifact edit is reported alongside a **failed graduation** with the reason (`ruff does not read this file`, `job never runs on push`, `landed in the @-include shim`). Leave the artifact for a human to fix or revert; do not silently retry with a different gate type.
4. **Verification passed** → demote:

 ```bash
 "$FLOWCTL" memory mark-hardened "$ENTRY_ID" \
 --gate-ref "<path>#<rule-id> -- <note>" \
 --audited-by "/flow-next:audit"
 ```

 The helper sets `status: hardened`, stores `hardened_into` verbatim, clears the stale-only fields, and stamps `last_audited` (a UTC date — a same-day re-mark is observably a no-op on that field). It is atomic and preserves unknown frontmatter fields — **never hand-edit frontmatter to demote**.
5. **`--gate-ref` format** is the skill's contract (flowctl stores it verbatim and validates only non-emptiness — parsing it there would be judgment leaking into plumbing): `<path>#<rule-id> -- <note>`, with `<path>` repo-relative and `<rule-id>` a **literal substring of the artifact at that path** — copy the exact token from the file you just wrote. §0.75.2 greps for it verbatim on the next run, so a locator expression describing where the rule lives (`tool.ruff.select:DTZ`, `jobs.lint.steps[name=ruff]`, a heading anchor, a JSON path) is wrong: it never occurs in the TOML/YAML/Markdown, and the live gate would be falsely proposed for un-graduation. Grep the artifact to confirm the ref hits before calling `mark-hardened`. `<note>` is a short human gloss — never grepped, so put the human context there. One example per gate type:

 - lint: `pyproject.toml#DTZ -- ruff select entry, bans naive datetimes` (`DTZ` is the literal token in the select list)
 - CI: `.github/workflows/ci.yml#ruff check -- lint job runs the DTZ gate` (the command string as written in the YAML)
 - instruction file: `CLAUDE.md#stamp timestamps in UTC ISO-8601 -- instruction-file floor gate` (the rule line's own wording)

**Never `git rm` on Harden — on any track.** The entry file stays on disk with its body intact; it becomes a pointer at the gate, so provenance survives and "why does this rule exist?" stays answerable. For `knowledge/decisions/` entries the supersession fields (`decision_status`, `superseded_by`, `alternatives_considered`) are preserved alongside the new status — `mark-hardened` touches only status, `hardened_into`, `last_audited`, and `audit_notes`.

**Pointer-demotion (duplication guard found an active gate):** skip steps 1-3 entirely — the gate already exists and was already confirmed active. Go straight to step 4 with the existing gate as `--gate-ref`. No new artifact is written.

**Un-graduation (§0.75.2, gate gone):**

```bash
"$FLOWCTL" memory mark-fresh "$ENTRY_ID" --audited-by "/flow-next:audit"
```

Returns the entry to `active` and drops `hardened_into`, so the lesson re-enters the context window. Autofix reports the proposal instead of applying it.
