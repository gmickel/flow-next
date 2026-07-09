# fn-76 Smart model resolution — strongest available, never fail

## Goal & Context

flow-next injects a hardcoded model on every review backend's unconfigured path. A hardcoded default cannot know per-user/per-plan/per-org/per-CLI-version availability — fn-74 hit it twice (Finding A, T6) and the GPT-5.6 launch (2026-07-10) reproduced it live: `gpt-5.6-sol` worked on cursor, 400'd on codex CLI < 0.144, and was rejected by copilot 1.0.65 — three answers for one string on one machine.

Naive fix rejected: defaulting to `auto`/CLI-default never fails but hands model choice to the vendor's cost-optimizing router — review quality is the whole point of the review backends. The fix is a **strongest-available resolution ladder**: flow-next curates a quality ranking; resolution finds the best entry the account can actually run; `auto`/omit is only the terminal never-fail floor.

## Architecture & Data Models

All in flowctl.py (dual-copied). No new user-facing surface; no setup ceremony.

1. **Preference ranking (per backend).** The registry `models` set becomes an ORDERED quality ranking (strongest first), e.g. cursor: `gpt-5.6-sol-high` > `gpt-5.6-terra-high` > `claude-opus-4-8-thinking-high` > `gpt-5.5-high` > … Curated by flow-next, updated opportunistically; **lenient** — unknown explicit models warn-and-accept (the CLI stays the availability authority), the ranking is preference, never a parse-time gate.
2. **Resolution — list-capable backend (cursor):** run `cursor-agent --list-models` at resolution time, intersect with the ranking, pick the top. List call failure/timeout → floor rung. 
3. **Resolution — no-list backends (codex, copilot):** optimistic ladder with **fail-soft on the review call itself**: dispatch with the ranking's top entry; iff the exec fails with the backend's DISTINCTIVE model-unavailable signature (codex: HTTP 400 `invalid_request_error` "The '<m>' model requires a newer version of Codex" / model-not-available; copilot: `Model "<m>" from --model flag is not available` — both captured verbatim 2026-07-10), step down the ranking and retry. Max 2 steps, then the floor rung (codex: omit `--model`; copilot: `--model auto`). Any OTHER failure propagates unchanged (never retried).
4. **Per-CLI-version cache.** The resolved model is memoized keyed by `(backend, cli --version)` in `.flow/.cache/model-resolution.json` (gitignored, atomic write). Hit → zero probe/ladder cost. CLI upgrade changes the key → natural invalidation. `--spec`/explicit models bypass the cache entirely. Corrupt/missing cache = cold start, never an error.
5. **Floor-rung hygiene:** on the floor, omit `--effort` (unknown family); receipts record the model actually used when parseable from CLI output, else `"auto"`/`"default"` — never a fabricated name.

## API Contracts

- Explicit model anywhere in the precedence chain (`--spec` > per-task/per-spec `review` > env > config): byte-identical to today, no probing, no cache, no retry-downgrade — an explicit unavailable model errors clearly.
- Unconfigured path: resolved model = strongest ranking entry the account can run (cursor: list-proven; codex/copilot: ladder-proven, cached), else floor.
- `BackendSpec.parse("<backend>:<unknown-model>")`: warn-and-accept; effort axis stays strict.
- Receipt `model` = actual model used; ladder downgrades and floor hits emit one visible stderr warning naming what was tried and what ran.

## Edge Cases & Constraints

