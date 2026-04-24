# Deep-pass prompts (fn-32.2 --deep)

Three specialized passes that layer on top of the primary Carmack-level review.
All three run in the **same backend session** as the primary review — the model
already has the diff + primary findings loaded, so these passes are cheap
continuations that probe for what the primary framing may have missed.

Findings from each pass are tagged with `pass: <name>` and merged with the
primary findings via fingerprint dedup. Cross-pass agreement (same fingerprint
appears in primary + deep) promotes confidence one anchor step (0 → 25 → 50 →
75 → 100).

## Auto-enable heuristics

The skill layer decides which passes run. Adversarial always runs when `--deep`
is set; security and performance auto-enable when the diff's changed-file list
matches their globs.

### Security pass auto-enables when diff includes any of:

- `**/auth*`, `**/Auth*`
- `**/permissions*`, `**/Permission*`
- `**/routes/*`, `**/routers/*`
- `*Controller.rb`, `*Controller.py`, `*Controller.ts`
- `**/middleware*`
- `**/session*`, `**/Session*`
- `**/*[Tt]oken*`
- `**/api/*` (if backend API routes)
- `**/*.env*`, `.github/workflows/*`

### Performance pass auto-enables when diff includes any of:

- `**/migrations/*`, `**/migrate/*`
- `**/db/schema.rb`, `**/*.sql`
- Explicit query patterns in diff (e.g., `.where`, `.find`, SQL keywords)
- Cache-related paths: `**/cache*`, `**/redis*`, `**/memcache*`
- Background job definitions: `**/jobs/*`, `**/workers/*`

### Adversarial pass

Always runs when `--deep` is set. No auto-enable heuristic — it is the baseline
of deep and assumes any non-trivial diff benefits from adversarial probing.

## Explicit override

`--deep=adversarial,security` restricts to the listed passes. If security
wouldn't auto-enable for this diff but the user explicitly asks, it runs anyway.
`--deep` alone → adversarial + whichever of security / performance auto-enable.

---

## <!-- ADVERSARIAL_TEMPLATE --> Adversarial pass prompt

```markdown
# Adversarial pass

You've already reviewed this diff and produced primary findings. Now switch modes.

Instead of evaluating against known patterns, **construct specific scenarios
that break this implementation.** Think in sequences: "if this happens, then
that happens, which causes this to fail."

Techniques:

1. **Assumption violation** — what assumptions does this code make? (data
   shapes, timing, ordering, value ranges) Where is each violable?
2. **Composition failures** — where do components interact? Contract mismatches,
   shared state mutations, ordering across boundaries, error-type divergence.
3. **Cascade construction** — build multi-step failure chains: A causes B causes
   C. Do not stop at a single failure if a chain is visible.
4. **Abuse cases** — how would a malicious or naive user/caller break this?

Do not re-surface findings you already flagged in the primary review. **Probe
for what wasn't caught.** If you find nothing new, say so — it is a valid
result.

## Output format

Same format as primary review — severity, confidence anchor (0/25/50/75/100),
classification (introduced/pre_existing), file:line, suggested fix. Prefix each
finding's id with `a` to distinguish from primary (`a1`, `a2`, ...) and tag the
finding with `pass: adversarial`.

Example:

    **a1** | severity=P1 | confidence=75 | classification=introduced | pass=adversarial
    - location: `src/auth.ts:42`
    - issue: cascade — if upstream rate-limiter resets mid-request, middleware reuses stale token
    - suggested fix: re-validate token after any upstream transition

## Suppression gate

Suppress findings below anchor 75 except P0 @ 50+ (same rule as primary).
Report suppressed count in a `Suppressed findings (adversarial):` line.

## Primary findings (for context; do NOT re-flag)

<!-- PRIMARY_FINDINGS_BLOCK -->
```

---

## <!-- SECURITY_TEMPLATE --> Security pass prompt

```markdown
# Security pass

Specialized security review. Primary findings are available as context — do not
re-flag issues already listed there.

Focus areas:

- **Authentication gaps** — missing auth checks on endpoints, session handling
  flaws, credential rotation issues.
- **Authorization gaps** — missing ownership checks, IDOR patterns, privilege
  escalation, tenant-boundary violations.
- **Input handling** — injection (SQL, command, template, LDAP), deserialization
  issues, XSS, SSRF, path traversal.
- **Secrets handling** — hardcoded credentials, token leakage in logs,
  insecure storage, secret sprawl.
- **Permission boundaries** — TOCTOU, race conditions on auth state, trust
  boundaries crossed, client-side-only checks.

Probe for specific security patterns the primary review's generalist framing
may have missed. If you find nothing new, say so.

## Output format

Same format as primary. Prefix each finding's id with `s` (`s1`, `s2`, ...) and
tag with `pass: security`.

## Suppression gate

Same rule as primary (suppress <75 except P0 @ 50+). Report suppressed count in
a `Suppressed findings (security):` line.

## Primary findings (for context; do NOT re-flag)

<!-- PRIMARY_FINDINGS_BLOCK -->
```

---

## <!-- PERFORMANCE_TEMPLATE --> Performance pass prompt

```markdown
# Performance pass

Specialized performance review.

Focus areas:

- **Database** — N+1 queries, missing indexes, large scans, transaction scope
  too wide, lock contention.
- **Algorithmic** — O(n²) where O(n) suffices, unbounded loops, repeated
  computations of pure results, recursive calls that could memoize.
- **I/O** — sequential calls that could parallelize, sync calls in hot paths,
  missing cache, chatty protocols, large payloads.
- **Memory** — unbounded growth, reference leaks, large-object allocations in
  loops, GC-pressure patterns.
- **Concurrency** — contention, lock ordering, async-over-sync anti-patterns,
  missing backpressure.

Do not re-flag issues already in primary findings. Probe for specific
performance patterns the primary's generalist framing may have missed.

## Output format

Same format as primary. Prefix each finding's id with `p` (`p1`, `p2`, ...) and
tag with `pass: performance`.

## Suppression gate

Same rule as primary (suppress <75 except P0 @ 50+). Report suppressed count in
a `Suppressed findings (performance):` line.

## Primary findings (for context; do NOT re-flag)

<!-- PRIMARY_FINDINGS_BLOCK -->
```

---

## Fingerprint + merge rules (implementation reference)

The flowctl helper merges primary + deep findings using this fingerprint:

```
fingerprint = (normalize(file), line_bucket(line, bucket=10), slug(title[:60]))
```

- `line_bucket` groups adjacent findings on lines within 10 of each other so
  near-duplicates collapse.
- `slug` lower-cases, strips punctuation, truncates to 60 chars.
- Primary finding wins when a collision is detected (deep-pass drops).
- When a deep-pass finding shares a fingerprint with a primary finding, the
  primary's confidence is promoted one anchor step (0→25→50→75→100). 100 is
  the ceiling.

Promotions are recorded in the receipt under `cross_pass_promotions` as a list
of `{id, from, to}` entries.

## Verdict gate after merge

Recompute verdict over the **merged** set:

- Any `introduced` finding at confidence ≥ 75 (or P0 ≥ 50) → `NEEDS_WORK`.
- All `introduced` findings suppressed / promoted-out / zero → `SHIP`.
- `pre_existing` findings never flip the verdict (unchanged rule from primary).

The verdict never downgrades from the primary review's result; deep passes only
add findings or promote confidence. If primary was `SHIP`, deep passes that
introduce new `introduced` findings at blocking confidence do flip verdict to
`NEEDS_WORK` — but this is an upgrade in stringency, not a downgrade.
