---
satisfies: [R4, R17]
---

## Description

Automated test that fails if any DDD terminology ("ubiquitous language", "bounded context", "domain expert", "aggregate root", or equivalent) appears in skill prose, agent definitions, flowctl Python source, or user-facing slash command files. Also greps for meta-file references (`GLOSSARY-MAP.md`, `CONTEXT-MAP.md`) per R4 cross-coverage.

**Two-tier check** to mirror the existing `AskUserQuestion` / `ToolSearch` split:
- `ci_test.sh` greps **canonical** files (skills/, agents/, commands/, flowctl.py)
- `scripts/sync-codex.sh` validation block greps the **Codex mirror** (`plugins/flow-next/codex/`)

**Size:** S
**Files:** `plugins/flow-next/scripts/ci_test.sh`, `scripts/sync-codex.sh`

## Approach

### Part 1 — `ci_test.sh` (canonical scan)

Add a test block (placement: near existing memory or smoke-test sections):

```bash
# R17: no DDD jargon in canonical user-facing prose
HITS=$(grep -RnE 'ubiquitous language|bounded context|domain expert|aggregate root' \
  plugins/flow-next/skills \
  plugins/flow-next/scripts/flowctl.py \
  plugins/flow-next/agents \
  plugins/flow-next/commands 2>/dev/null || true)
if [[ -n "$HITS" ]]; then
  echo "FAIL: DDD jargon detected in canonical:"; echo "$HITS"; exit 1
fi

# R4: no meta-file precedent leaks into canonical prose
META_HITS=$(grep -RnE 'GLOSSARY-MAP\.md|CONTEXT-MAP\.md' \
  plugins/flow-next/skills \
  plugins/flow-next/scripts/flowctl.py \
  plugins/flow-next/agents \
  plugins/flow-next/commands 2>/dev/null || true)
if [[ -n "$META_HITS" ]]; then
  echo "FAIL: meta-file references detected in canonical:"; echo "$META_HITS"; exit 1
fi
```

Match existing `ci_test.sh` test-block style (`set -euo pipefail`, fail-on-hit pattern).

### Part 2 — `scripts/sync-codex.sh` (mirror scan)

Extend the validation block at `scripts/sync-codex.sh:760-770` (alongside the existing `AskUserQuestion` / `ToolSearch` check) with:

```bash
# Check no DDD terminology in codex mirror prose. Canonical clean +
# mechanical rewrite should keep mirror clean, but a derived artifact
# deserves its own validation.
ddd_refs=$( { grep -rE 'ubiquitous language|bounded context|domain expert|aggregate root' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$ddd_refs" -gt 0 ]; then
  echo -e "  ${RED}✗${NC} $ddd_refs DDD terminology refs in codex mirror — clean canonical first"
  fail=1
fi

# R4 mirror cross-coverage
meta_refs=$( { grep -rE 'GLOSSARY-MAP\.md|CONTEXT-MAP\.md' "$CODEX_DIR/skills/" "$CODEX_DIR/agents/" 2>/dev/null || true; } | { grep -v '/templates/' || true; } | wc -l | tr -d ' ')
if [ "$meta_refs" -gt 0 ]; then
  echo -e "  ${RED}✗${NC} $meta_refs meta-file refs in codex mirror"
  fail=1
fi
```

T3-T6 already mandate `scripts/sync-codex.sh runs clean` in their acceptance — extending the script's validation is in scope for this task because the validation block is shared infrastructure, not skill-specific prose.

### Compatibility note

The grep guard runs in <1s per scan. T7 must ship AFTER T3 (skill prose changes) so the canonical is clean by the time the guard runs. T7 depends on T3 already.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/ci_test.sh` — existing test structure (insertion point)
- `scripts/sync-codex.sh:760-770` — validation block (existing `AskUserQuestion` / `ToolSearch` checks; new DDD/meta checks land alongside)

**Optional:**
- All skill prose files modified by T3-T6 (verify no DDD jargon before adding the guards)

## Acceptance

- [ ] `ci_test.sh` includes DDD-terminology grep guard (canonical scan); passes on current codebase after T3-T6 ship
- [ ] `scripts/sync-codex.sh` validation block includes DDD-terminology grep guard (Codex mirror scan); passes after sync runs
- [ ] Both guards also catch meta-file references (`GLOSSARY-MAP.md`, `CONTEXT-MAP.md`) per R4
- [ ] Failure messages list offending files + lines (canonical) or count + remediation hint (mirror)
- [ ] Each guard runs in <2s (trivially — pure grep on a small file set)
- [ ] CI passes after this task lands (entire epic-touched canonical + mirror is clean)

## Done summary

## Evidence
