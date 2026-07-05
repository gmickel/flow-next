---
satisfies: [R2, R3, R9, R10, R11, R12]
---

## Description

Add the optional model-routing scaffold ceremony to the setup skill: one grouped question, probe-annotated block composition, pre-write read-back, marker-fenced write with byte-compare re-run idiom, optional delegation config set.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-setup/workflow.md`, `plugins/flow-next/skills/flow-next-setup/SKILL.md` (description clause), `plugins/flow-next/codex/**` (regenerated)

## Approach

- **Question (Step 6d):** join the existing grouped-question mechanics (follow whatever chunking the file already does — do not invent a new call shape). Frozen options: `scaffold` / `scaffold + enable codex delegation` (include this option ONLY when `HAVE_CODEX=1`) / `skip` (default). Under any non-interactive marker (Ralph/autonomous family), skip silently — never ask.
- **Processing (Step 7):** new block AFTER the existing Docs-block processing (~L653-674), operating on the file state on disk (sequential, never interleaved):
  1. Resolve target file(s) via the deterministic ladder (R12), independent of whether the Docs question fired: (a) Docs answered this run → mirror the choice (incl. "Both" → same block to both); (b) Docs skipped/current → the file(s) already carrying the `BEGIN FLOW-NEXT` docs marker (both → Both); (c) neither → platform-default mapping (workflow.md 6b buckets: Droid-with-Claude, Cursor). Shim guard, exact patterns: target whose only non-empty content line matches `@<path>.md` or `See[:] <path>.md` (case-insensitive, repo-relative) → follow the pointer when the file exists in-repo, else report + skip; anything else = normal file.
  2. Compose the block from `templates/model-routing-snippet.md` via the deterministic sentinel line transform (R10): `HAVE_CODEX=0` → comment out exactly the `<!-- probe:codex -->` lines + install note; same for `HAVE_CURSOR`. Both probes fail → all sentinel lines commented + note, or recommend skip. Also substitute the provenance line's invocation syntax per platform (`/flow-next:setup` on Claude/Droid/Cursor, `$flow-next-setup` on Codex — same split as the snippet templates).
  3. Inspect marker + byte-compare FIRST (against the current composed canonical): identical → silent no-op, END (nothing shown, no mtime bump — R11). Only on a would-write path continue to step 4.
  4. Would-write branches: no marker in file → proceed to read-back; marker present + different (user edits OR probe-state drift, e.g. a CLI installed since the last scaffold) → `Keep mine (Recommended)` / `Overwrite with canonical` / `skip` (R11 — probe drift counts as canonical drift, never a silent rewrite); Overwrite chosen → proceed to read-back. Also detect a model-routing-shaped heading WITHOUT our markers → augment-or-skip question, never duplicate. **Read-back (R3, would-write path only):** show the FULL composed block, options `write` / `skip`, immediately before the write.
  5. Post-write: one confirmation line inviting free editing ("this section is yours now; re-run setup to regenerate").
  6. If option was `scaffold + enable codex delegation`: `flowctl config set work.delegate codex` via existing machinery; NEVER touch `work.delegateConsent` (R9). Read persisted config back to confirm (ceremony-validation-reads-persisted rule).
- **Step 8 summary:** add one line reporting scaffold outcome (written/kept/skipped + file).
- **SKILL.md:** extend the description line with the optional scaffold clause (keep README/docs/skills.md rows for fn-88.4).
- Regenerate Codex mirror; verify the mirror renders the new question as a plain-text numbered prompt with the same frozen options and no AskUserQuestion mention (R5 — the existing catch-all transform should handle it; verify, don't assume).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:353-420` — probes (HAVE_CODEX/HAVE_CURSOR L359-362), docs-status marker detection, platform buckets
- `plugins/flow-next/skills/flow-next-setup/workflow.md:496-580` — grouped question shapes + option conventions
- `plugins/flow-next/skills/flow-next-setup/workflow.md:653-680` — Docs-block processing idiom to clone (byte-compare, Keep-mine question, no-mtime discipline)
- `plugins/flow-next/skills/flow-next-setup/templates/model-routing-snippet.md` — the canonical block (from fn-88.2)

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:9490-9573` — `_discoverability_pick_target`/shim detection (reference for the shim guard; the guard itself stays skill-prose, cheap check)
- `plugins/flow-next/codex/skills/flow-next-setup/workflow.md` — post-sync mirror to verify the transform

## Key context

- Memory (binding): sync-codex AskUserQuestion→numbered-prompt transform is prose surgery — run the mirror check after regen; hand-editing `codex/` is forbidden. Ceremony validation reads PERSISTED config, not env.
- Re-running setup must not bump mtime on unchanged files (workflow.md discipline, L425/L665).

## Acceptance

- [ ] Question appears in interactive setup with frozen options; delegation option only when HAVE_CODEX=1; silent skip under non-interactive markers
- [ ] Sentinel line transform correct for all four HAVE_CODEX×HAVE_CURSOR combinations (both-fail path per R10); provenance invocation syntax platform-correct
- [ ] Ordering: compare-before-read-back — identical re-run shows nothing; would-write path shows full composed block (write/skip) before the marker-fenced write with provenance; post-write invitation printed
- [ ] Re-run: identical-to-current-canonical → silent no-op (mtime unchanged); user-edited OR probe-drifted → Keep-mine/Overwrite/skip; unmarked routing heading → augment-or-skip, no duplicate
- [ ] Target ladder: Docs-answer → marker-location → platform-default all covered; "Both" writes both files; shim patterns exact (follow or report+skip)
- [ ] Delegation opt-in sets `work.delegate codex` only; `work.delegateConsent` untouched (verified from persisted config)
- [ ] Mirror regenerated: numbered-prompt rendering verified, zero AskUserQuestion mentions; full pytest + smoke green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
