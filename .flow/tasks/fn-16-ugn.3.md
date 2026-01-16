# fn-16-ugn.3 Add smoke test for /flow-next:sync

## Overview

Add smoke tests to `plugins/flow-next/scripts/smoke_test.sh` to verify the `/flow-next:sync` command works correctly.

## Context

- Existing smoke test: `plugins/flow-next/scripts/smoke_test.sh`
- The test doesn't run Claude - it tests flowctl CLI commands and file structure
- For skill testing, we verify files exist and have correct structure

## Tests to Add

Add a new section `--- sync command files ---` to smoke_test.sh:

### Test 1: Command stub exists
```bash
if [[ -f "$PLUGIN_ROOT/commands/flow-next/sync.md" ]]; then
  echo -e "${GREEN}✓${NC} sync command stub exists"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync command stub missing"
  FAIL=$((FAIL + 1))
fi
```

### Test 2: Skill file exists
```bash
if [[ -f "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md" ]]; then
  echo -e "${GREEN}✓${NC} sync skill exists"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill missing"
  FAIL=$((FAIL + 1))
fi
```

### Test 3: Command invokes skill
```bash
if grep -q "flow-next-sync" "$PLUGIN_ROOT/commands/flow-next/sync.md"; then
  echo -e "${GREEN}✓${NC} sync command invokes skill"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync command doesn't reference skill"
  FAIL=$((FAIL + 1))
fi
```

### Test 4: Skill has correct frontmatter
```bash
if grep -q "name: flow-next-sync" "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md"; then
  echo -e "${GREEN}✓${NC} sync skill has correct name"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill missing name frontmatter"
  FAIL=$((FAIL + 1))
fi
```

### Test 5: Skill mentions plan-sync agent
```bash
if grep -q "plan-sync" "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md"; then
  echo -e "${GREEN}✓${NC} sync skill references plan-sync agent"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill doesn't reference plan-sync agent"
  FAIL=$((FAIL + 1))
fi
```

### Test 6: Skill supports dry-run
```bash
if grep -qi "dry.run\|dry-run\|DRY_RUN" "$PLUGIN_ROOT/skills/flow-next-sync/SKILL.md"; then
  echo -e "${GREEN}✓${NC} sync skill supports dry-run"
  PASS=$((PASS + 1))
else
  echo -e "${RED}✗${NC} sync skill missing dry-run support"
  FAIL=$((FAIL + 1))
fi
```

## Location in smoke_test.sh

Add after the existing test sections, before the final results summary.

## Acceptance

- [ ] 6 new tests added to smoke_test.sh
- [ ] Tests verify command stub exists and references skill
- [ ] Tests verify skill exists with correct frontmatter
- [ ] Tests verify dry-run mentioned in skill
- [ ] All tests pass when run: `plugins/flow-next/scripts/smoke_test.sh`

## Done summary
Added 6 smoke tests verifying /flow-next:sync command stub and skill files exist with correct content (name frontmatter, plan-sync reference, dry-run support).
## Evidence
- Commits: 491d8593fd3eaedda39f05438e860b34607f5754
- Tests: plugins/flow-next/scripts/smoke_test.sh
- PRs:
## References

- Smoke test: `plugins/flow-next/scripts/smoke_test.sh`
- Command stub: `plugins/flow-next/commands/flow-next/sync.md`
- Skill: `plugins/flow-next/skills/flow-next-sync/SKILL.md`