- **Ladder must not mask real failures:** only the captured model-unavailable signatures trigger a step-down; auth/network/sandbox/timeout errors propagate unchanged.
- **Ralph/headless:** ladder + cache work unattended (no prompts); list-probe failure inside CI degrades to floor with the warning on stderr.
- **Review-cap interaction (fn-90):** a ladder retry is the SAME review round — `enforce_and_increment_review_cap` fires once per logical dispatch, not per rung (the ladder lives inside the exec wrapper, below the cap).
- **Cache staleness inside one CLI version** (org revokes a model mid-version): the ladder's fail-soft still catches it on the next dispatch (a cached-model 400 with the distinctive signature clears that cache entry and re-resolves — one extra retry, self-healing).
- Cross-platform: copilot Windows stdin/session logic untouched; codex mirror regenerated.
- The 2.10.3 interim cursor pin (`gpt-5.6-sol-high`) remains correct meanwhile and becomes the ranking's top entry — behavior converges.

## Acceptance Criteria

- [ ] **R1:** Registry `models` becomes an ordered per-backend quality ranking; `BackendSpec.parse` warns-and-accepts unknown models (effort strict); unit-tested.
- [ ] **R2:** Cursor unconfigured resolution picks the top ranking entry present in `--list-models` output (mocked list in tests: full list, partial list, empty/failed list → floor); the real list call is one bounded subprocess with a timeout.
- [ ] **R3:** Codex/copilot unconfigured resolution ladders on the captured model-unavailable signatures ONLY (fixture streams from the 2026-07-10 live probes), max 2 steps, floor = omit/`auto`; any other error propagates; a ladder retry does not consume an extra fn-90 review-cap round; unit-tested with mocked execs.
- [ ] **R4:** Resolution memoized per `(backend, CLI version)` in `.flow/.cache/model-resolution.json` (atomic, gitignored, corrupt-safe); explicit models bypass; a cached model failing with the distinctive signature invalidates its entry and re-resolves; unit-tested.
- [ ] **R5:** Floor omits `--effort`; receipts record the actual model (else `"auto"`/`"default"`); downgrade/floor emits one stderr warning; full suite + smoke green; dual-copy parity; mirror regenerated; docs updated (flowctl.md resolution section, troubleshooting entry).

## Boundaries

- Out: any setup-ceremony/model-discovery question (resolution is automatic; setup MAY later surface the resolved model read-only — separate item); a user-facing `flowctl <backend> models` command (internal helper only, expose later if wanted); BYOK/custom providers; mid-review model switching; changing explicit-pin semantics.
- Out: ranking auto-derivation from vendor metadata — the ranking is curated (quality judgment is flow-next's value-add; lenient parse keeps it non-blocking when it lags).

## Decision Context

`auto`-as-default was tried in spec v2 and REJECTED by the maintainer (2026-07-10): vendor routers optimize their cost, not review quality — the review backend exists to buy quality. The ladder keeps v2's never-fail floor while restoring quality: strongest-available beats both a hardcoded guess (fails: fn-74 Finding A/T6, GPT-5.6 launch) and `auto` (quality floats with the vendor).

Why resolution-time instead of a setup ceremony (the v1 fat spec's shape): the availability answer changes with CLI upgrades and plan changes — a setup-time snapshot goes stale exactly like a hardcoded default, just slower. Resolution-time + per-CLI-version cache answers fresh when it matters and costs ~nothing when it doesn't.

Why max-2 ladder steps: the ranking's top entries are the ones worth trying; below that the floor's quality is comparable and each step costs a failed API round-trip. Distinctive-signature-only retries keep the ladder from masking real failures.

**Live verification base (2026-07-10):** cursor `--list-models` includes the full `gpt-5.6-sol` family + `auto`; codex 0.144.1 runs `gpt-5.6-sol` and no-model OK, codex 0.142 400s with the "requires a newer version" signature; copilot 1.0.65 rejects `gpt-5.6-sol` with the `--model flag is not available` signature and accepts `--model auto`. All error signatures for R3's fixtures were captured verbatim from these probes.

**Interim (2.10.3):** cursor default pinned to live-verified `gpt-5.6-sol-high`; codex accepts `gpt-5.6-sol` explicitly; codex/copilot defaults held at `gpt-5.5`. This spec supersedes the interim by making the pin's VALUE the ranking's top and the resolution availability-aware.
