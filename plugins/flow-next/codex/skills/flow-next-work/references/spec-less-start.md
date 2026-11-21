# Spec file and idea-text starts (gated reference)

> Read from phases.md Phase 1 only when the input is kind 4 (spec file) or 5 (idea text).

**Spec file start (.md path that exists)**:
1. Check file exists: `test -f "<path>"` — if not, treat as idea text
2. Initialize if needed: `[ -d .flow ] || $FLOWCTL init --json`
3. Read file and extract title from first `# Heading` or use filename
4. Create spec — mint gate (tracker-first vs flow-first): [spec-id-mint.md](spec-id-mint.md), read only when minting. Take the ONE root config snapshot the gate reads (one config read, never a per-leaf `config get tracker.specIds`; re-type the literal path, bash vars die across prompt turns):

   ```bash
   WORK_CFG="${TMPDIR:-/tmp}/flow-work-config-<suffix>.json"
   $FLOWCTL config get --json > "$WORK_CFG" 2>/dev/null || printf '{"key":null,"value":{}}' > "$WORK_CFG"
   ```

5. Set spec from file: `$FLOWCTL spec set-plan <spec-id> --file <path> --json`
6. Create single task: `$FLOWCTL task create --spec <spec-id> --title "Implement <title>" --json`
7. Continue with spec-id

**Spec-less start (idea text)**:
1. Initialize if needed: `[ -d .flow ] || $FLOWCTL init --json`
2. Create spec — run the **same tracker-first gate as Spec file start above**, verbatim, with `<idea>` as the title. Do not restate it here; that block is the single source.
3. Create single task: `$FLOWCTL task create --spec <spec-id> --title "Implement <idea>" --json`
4. Continue with spec-id
