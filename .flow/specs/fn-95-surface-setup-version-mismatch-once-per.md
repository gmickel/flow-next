# fn-95 Surface setup-version mismatch: once-per-version blocking ack in interactive skills, loud verdict line in autonomous skills

## Goal & Context
<!-- scope: business -->

Every lifecycle skill already runs a fail-open version pre-check (the `## Pre-check: Local setup version` block, present in ~21 SKILL.md files, e.g. `plugins/flow-next/skills/flow-next-interview/SKILL.md` lines 22-33): it compares `.flow/meta.json` `setup_version` against the plugin manifest version and, on mismatch, emits a one-line `echo` telling the user to run `/flow-next:setup`.

Detection works. Surfacing does not. The `echo` lands inside a bash block that the host agent routinely paraphrases away or buries under skill output, so users never act on it. Proof: this very repo sat at `setup_version` 2.6.0 while the plugin was at 2.12.2 and the maintainer never noticed across dozens of skill runs. A stale local setup means stale `flowctl` copies under `.flow/bin/`, stale templates, and stale docs, which silently degrades every downstream skill.

This spec changes ONLY what happens on mismatch:
- Interactive skills escalate to a blocking `AskUserQuestion`, asked ONCE per new plugin version, with the acknowledgement persisted so users are never re-nagged for a version they already dismissed. Nag fatigue is the failure mode that produced the silent echo in the first place; do not reintroduce it.
- Autonomous skills (pilot, land) never block, but the mismatch becomes loud and durable: a dedicated line adjacent to the terminal `PILOT_VERDICT` / `LAND_VERDICT` output so it survives into driver logs and summaries.

The check itself (fail-open, cheap, jq-based) is unchanged.

## Architecture & Data Models
<!-- scope: technical -->

**Ack persistence.** New optional field `version_ack` in `.flow/meta.json`, sibling of `setup_version`:

```json
{
  "next_spec": 96,
  "schema_version": 3,
  "setup_date": "...",
  "setup_version": "2.6.0",
  "version_ack": "2.12.2"
}
```

Semantics: "the user has been asked about plugin version X and chose not to refresh." Written only by the interactive mismatch flow. Cleared implicitly: `/flow-next:setup` rewrites `setup_version` to the current plugin version, after which the pre-check comparison passes and `version_ack` is inert (no cleanup needed; setup MAY drop it when writing meta.json but is not required to).

**Write mechanism.** No `flowctl` meta.json field-setter exists (verified: `flowctl.py` has no `meta set` subcommand; setup writes meta.json fields via jq). Anchor to the existing jq + atomic-write pattern already used by the setup workflow (`plugins/flow-next/skills/flow-next-setup/workflow.md`, meta.json shape near line 346): `jq '.version_ack = "<PLUGIN_VER>"' .flow/meta.json > tmp && mv tmp .flow/meta.json`, tmp file in the same directory for same-filesystem atomicity. Do NOT add a new flowctl subcommand for this; it is one field on one file and the skill-side jq write keeps the change small.

**Escalation logic (interactive skills).** The existing pre-check bash block gains one extra read: `VERSION_ACK=$(jq -r '.version_ack // empty' .flow/meta.json 2>/dev/null)`. Decision table:

| condition | behavior |
|---|---|
| no mismatch | silent, continue (unchanged) |
| mismatch AND `version_ack == PLUGIN_VER` | one-line echo (current behavior), continue; no question |
| mismatch AND `version_ack != PLUGIN_VER` (or empty) | blocking `AskUserQuestion`, then act per answer |
| jq/meta.json/manifest missing or unparseable | silent, continue (fail-open, unchanged) |

