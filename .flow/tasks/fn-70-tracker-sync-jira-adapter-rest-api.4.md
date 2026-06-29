## Goal
Regenerate the Codex mirror and complete the full doc sweep — flipping "Jira out of scope" everywhere — + changelog. (Spec R8, R9.) [dep: fn-70.1, .2, .3.]

## Files
- `bash scripts/sync-codex.sh` → regenerate `plugins/flow-next/codex/` mirror.
- `plugins/flow-next/docs/tracker-sync.md` — flip the "Jira out of scope" line to supported; document `tracker.type jira` + `baseUrl`/`projectKey`/**`authScheme`/`apiVersion`/`sslVerify`**/`statusMap`.
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md` — confirm the ceremony table's "Jira out of scope" line is flipped (fn-70.1) and consistent.
- **`plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md`** — update the implemented-by table, the `issue.tracker` enum, the receipt-transport enum (add `rest`), the Jira `authorAuthority` mapping note, the `listOpenIssues` Jira semantics, **AND the relation/`linkPresent` prose (rp-review B3): fn-69's text says `linkPresent:false`/`block-only` is GitLab-only and names the Linear/GitHub `linkPresent:true` paths — ADD Jira there: native issue links return `source:"unknown"`, `linkPresent:true`, no orphan/block divergence.**
- **Doc sweep — every stale "Linear/GitHub" / "Jira out of scope" enumeration.** Named floor: `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/skills.md`, `teams.md`, root `README.md`, `GLOSSARY.md`, the Codex `openai.yaml` description + `scripts/sync-codex.sh` registration line. **But the named list is a FLOOR, not a ceiling (rp-review B4 / fn-69 scar):** run a **broad grep** — `grep -rniE 'linear.*github|jira.*(out of scope|surfaced|not.*offered)|tracker\.type.*linear' plugins/ docs/ *.md` — and sweep EVERY hit, explicitly including `plugins/flow-next/commands/flow-next/tracker-sync.md` frontmatter, `plugins/flow-next/docs/README.md`, the tracker-sync SKILL.md **frontmatter description**, and `flow-next-setup/templates/usage.md` + `claude-md-snippet.md` if they enumerate trackers.
- `CHANGELOG.md` — `## Unreleased` entry (NO version bump).
- `~/work/flow-next.dev`: tracker-sync page (Jira), **BOTH navbars** (`site.ts` + `astro.config.mjs`), changelog `## Unreleased`. **`FLOW_NEXT_VERSION` is NOT changed by this task** (the batched release bumps it later).
- **Downstream chain (STANDING CLAUDE.md requirement — the fn-69 miss; NOT "only if"):** AI×SDLC guide (`guides/mcp-integrations.md` — its `### Jira` subsection currently frames Jira as in-development → flip to shipped; `guides/methodology.md` ticket-system checklist already lists Jira — confirm), GF microsite (if it enumerates trackers), and the **Obsidian vault flow-next space** (`~/Documents/GordonsVault/Spaces/Projects/flow-next` — Tracker Sync + Skills Catalog + Vocabulary notes: flip "Jira in active development / fn-70" → shipped). The vault is NOT git — edit the note files directly.
- `plugins/flow-next/tests/test_tracker_sync_mirror_parity.py` (or the existing parity test) — assert canonical `jira.md` is mirrored into `plugins/flow-next/codex/` AND the `openai.yaml` description includes Jira.

## Approach
- Deterministic sync-codex regen; commit mirror with canonical.
- Sweep every "supported trackers" / "Jira out of scope" site → Jira supported. Verify both flow-next.dev navbars (slug-set diff).
- Verify zero-setup floor (R9): a standard Jira credential (Cloud API token or DC/Server PAT) — no OAuth app / webhook / Connect / Forge.
- **Walk the FULL downstream chain** (repo → flow-next.dev → microsite / AI×SDLC / Obsidian vault); flip every "Jira in active development / surfaced-not-offered" → **shipped** wherever trackers are enumerated.
- **Land note (fn-69 scar):** this is the LAST task and it is **docs-heavy** — a docs-only commit tip won't get a codex review (codex skips pure-docs diffs; verified fn-69), so land's `AUTO_REVIEW_CURRENT` (silence) signal can't satisfy and land stalls at AWAITING_REVIEW. **Order the final pushed commit so a substantive (non-docs) change is the tip, OR** expect to merge via the authorized gate once CI + threads + window are green (don't wait on a codex review that won't come).

## Acceptance
- Mirror regenerated + parity test green (R8).
- docs/tracker-sync.md + SKILL.md "Jira out of scope" flipped; flow-next.dev (page + BOTH navbars + changelog) (R8).
- CHANGELOG `## Unreleased`; no version bump.
- Full downstream chain updated — flow-next.dev + AI×SDLC + GF microsite + **Obsidian vault** — "Jira in active development" flipped to **shipped** everywhere it appears (R8 + standing CLAUDE.md req).
- Full suite + flow-next.dev `pnpm build` green.

## Test notes
- Mirror/parity + full suite + docs-site build. No live Jira.

## Description
TBD

## Done summary
Regenerated the Codex mirror and swept Jira through every tracker-sync enumeration + per-adapter fidelity surface (adapter-interface.md implemented-by table / issue.tracker enum / terminal invariant / authorAuthority / relation source+linkPresent / direction / dedup / listOpenIssues JQL; docs/tracker-sync.md transport ladder + per-adapter relation/direction/readyState/dep-projection bullets + Linear-Diffs branch; flowctl.md config; README/GLOSSARY/teams/skills/commands/SKILL/steps/work/pilot/make-pr/setup; CHANGELOG Unreleased — no version bump; flat-tracker answer-matching prose). Extended the mirror-parity test to assert canonical jira.md is mirrored + openai.yaml/sync-codex register Jira. rp impl-review SHIP after 5 rounds; full suite (1283) + parity (17) green. A pre-existing jira.md ADF/flow:deps self-contradiction (Jira writes no block) was flagged out-of-scope as a tracked follow-up.
## Evidence
- Commits: e8594785aeb45bb85db995761b33289dd7ef3b64, e91a9d2c4bfc0ac415abadd295256351b3f59194, f495178d24a5090c87d06b85204c32e0032d38b5, 17cb87b4a868a6a9a0eeeab9f475539cb48cf1c4, b63f2e6cda5b06e62b847d13d0d4079514b95c98
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1283 tests, OK skipped=2), python3 -m unittest plugins.flow-next.tests.test_tracker_sync_mirror_parity (17 tests, OK — 8 new Jira parity assertions), bash scripts/sync-codex.sh (mirror regenerated, all validations pass)
- PRs: