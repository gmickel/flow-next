# fn-29-review-rigor-bundle.6 Trivial-diff skip pre-check

## Description

Add fast-model triage to impl-review: before invoking the configured backend, a cheap-model judgment decides whether the diff is worth a full review. Lockfile-only / release-chore / docs-only / generated-file-only diffs return `VERDICT=SHIP` with receipt `mode: triage_skip` and reason. Saves rp/codex/copilot calls on Ralph runs and user-triggered reviews alike.

**Size:** M (flowctl + skill integration)

**Files:**
- `plugins/flow-next/scripts/flowctl.py` — new `triage-skip` subcommand
- `.flow/bin/flowctl.py` (mirror)
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` — Step 0 triage call; opt-out flag
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — workflow section describing triage

## Change details

### flowctl `triage-skip` subcommand

Signature:

```
flowctl triage-skip [--base <ref>] [--backend <codex|copilot|claude>] [--model <fast-model>] [--receipt <path>] [--json]
```

Behavior:
1. Compute diff summary: `git diff --stat <base>..HEAD` + list of changed files
2. Build a minimal triage prompt:

   ```
   Diff summary:
   <stat output>

   Changed files:
   <list>

   Is this diff worth a full code review?

   Answer SKIP only if the diff matches one of:
   - Lockfile-only bumps: package-lock.json, bun.lock, pnpm-lock.yaml, yarn.lock, Gemfile.lock, poetry.lock, Cargo.lock, uv.lock (and nothing else)
   - Pure release chore: version bump in plugin.json / package.json / Cargo.toml + CHANGELOG entry, no other code
   - Pure documentation: only *.md files changed, no executable code
   - Pure generated-file regeneration: plugins/flow-next/codex/ (from sync-codex.sh), or other clearly-generated paths
   - Pure vendored-asset changes: files under /vendor/, /third_party/, or similarly designated paths

   When in doubt, answer REVIEW. A missed review is worse than a skipped chore.

   Output exactly one line:
   SKIP: <one-line reason>
   or
   REVIEW: <one-line reason>
   ```

3. Invoke the fast model:
   - Claude backend available → spawn Agent with `model: "haiku"` (`claude-haiku-4-5-20251001`)
   - Codex backend → `codex exec --model gpt-5.4-mini` with `-c model_reasoning_effort="low"`
   - Copilot backend → `gh copilot` with `claude-haiku-4.5`
   - Backend selection uses the same priority chain as impl-review: `--backend` arg > `FLOW_REVIEW_BACKEND` > config > default-codex
4. Parse output:
   - `SKIP: <reason>` → return exit 0 + `{verdict: "SHIP", mode: "triage_skip", reason: "<reason>"}`
   - `REVIEW: <reason>` → return exit 1 (non-zero signals "proceed to full review") + json blob with reason
   - Malformed output → return exit 1 (conservative — fall through to full review)
5. If `--receipt` provided and SKIP: write receipt with:

   ```json
   {
     "type": "impl_review",
     "id": "<uuid>",
     "mode": "triage_skip",
     "base": "<base-ref>",
     "verdict": "SHIP",
     "reason": "<one-line>",
     "model": "<fast-model-used>",
     "timestamp": "<iso>"
   }
   ```

### impl-review skill integration

Add Step 0 to `SKILL.md` workflow, **before** Step 1 (detect backend):

```markdown
### Step 0: Trivial-diff triage (skip pointless reviews)

Unless `--no-triage` is in $ARGUMENTS, run:

FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"

TRIAGE_OUT=$($FLOWCTL triage-skip --base "${BASE_COMMIT:-main}" --receipt "${REVIEW_RECEIPT_PATH:-/tmp/impl-review-receipt.json}" --json)

if [[ $? -eq 0 ]]; then
  echo "Triage-skip: $(echo "$TRIAGE_OUT" | jq -r '.reason')"
  echo "VERDICT=SHIP"
  exit 0
fi
```

Exit 0 from triage-skip means "this skipped"; impl-review exits early with SHIP. Exit 1 means "proceed to full review"; impl-review falls through to Step 1.

Document the opt-out in the skill body:

> **Triage opt-out.** Pass `--no-triage` to skip the fast-model pre-check. Useful for forced deep reviews or when the triage model is unavailable.

### Ralph compatibility

Ralph sets `REVIEW_RECEIPT_PATH` before invoking `/flow-next:impl-review`. On SKIP, the receipt is written with `mode: triage_skip` and `verdict: SHIP`. Ralph's gate logic reads `verdict` — `SHIP` satisfies the gate regardless of mode. No Ralph-script changes required.

Triage is **on by default** in Ralph mode. Ralph opt-out via env var:

```bash
FLOW_RALPH_NO_TRIAGE=1
```

Skill checks `FLOW_RALPH_NO_TRIAGE` and `--no-triage` arg with equivalent effect.

### Cost-model note

Triage call uses a fast model (haiku / gpt-5.4-mini). Roughly 1/20th the cost of a full Carmack-level review. Net cost on a Ralph run: decreases whenever triage catches a trivial diff; otherwise ~2% overhead.

## Rationale

Ralph loops regularly produce lockfile-only commits (dep updates via tools), release-chore commits (version bumps), and docs-only commits. Each one currently triggers rp/codex/copilot full review. MergeFoundry upstream's trivial-PR judgment pattern saves those cycles cheaply. Conservative "when in doubt, REVIEW" rule prevents false skips.

## Acceptance

- **AC1:** `flowctl triage-skip` subcommand exists with `--base`, `--backend`, `--model`, `--receipt`, `--json` flags.
- **AC2:** Exit code 0 = SKIP, exit code 1 = proceed to full review, exit code ≥ 2 = error (tooling unavailable / malformed output).
- **AC3:** On SKIP with `--receipt`, receipt written with `mode: triage_skip`, `verdict: SHIP`, `reason`, `model`.
- **AC4:** impl-review SKILL.md calls triage-skip as Step 0 when `--no-triage` / `FLOW_RALPH_NO_TRIAGE` absent.
- **AC5:** impl-review exits early on SKIP with `VERDICT=SHIP` in output; no backend call invoked.
- **AC6:** Lockfile-only diff (single `bun.lock` change) → SKIP.
- **AC7:** Version-bump + CHANGELOG diff only → SKIP.
- **AC8:** Pure docs diff (only `*.md` in changed files) → SKIP.
- **AC9:** Any diff touching `src/` or `plugins/flow-next/scripts/flowctl.py` → REVIEW (even if small).
- **AC10:** Ralph smoke test runs unchanged; if triage-skip fires on an actual Ralph cycle, receipt verdict=SHIP advances the loop correctly.
- **AC11:** `--no-triage` opt-out works; `FLOW_RALPH_NO_TRIAGE=1` also disables triage.

## Out of scope

- LLM-as-judge for pre-existing vs introduced during triage (full review handles that).
- Multi-file heuristic sophistication (e.g., "small docs change piggy-backed with one code line") — keep triage rules tight and conservative.
- Caching triage decisions across re-reviews (fresh call each time).

## Risks

| Risk | Mitigation |
|------|------------|
| Fast model hallucinates SKIP on real code changes | Strict whitelist prompt; "when in doubt REVIEW" rule; exit-1 default on malformed |
| Triage adds latency to user-triggered reviews | Fast model is ~1-2s; negligible vs full review |
| Triage backend unavailable (haiku down) | Non-zero exit code + falls through to full review |
| User expects full review on lockfile-only diff | `--no-triage` opt-out documented |

## Done summary
Added `flowctl triage-skip` subcommand + impl-review Step 0.5 integration that short-circuits lockfile-only / docs-only / release-chore / generated-only diffs with SHIP verdict (mode=triage_skip), avoiding full rp/codex/copilot review calls. Deterministic whitelist layer is the default (conservative: ambiguous → REVIEW); optional LLM judge via FLOW_TRIAGE_LLM=1 (codex gpt-5-mini / copilot claude-haiku-4.5). Opt-out via --no-triage or FLOW_RALPH_NO_TRIAGE. Smoke tests (71/71) cover classifier, deterministic logic (all 4 AC scenarios: lockfile/docs/release-chore/generated → SKIP, code → REVIEW), LLM-output parser, and git-diff e2e.
## Evidence
- Commits: 691b13e172d36b69c8bfafe1709082914f33af90
- Tests: plugins/flow-next/scripts/smoke_test.sh (71/71 passed)
- PRs: