# fn-32-opt-in-review-flags.2 --deep flag: additional specialized passes on top of primary review

## Description

Implement `--deep` flag. Primary Carmack-level review runs unchanged; additional specialized passes (adversarial / security / performance) run in the same backend session and contribute findings that merge with primary via confidence anchors. Auto-enable heuristic for security/performance based on diff paths.

**Size:** L

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` — flag parsing
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — deep-pass flow
- `plugins/flow-next/skills/flow-next-impl-review/deep-passes.md` (new) — three prompt templates + auto-enable heuristics
- `plugins/flow-next/scripts/flowctl.py` — `codex deep-pass`, `copilot deep-pass` subcommands
- `.flow/bin/flowctl.py` (mirror)

## deep-passes.md

### Auto-enable heuristics

**Security pass auto-enables when diff includes any of:**
- `**/auth*`, `**/Auth*`
- `**/permissions*`, `**/Permission*`
- `**/routes/*`, `**/routers/*`
- `*Controller.rb`, `*Controller.py`, `*Controller.ts`
- `**/middleware*`
- `**/session*`, `**/Session*`
- `**/*[Tt]oken*`
- `**/api/*` (if backend API routes)
- `**/*.env*`, `.github/workflows/*`

**Performance pass auto-enables when diff includes any of:**
- `**/migrations/*`, `**/migrate/*`
- `**/db/schema.rb`, `**/*.sql`
- Explicit query patterns in diff (e.g., `.where`, `.find`, SQL keywords)
- Cache-related paths: `**/cache*`, `**/redis*`, `**/memcache*`
- Background job definitions: `**/jobs/*`, `**/workers/*`

**Adversarial pass: always runs when `--deep` set** (no auto-enable heuristic needed; it's the baseline of deep).

### Explicit override

`--deep=adversarial,security` — restrict to listed passes. If security wouldn't auto-enable but user asks, it runs.

`--deep` alone → adversarial + whichever of security/performance auto-enable.

### Adversarial pass prompt template

Framed around constructing failure scenarios. Content adapts the MergeFoundry upstream adversarial persona style:

```markdown
# Adversarial pass

You've already reviewed this diff and produced primary findings. Now switch modes.

Instead of evaluating against known patterns, **construct specific scenarios that break this implementation.** Think in sequences: "if this happens, then that happens, which causes this to fail."

Techniques:
1. **Assumption violation** — what assumptions does this code make? (data shapes, timing, ordering, value ranges) Where is each violable?
2. **Composition failures** — where do components interact? Contract mismatches, shared state mutations, ordering across boundaries, error-type divergence.
3. **Cascade construction** — build multi-step failure chains: A causes B causes C.
4. **Abuse cases** — how would a malicious or naive user/caller break this?

Do not re-surface findings you already flagged in the primary review. **Probe for what wasn't caught.**

Output format: same as primary review — findings with severity, confidence anchor (0/25/50/75/100), classification (introduced/pre_existing), file:line, suggested fix. Tag each finding with `pass: adversarial`.
```

### Security pass prompt template

```markdown
# Security pass

Specialized security review. Primary findings are available as context.

Focus areas:
- Authentication gaps: missing auth checks on endpoints, session handling flaws
- Authorization gaps: missing ownership checks, IDOR patterns, privilege escalation
- Input handling: injection (SQL, command, template), deserialization issues, XSS
- Secrets handling: hardcoded credentials, token leakage in logs, insecure storage
- Permission boundaries: TOCTOU, race conditions on auth state, trust boundaries crossed

Do not re-flag issues already in primary findings. Probe for specific security patterns the primary review's generalist framing may have missed.

Output format: same as primary — tag findings with `pass: security`.
```

### Performance pass prompt template

```markdown
# Performance pass

Specialized performance review.

Focus areas:
- Database: N+1 queries, missing indexes, large scans, transaction scope
- Algorithmic: O(n²) where O(n) suffices, unbounded loops, repeated computations
- I/O: sequential calls that could parallelize, sync calls in hot path, missing cache
- Memory: unbounded growth, reference leaks, large-object allocations in loops
- Concurrency: contention, lock ordering, async-over-sync anti-patterns

Do not re-flag issues already in primary findings. Probe for specific performance patterns the primary review's generalist framing may have missed.

Output format: same as primary — tag findings with `pass: performance`.
```

## flowctl `codex deep-pass` / `copilot deep-pass` subcommands

```
flowctl codex deep-pass --pass <adversarial|security|performance> --receipt <path> [--primary-findings <path>] [--json]
flowctl copilot deep-pass --pass <adversarial|security|performance> --receipt <path> [--primary-findings <path>] [--json]
```

Behavior:
1. Read session ID from receipt — continues the primary-review session for context
2. Load the pass-specific prompt from `deep-passes.md`
3. Inject `--primary-findings` content (if provided) as context
4. Invoke backend with resumed session
5. Parse output; return findings list tagged with `pass: <name>`

## Skill integration

Flag parse:

```bash
DEEP=false
DEEP_PASSES=""
for arg in $ARGUMENTS; do
  case "$arg" in
    --deep) DEEP=true ;;
    --deep=*) DEEP=true; DEEP_PASSES="${arg#--deep=}" ;;
  esac
done

# Env opt-in
if [[ "${FLOW_REVIEW_DEEP:-}" == "1" ]]; then
  DEEP=true
fi
```

Workflow (in workflow.md):

```bash
if [[ "$DEEP" == "true" ]]; then
  # Determine which passes to run
  PASSES=()
  if [[ -n "$DEEP_PASSES" ]]; then
    IFS=',' read -ra PASSES <<< "$DEEP_PASSES"
  else
    PASSES=("adversarial")  # always
    # Auto-enable security/performance based on diff paths
    if <diff matches security globs>; then PASSES+=("security"); fi
    if <diff matches performance globs>; then PASSES+=("performance"); fi
  fi

  # Run each pass in same session
  for pass in "${PASSES[@]}"; do
    $FLOWCTL $BACKEND deep-pass --pass "$pass" --receipt "$RECEIPT_PATH" --primary-findings /tmp/primary-findings.json
  done

  # Merge findings: primary + all deep-pass outputs
  # Dedupe by fingerprint (file + line_bucket + normalized title)
  # Cross-pass agreement: same fingerprint in primary + deep → promote one confidence anchor step
  # Re-compute verdict over merged set
fi
```

## Receipt extension

```python
if deep_passes:
    receipt_data["deep_passes"] = list(deep_passes)  # ["adversarial", "security"]
    receipt_data["deep_findings_count"] = {
        pass_name: count for pass_name, count in findings_by_pass.items()
    }
```

## Auto-enable heuristic implementation

In skill bash, compute:

```bash
CHANGED_FILES=$(git diff --name-only "$BASE_COMMIT")

matches_security_globs() {
  echo "$CHANGED_FILES" | grep -qE '(auth|Permission|routes|Controller|middleware|session|Token|api/|\.env)' 
}

matches_performance_globs() {
  echo "$CHANGED_FILES" | grep -qE '(migrations|migrate|schema\.rb|\.sql$|cache|redis|memcache|jobs/|workers/)' 
}
```

Print auto-enable decisions in the skill output:

> Deep passes selected: adversarial (always), security (auto — diff touches auth files)

## Acceptance

- **AC1:** `--deep` flag parsed; `FLOW_REVIEW_DEEP=1` env var also enables.
- **AC2:** `--deep=adversarial,security` restricts to listed passes explicitly.
- **AC3:** `--deep` alone → adversarial always + auto-enabled security/performance per diff paths.
- **AC4:** Three pass prompts defined in `deep-passes.md` — adversarial, security, performance.
- **AC5:** Auto-enable heuristic correctly matches security/performance globs against changed files.
- **AC6:** `flowctl codex deep-pass` and `flowctl copilot deep-pass` subcommands exist and continue the primary session via receipt's session_id.
- **AC7:** Each pass's findings tagged `pass: <name>`; merged with primary via fingerprint dedup.
- **AC8:** Cross-pass agreement promotes confidence one anchor step when same finding appears in primary + deep.
- **AC9:** Verdict re-computed over merged findings.
- **AC10:** Receipt carries `deep_passes` + `deep_findings_count`.
- **AC11:** `--deep` off → existing behavior unchanged; no deep passes invoked.
- **AC12:** Skill output reports pass selection decisions transparently.

## Dependencies

- Depends on Epic fn-29 (confidence anchors for merge logic, fingerprint convention)
- Depends on fn-32-opt-in-review-flags.1 (flag parsing infrastructure; tasks can land in either order but share workflow.md edits)

## Done summary
Implemented fn-32.2 --deep flag: three specialized passes (adversarial always, security/performance auto-enabled by diff globs or explicit --deep=csv) layered on top of the primary Carmack review. Each pass continues the primary backend session via receipt session_id; findings merge into the receipt via fingerprint dedup with primary+deep agreement promoting confidence one anchor step (50→75, 75→100, ceiling 100). Cross-deep collisions dedup but don't promote (avoids double-counting correlated passes). SHIP→NEEDS_WORK upgrade fires when deep surfaces new blocking findings; verdict never downgrades. Added codex/copilot deep-pass subcommands, review-deep-auto heuristic helper, deep-passes.md prompt templates + auto-enable glob list, SKILL.md flag parsing + FLOW_REVIEW_DEEP env, workflow.md Deep-Pass Phase section, 9 new smoke tests (113 total pass). Receipt extensions (deep_passes, deep_findings_count, cross_pass_promotions, verdict_before_deep, deep_timestamp) are additive — existing Ralph scripts unaffected.
## Evidence
- Commits: 017d32f10fccc2c3c73dfc7243e62b4d1bb4e2f5
- Tests: bash plugins/flow-next/scripts/smoke_test.sh (113 passed, 0 failed); python3 unit tests for fingerprint, promote_confidence, merge_deep_findings, auto_enabled_passes, parse_deep_findings, load_deep_pass_template, _apply_deep_passes_to_receipt (10 assertions all OK)
- PRs: