---
satisfies: [R7]
---
# fn-168-review-convergence-lost-ratchet-prompt.5 review.maxIterations config key + ralph-guard self-grant block

## Description
Make the review cap settable from config — `review.maxIterations` with env > config > default-8 precedence — and block `config set review.maxIterations` in ralph-guard, because a persisted cap is a self-grant path the env var never was.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`get_max_review_iterations`, `get_default_config`), `scripts/gen_flow_config_schema.py` + the regenerated committed schema artifact, `plugins/flow-next/scripts/hooks/ralph-guard.py`, `plugins/flow-next/tests/` (cap-precedence tests, guard tests, `test_flow_config_schema_drift`), `plugins/flow-next/docs/flowctl.md` / `docs/orchestration.md` as the config-key reference requires, `.flow/bin/flowctl.py` (propagation)

### Approach
- **Why this task exists at all:** the spec's accepted consequence (a) tells future maintainers to *lower the cap instead of re-adding inference*. Today `get_max_review_iterations()` (~:9556) reads **env only** — no config key, none in the published schema — so the advertised knob would mean threading `MAX_REVIEW_ITERATIONS` through pilot, land, ralph, and every manual invocation with nothing persisted. Shipping the advice without the valve guarantees the advice is ignored.
- Add `review.maxIterations`. **Precedence: env `MAX_REVIEW_ITERATIONS` > config > default 8.** Apply the `>= 1` clamp on **both** paths (today the clamp lives only in the env branch); the cap is never disable-able and never 0 (fn-159 invariant). Invalid / non-integer / `0` / negative on either path falls back to the default.
- **GUARD (non-optional — this is the reason the task is not just a config key). THREE routes, not one (plan-review round 1, P0).** A durable cap is a **self-grant path**: an autonomous agent could write itself 99 rounds and defeat fn-159's *"the implementing agent can never reset or extend its own gate."* Verified against `ralph-guard.py`, all three routes are open today:
  1. **`flowctl config set` writing the cap — in BOTH its leaf and parent-key forms (plan-review round 2, P0).** `config set` is not on the recovery blocklist (which blocks `reset-review-rounds`, `review-rounds reset`, `--force` dispatches). Verified in `_set_config_locked`: a string value beginning `{` or `[` is `json.loads`-coerced, and the nested-path walk creates/replaces whole subtrees — so **`flowctl config set review '{"maxIterations":99}'` writes the same cap through the parent key** and a leaf-key-only screen does nothing. Block **both**: the exact leaf key `review.maxIterations`, and a `config set review <JSON>` whose value carries a `maxIterations` member. The simplest sound rule is to block any `flowctl config set` invocation that names `maxIterations` in the key or the value — precise, and it leaves every other key alone.
     - Scope it to the cap, NOT to `config set` wholesale — a blanket block would break the tracker resolve transactions and setup writers that legitimately run under Ralph. `config set review.backend …` must still pass; pin that with a positive test.
     - Decision: **block outright**, not "allow lowering, block raising" — simpler, safe, and a human setting it once is the intended path; humans aren't guard-gated.
  2. **A file-tool write to `.flow/config.json`** — the path is **not** in `PROTECTED_FILE_PATTERNS` (which holds `ralph-guard.py`, `flowctl.py`, `.claude/settings.json`, `.factory/*`, `.codex/hooks.json`, `/hooks/hooks.json`). Add it. Note this screens **file tools only**, so flowctl's own config writers (`config set`, tracker resolve) are unaffected.
  3. **`MAX_REVIEW_ITERATIONS=99 …` on a command** — the **higher-precedence** route, and a **pre-existing** hole (nothing screens it today; `_ENV_ASSIGN_RE` is used for argv classification, not for blocking). Block the assignment. The env var has exactly one purpose, so a tokenized block on any assignment of it is safe and does not need a co-occurrence screen — but follow the existing screens' shape if a launcher co-occurrence is preferred after reading them.
  - Use the same **tokenized** matching the existing screens use — memory `shell-command-allowlist-gates-must-2026-06-05`: tokenize, never substring-match. Follow the existing shape, including the raw-text floor and assignment-value smuggle patterns (`_RECOVERY_ASSIGN_RE` and friends, ~:702-738) and the argv pass (~:1340-1370). Each route gets its own guard test.
  - **Caveat to state in the code comment and the docs:** the guard does not fire on Cursor (different hook events), degrading to prose-only exactly as the existing reset block already does.
  - Blocking only route 1 while shipping a durable key would make this spec a **net regression** on autonomy safety — that is why all three are in scope, including the pre-existing one.
