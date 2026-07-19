# fn-115 model-pin registry: role map in config + agent refresh ceremony at setup

> STUB (2026-07-19, maintainer-requested during the fn-101 review). Problem: hardcoded model pins rot. Interview/plan before building.

## Goal & Context

Model pins are scattered and hardcoded across flow-next, and every one of them rots as providers ship new tiers:

- `BACKEND_REGISTRY` ladders + `default_model`/`default_effort` per backend (flowctl.py:4020-4110; comments literally say "keep synced with `copilot -p /model`" - manual maintenance, verified-by-hand dates in comments)
- triage judge defaults (`gpt-5-mini` codex / `claude-haiku-4.5` copilot, flowctl.py:27054)
- `work.delegateModel` config DEFAULT (`gpt-5.6-terra`, flowctl.py:1219)
- sync-codex.sh `CODEX_MODEL_INTELLIGENT`/`CODEX_MODEL_FAST` scout-tier pins (build-time, env-overridable)
- deep-pass/validator model defaults (ride the registry)

Two patterns in the repo already do NOT rot, and they point at the answer: agents/*.md `model:` uses family aliases resolved by the host (never version-pinned, per repo rule), and setup's CLAUDE.md routing table is scaffolded prose the agent re-ranks ("this section is yours now"). The rot lives exactly where pins are deterministic Python constants nobody re-judges.

Direction (doctrine-conformant split): flowctl stores and validates a pin map + does mechanical staleness math; the AGENT (setup skill) probes, judges, and refreshes it. No LLM calls, no probing, no "which model is best" logic in Python - leverage the host's intelligence, do not overbloat flowctl.

## Design sketch (refine at interview)

1. **Role map in config** - one place that rots, semantic roles not call-site pins:
   `models.roles.<role>.<backend>` in .flow/config.json, e.g. `fastJudge: {codex: gpt-5.6-luna, copilot: claude-haiku-4.5, cursor: composer-2.5}`, `review: {codex: gpt-5.6-sol, ...}`, `delegate: {codex: gpt-5.6-terra}`, `scoutFast`/`scoutIntelligent` (feeds sync-codex env at mirror-regen time). Plus `models.verifiedAt` (ISO date) and optionally `models.verifiedWith` (CLI versions probed). Start with ONLY the roles that exist today; no speculative roles.
2. **Resolution order** extends the existing fn-76 precedence (flowctl.py:4244): explicit CLI flag / per-task pin > env > config role map > registry baseline. The registry ladders REMAIN as availability fallbacks (the runtime model-unavailable step-down already self-heals "pin too new"); the role map heals "pin too old".
3. **Refresh ceremony (the intelligence, in the setup skill's prose)**: on fresh setup AND re-runs, the agent (a) probes installed CLIs for ground truth - `cursor-agent --list-models`, `copilot -p "/model"`, codex accept-probe; (b) judges from its own knowledge (optionally web) which current tiers fit each role (fast/cheap for fastJudge, strongest for review, value tier for delegate); (c) diffs against the config map and proposes changes via AskUserQuestion (show current -> proposed with one-line reasons); (d) writes accepted pins + verifiedAt stamp via `flowctl config set`. Skips silently in autonomous contexts.
4. **Staleness nudge (the only new flowctl logic besides map resolution)**: mechanical date check - if `models.verifiedAt` older than ~90d, setup/status prints a one-line "model pins last verified <date>; re-run setup to refresh" notice. Never blocks, never judges.
5. **Failure-feedback loop (agent-side, zero new plumbing)**: review receipts already record `model_used`; the refresh ceremony's prose has the agent scan recent receipts for fallback-ladder activations ("pin X keeps failing -> propose replacement").
6. **Downstream consumers**: triage judge (fn-113's interim default bump re-homes here), backend dispatch defaults, work.delegateModel default, sync-codex scout pins (maintainer regen reads the map or its env exports). CLAUDE.md routing table: refresh ceremony OFFERS to update it in the same pass (it is agent-owned prose already). agents/*.md family aliases: unchanged, explicitly out of scope.

## Boundaries / non-goals

- No new flowctl subcommands beyond what `config get/set` already provides plus map resolution + the date check. No probing, no ranking, no LLM invocation from Python.
- Registry baseline ladders stay (last-resort defaults for repos that never ran setup); fn-76 invariants (default_model == models[0]) keep holding for the baseline.
- Per-task `review:` pins and env overrides keep absolute precedence - this changes defaults, not steering.
- Coordinate with fn-112 (registry refactor) - land order matters; whoever lands second rebases the registry shape.

## Open questions

- Role vocabulary: minimum viable set (fastJudge / review / delegate / scoutFast / scoutIntelligent) or fold review into existing review.backend semantics?
- Should the staleness nudge live in setup only (quiet) or also `flowctl status` (visible)? Bias: setup only, avoid noise.
- Does sync-codex read the map directly (repo-local config at regen time) or via exported env (current mechanism)? Bias: env, keep the mirror build decoupled.

## Ladder policy + probed seed data (maintainer critique session, 2026-07-19)

Maintainer decisions on the current BACKEND_REGISTRY ladders:

1. **Floor rule**: review ladders floor at roughly gpt-5.6-terra-high intelligence. No mini/nano/4.1-class rungs on any REVIEW path - a weak model silently issuing SHIP verdicts is worse than failing loudly. When the ladder exhausts, error with a clear "no acceptable review model available - update your CLI or check model access" instead of degrading.
2. **codex ladder**: solve old-CLI compatibility via DOCUMENTATION ("update your codex CLI"), not programmatic rungs. Ladder shrinks to the 5.6 family (sol -> terra -> luna if accepted; probe codex CLI at build), then loud failure. Drop gpt-5.5/5.4/5.2/5/5-mini/5-codex rungs.
3. **copilot ladder**: reseed from GitHub's product docs (GA as of 2026-07: gpt-5.6 sol/terra/luna, claude-opus-4.8, claude-sonnet-5, claude-sonnet-4.6, claude-fable-5 w/ enterprise enablement) with the floor rule applied; org allowlists vary wildly (see probe below), so the ladder tops stay optimistic and the existing unavailable-signature step-down personalizes per account. Drop gpt-4.1 (GitHub already removed it) and the mini tails from review.
4. **cursor ladder**: fix the ordering bug (all five sol effort tiers currently outrank terra-high); effort-degraded sol rungs (medium/low/none) drop below terra-high or out entirely. Drop `auto` (unpredictable tier) and composer-2.5 from the REVIEW ladder - composer-2.5 and luna tiers are fastJudge/scout material, not review gates. claude-fable-5-* rungs are NO ZDR on cursor - keep them out of the default ladder; users opt in explicitly (existing CLAUDE.md guidance).
5. **Role map seeds**: fastJudge = luna-class (codex: gpt-5.6-luna; copilot: claude-haiku-4.5; cursor: composer-2.5 or gpt-5.6-luna-low). scoutFast likewise moves off gpt-5.4-mini to a luna tier at refresh.

Probe results 2026-07-19 (why per-install probing is the mechanism, not better universal pins):

- **cursor-agent 2026.07.16** (updated, then `--list-models`, 193 ids): full gpt-5.6 sol/terra/luna ranges (none->max, +fast variants), claude-opus-4-8 full range, claude-fable-5 (NO ZDR), claude-sonnet-5 range, cursor-grok-4.5 tiers, composer-2.5, gpt-5.5/5.4-high, codex 5.3/5.2/5.1-max families. Registry's v2026.06 snapshot already stale (missing fable-5, sonnet-5, grok tiers, opus-4-8 non-thinking range).
- **copilot, AUTHORITATIVE product list** (org model-policy page, pulled by maintainer 2026-07-19; enabled/disabled flags are per-org, the roster is what Copilot offers): Anthropic claude-sonnet-4 / 4.5 / 4.6 / sonnet-5, claude-haiku-4.5, claude-opus-4.5 / 4.6 / 4.7 / 4.8 (+4.8 fast-mode preview), claude-fable-5; OpenAI gpt-5.4, gpt-5.4-mini, gpt-5.5, gpt-5.6-luna / -sol / -terra, gpt-5-mini; Google gemini-2.5-pro, gemini-3.1-pro (preview), gemini-3-flash (preview), gemini-3.5-flash; xAI grok-code-fast-1; Microsoft MAI-Code-1-Flash; Moonshot kimi-k2.7-code. NOTE: exact `--model` id strings for the Gemini/Grok/MAI/Kimi rows are unverified in the CLI - probe at build before seeding.
- **copilot CLI 1.0.71 probe on the maintainer's org account** (allowlist example): ACCEPTS gpt-5.5, gpt-5.4, gpt-5.4-mini, claude-opus-4.7, claude-sonnet-4.5, claude-haiku-4.5. REJECTS (org-disabled) gpt-5.6-sol/terra/luna, claude-opus-4.8, claude-sonnet-5, claude-sonnet-4.6, claude-fable-5; gpt-4.1 no longer exists. Ladder tops stay optimistic (full product roster); the unavailable-signature step-down personalizes per org, and the refresh ceremony records the per-install truth. Also: registry claims default gpt-5.5, but a bare copilot session self-reports claude-sonnet-4.5 as its conductor on this account - verify what "default" even means per org at build.

Acceptance addition: BACKEND_REGISTRY ladders reseeded per the five policies above (coordinate shape with fn-112); triage defaults, work.delegateModel default, and sync-codex FAST/INTELLIGENT pins all resolve through the role map (they are the "other deterministic pins" - confirmed in scope).