`AskUserQuestion` options (frozen set):
1. `Refresh now` - instruct the user that the skill will pause while they run `/flow-next:setup`; setup has NO dedicated non-interactive refresh flag (verified in `flow-next-setup/workflow.md`), but its older-version path already proceeds without a y/n gate ("Updating from vOLD to vNEW" then continue, workflow.md line 134). After setup completes, continue the skill. Do not attempt to run setup from inside the current skill.
2. `Remind me next version` - write `version_ack = PLUGIN_VER` via the jq atomic write, continue. User will only be re-asked when the plugin version changes again.
3. `Skip this run` - continue without writing anything; the question re-fires next skill invocation (deliberate: skip is a per-run answer, ack is a per-version answer).

**Autonomous-skill path (pilot, land).** Their pre-check blocks (`flow-next-pilot/SKILL.md` line 25, `flow-next-land/SKILL.md` line 29, both currently "Non-blocking, same pattern as /flow-next:plan") stay non-blocking and never ask. On mismatch they carry the fact to the terminal verdict: emit a dedicated `SETUP_STALE: local vX.Y.Z, plugin vA.B.C, run /flow-next:setup` line immediately before the `PILOT_VERDICT` / `LAND_VERDICT` line, so any driver that captures the verdict tail captures the warning. `version_ack` does NOT suppress this line (logs are cheap; human attention at the terminal was the scarce resource, driver logs are grep-able).

**Autonomy-marker guard.** Interactive skills can also run under autonomous drivers (Ralph loops invoke work/plan). The blocking question MUST be suppressed under the autonomy-marker family already used by setup (`flow-next-setup/workflow.md` lines 388-396): `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set, `FLOW_AUTONOMOUS=1`, or `ARGUMENTS` containing `mode:autonomous`. Under any marker, fall back to the one-line echo (current behavior).

**Cross-platform.** Canonical skill files write `AskUserQuestion`; `scripts/sync-codex.sh` already rewrites AskUserQuestion invocations into the numbered-prompt instruction for the Codex mirror (verified: the mirror at `plugins/flow-next/codex/skills/flow-next-interview/SKILL.md` line 24 already carries the pre-check block). No special handling needed beyond regenerating the mirror via `scripts/sync-codex.sh` after editing canonical files.

## API Contracts
<!-- scope: technical -->

- `.flow/meta.json` gains OPTIONAL `version_ack: string` (a plugin semver). Absence means "never acknowledged". `flowctl init` / `doctor` MUST tolerate its presence (they already ignore unknown keys; verify, do not rewrite them to strip it).
- Interactive pre-check block contract (the block every interactive skill embeds): reads `setup_version`, `version_ack`, plugin manifest version; on ask-worthy mismatch invokes `AskUserQuestion` with exactly the three options above; writes `version_ack` only on option 2; always continues the skill afterward. All reads/writes fail open.
- Autonomous verdict contract: on mismatch, one line matching `SETUP_STALE: local v<setup_version>, plugin v<plugin_version>, run /flow-next:setup` emitted in the same terminal output block as, and before, `PILOT_VERDICT:` / `LAND_VERDICT:`. Absent when versions match or either version is unreadable.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Fail-open is inviolable.** Missing jq, missing meta.json, missing/unreadable plugin manifest, unwritable meta.json (jq write fails): never block, never error the skill; degrade to the current echo or to silence exactly as today.
- **Concurrent skill runs**: two skills racing the `version_ack` write is harmless (same value, atomic mv; last writer wins).
- **`setup_version` newer than plugin** (user downgraded plugin): still a mismatch; same flow applies; the question copy should say "differs from" not "older than".
- **No repeated asks within one skill run**: a skill asks at most once; sub-skills / subagents spawned by a skill must not re-run the interactive escalation (subagent-embedded copies of the pre-check, if any, keep the plain echo).
- **Do not touch detection**: the comparison logic, the jq expressions for `setup_version` / plugin version, and the `${DROID_PLUGIN_ROOT}/${CLAUDE_PLUGIN_ROOT}` manifest resolution stay byte-identical in spirit; only the on-mismatch branch changes.
- **Prompt weight**: the added prose per skill must stay small (this block is always-loaded context in ~21 skills; reuse one canonical wording, keep the decision table out of the skill files and encode it as compact bash + 3-4 lines of instruction).

## Acceptance Criteria
<!-- scope: both -->

- **R1:** In every interactive lifecycle skill carrying the `## Pre-check: Local setup version` block (interview, plan, work, capture, tracker-sync, sync, make-pr, resolve-pr, qa, prime, audit, prospect, strategy, memory-migrate, ralph-init, etc. - enumerate by grep for the block at implementation time; map is EXCLUDED: it is non-interactive by design and map_smoke_test.sh Case 1 guards its allowed-tools against the ask tool - map keeps the non-blocking echo), a `setup_version` vs plugin-version mismatch with no matching `version_ack` triggers a blocking `AskUserQuestion` with exactly the options Refresh now / Remind me next version / Skip this run, before the skill proceeds.
- **R2:** Choosing "Remind me next version" writes `version_ack: "<plugin version>"` to `.flow/meta.json` via jq + same-directory tmp file + atomic `mv`; subsequent skill runs under the same plugin version show only the one-line echo and never re-ask. A later plugin version (any value different from `version_ack`) re-arms the question.
- **R3:** Choosing "Skip this run" continues without writing `version_ack`; the next skill invocation asks again.
- **R4:** `/flow-next:pilot` and `/flow-next:land` never invoke `AskUserQuestion` for the mismatch; on mismatch they emit the `SETUP_STALE: local v<X>, plugin v<Y>, run /flow-next:setup` line in the terminal output immediately before their `PILOT_VERDICT` / `LAND_VERDICT` line, regardless of `version_ack`.
- **R5:** Interactive skills running under any autonomy marker (`FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set, `FLOW_AUTONOMOUS=1`, `ARGUMENTS` contains `mode:autonomous`) suppress the question and fall back to the current one-line echo.
- **R6:** Fail-open preserved: with jq absent, or `.flow/meta.json` absent/unparseable, or the plugin manifest unreadable, every skill proceeds exactly as today (no question, no error, no block). The detection comparison itself is unchanged.
- **R7:** Codex mirror parity: after `scripts/sync-codex.sh`, the mirrored skills carry the escalated block with `AskUserQuestion` rewritten to the numbered-prompt instruction (including the final "Other" option per the sync script's existing transform), and the autonomous skills' `SETUP_STALE` line is present verbatim.
- **R8:** `flowctl init` and `flowctl doctor` run clean against a meta.json containing `version_ack` (field tolerated, not stripped, not flagged).

## Boundaries
<!-- scope: business -->

- NO change to the detection logic, its cost, or its fail-open posture.
- NO new flowctl subcommand; the ack write is skill-side jq.
- NO non-interactive refresh mode added to `/flow-next:setup` (out of scope; "Refresh now" instructs the user to run setup).
- NO auto-running `/flow-next:setup` from inside another skill.
- NO receipts schema change; the autonomous surfacing is the terminal verdict-adjacent line only. (If a later spec wants `setup_stale` in receipt JSON, that is its own change.)
- NO nag escalation beyond once-per-version: `version_ack` semantics are final for a given version.

## Decision Context
<!-- scope: both -->

Blocking-once-per-version was chosen over louder non-blocking output (banners, repeated echoes) because the field evidence shows non-blocking text does not survive host-agent paraphrasing: this repo ran 2.6.0-era local files against a 2.12.2 plugin for weeks with the echo firing on every skill run. A blocking question is the only primitive the host agent cannot bury. The `version_ack` field caps the cost at one question per plugin release per project, which is the highest frequency that does not recreate nag fatigue. Skill-side jq (not a flowctl helper) keeps the diff small and matches how setup itself writes meta.json. Autonomous skills get a grep-able `SETUP_STALE` line co-located with the verdict because that is the one output surface drivers are contractually required to read; receipts were considered and deferred to keep this spec surfacing-only. The autonomy-marker guard reuses the exact family setup already honors so there is one convention, not two.

---