- **Perf:** `get_max_review_iterations()` has **7 call sites** (~:11337, :29676, :29844, :40664, :41113, :41458, plus the def). Do NOT add 7 config round-trips — memoize once per process or resolve via the existing config snapshot (`load_config_snapshot` ~:1637). fn-110 (round-trip diet) and fn-109 (memoize repo root) exist precisely to prevent this.
- **fn-138 contract:** extend the TABLE in `scripts/gen_flow_config_schema.py` (descriptions map ~:58, TABLE ~:561-572 — note `review` is a **closed** object today holding only `review.backend`), regenerate the committed artifact by running that script in the same change, and keep `test_flow_config_schema_drift` green.
- Decide and state whether the default belongs in `get_default_config()`'s `review` block (so `config get review.maxIterations` returns 8 rather than null on a fresh repo, matching the `work.delegate*` precedent) or stays resolved in code only — then make the precedence tests reflect the choice.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `get_max_review_iterations` (~:9556) and all 7 call sites; `get_default_config` (the `review` block); `load_config_snapshot` (~:1637) / `get_config` (~:1568) for the memoization choice
- `plugins/flow-next/scripts/flowctl.py` — `cmd_config_set` (~:19771) and `_set_config_locked`: the JSON-object coercion and nested-subtree replacement that make the parent-key bypass (route 1b) real
- `plugins/flow-next/scripts/hooks/ralph-guard.py` — the recovery screens (~:702-738 patterns, ~:1200-1234 raw-text floor) and the argv pass (~:1340-1370): match their tokenized style exactly
- `scripts/gen_flow_config_schema.py` — descriptions map (~:58) and `_build_table` (~:561-572); the `review` object's `open: False` flag
- `plugins/flow-next/tests/test_flow_config_schema_drift.py` — the drift contract this change must satisfy

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py` — `work.delegateModel` resolution as the precedent for a config-with-code-default key
- the existing ralph-guard tests — where a new blocked-verb case belongs

### Key context
- Independent of `.1`/`.2`/`.3` in code, but it touches `flowctl.py` like all of them — serialize in one checkout unless isolated. **`.4` depends on this task** (added at plan-review round 1): `.4` owns the full suite, lint, propagation, and docs gate, and this task changes `flowctl.py`, the schema, the guard, and docs — a gate that ran before it would not be the promised final gate.
- The guard block is the load-bearing half of this task. A config key with only one of the three routes blocked would *weaken* fn-159's invariant, making the spec net-negative on autonomy safety.
- `DEFAULT_MAX_REVIEW_TRANSPORT_FAILURES` (~:9593) is a sibling env-only knob — deliberately **out of scope**; do not opportunistically add a config key for it.
- Docs: a new config key needs a reference entry wherever `review.backend` is documented.

## Acceptance
- [ ] `review.maxIterations` resolves with precedence env `MAX_REVIEW_ITERATIONS` > config > default 8
- [ ] `>= 1` clamp on **both** paths; invalid / non-integer / `0` / negative on either path falls back to the default; the cap can never be disabled
- [ ] Precedence matrix tested explicitly: config-only, env-only, both, invalid config value, `0`/negative on each path
- [ ] Route 1a: `flowctl config set review.maxIterations <n>` BLOCKED by ralph-guard with tokenized matching (never substring), covering the raw-text floor and assignment-value smuggle shapes the existing screens cover
- [ ] Route 1b: the parent-key bypass `flowctl config set review '{"maxIterations":99}'` BLOCKED — verified against `_set_config_locked`'s JSON coercion + subtree replacement, not assumed
- [ ] Positive test: `flowctl config set review.backend codex` and other unrelated `config set` writes still PASS (the block is scoped to the cap, not to `config set`)
- [ ] Route 2: a file-tool write to `.flow/config.json` BLOCKED via `PROTECTED_FILE_PATTERNS`; flowctl's own config writers (`config set`, tracker resolve) verified unaffected
- [ ] Route 3: a `MAX_REVIEW_ITERATIONS=` assignment on a command BLOCKED (tokenized) — the higher-precedence, pre-existing hole
- [ ] Each of the three routes has its own guard test
- [ ] The Cursor non-coverage caveat is stated in the guard comment and the docs (prose-only degradation, same as the existing reset block)
- [ ] Resolution memoized once per process (or via the config snapshot) — the 7 call sites do not become 7 config round-trips; verified, not assumed
- [ ] fn-138 contract honored: TABLE + description extended in `scripts/gen_flow_config_schema.py`, committed artifact regenerated in the same change, `test_flow_config_schema_drift` green
- [ ] Default placement (config defaults vs code-only) decided, stated in the done summary, and reflected in the tests
- [ ] `DEFAULT_MAX_REVIEW_TRANSPORT_FAILURES` untouched
- [ ] Docs updated wherever `review.backend` is documented as a config key
- [ ] Focused suites green: `python3 -m unittest test_review_convergence_cap test_flow_config_schema_drift test_tracker_distribution -q` plus the ralph-guard suite
- [ ] Propagation done (cp flowctl.py to .flow/bin)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
