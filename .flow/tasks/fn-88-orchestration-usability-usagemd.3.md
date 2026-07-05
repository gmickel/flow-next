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
  1. Resolve target file(s): the SAME file(s) the Docs ceremony resolved this run — platform mapping incl. Droid-with-Claude and Cursor buckets; "Both" → write the same block to both. Shim guard: if the target's flow-relevant content is a single-line pointer to another file, follow it when it resolves in-repo, else report + skip (R12).
  2. Compose the block from `templates/model-routing-snippet.md`, applying probe annotations: `HAVE_CODEX=0` → comment out codex rows/rules with "not detected on this machine — uncomment after installing"; same for `HAVE_CURSOR` (R10). Both probes fail → all cross-CLI content commented + note, or recommend skip.
  3. Pre-write read-back: show the FULL composed block; options `write` / `skip` (R3). Never silent.
  4. Write mechanics — clone the Docs-block idiom verbatim (byte-compare family): no marker in file → append; marker present + byte-identical to canonical-composed → silent no-op, no mtime bump; marker present + customized → `Keep mine (Recommended)` / `Overwrite with canonical` / `skip` (R11). Also detect a model-routing-shaped heading WITHOUT our markers → augment-or-skip question, never duplicate.
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
- [ ] Probe annotations correct for all four HAVE_CODEX×HAVE_CURSOR combinations (both-fail path per R10)
- [ ] Pre-write read-back shows full composed block; write is marker-fenced with provenance; post-write invitation printed
- [ ] Re-run: pristine → silent no-op (mtime unchanged); customized → Keep-mine/Overwrite/skip; unmarked routing heading → augment-or-skip, no duplicate
- [ ] "Both" writes both files; shim target followed or reported+skipped
- [ ] Delegation opt-in sets `work.delegate codex` only; `work.delegateConsent` untouched (verified from persisted config)
- [ ] Mirror regenerated: numbered-prompt rendering verified, zero AskUserQuestion mentions; full pytest + smoke green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
