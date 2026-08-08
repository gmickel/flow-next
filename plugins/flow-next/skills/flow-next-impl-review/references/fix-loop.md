# NEEDS_WORK fix-loop procedure (INTERNAL — do not exit to Ralph)

Read this only when the delivered verdict is `NEEDS_WORK`. A SHIP run never
needs it; `MAJOR_RETHINK` escalates as `BLOCKED: DESIGN_CONFLICT` and never
enters this loop (see [../SKILL.md](../SKILL.md) § Fix Loop for the verdict
contract, the iteration cap, and the two anti-patterns — those stay in force
here).

**CRITICAL: Do NOT ask user for confirmation. Automatically fix ALL valid issues and re-review — our goal is production-grade world-class software and architecture. Never use AskUserQuestion in this loop.**

Loop internally until SHIP or the iteration cap:

0. **Deep-pass phase (only if `DEEP=true`)** — see [../optional-phases.md](../optional-phases.md) § Deep-Pass Phase.
   - After primary review completes (any verdict) and before validator,
     run each selected pass via
     `$FLOWCTL <backend> deep-pass --pass <name> --receipt ... --primary-findings ...`.
   - Passes merge into receipt via fingerprint dedup + cross-pass promotion
     (autonomy markers only; interactive returns host_judges JSON, receipt untouched - fn-113).
   - Deep may upgrade `SHIP → NEEDS_WORK` if it surfaces new blocking findings;
     it never downgrades `NEEDS_WORK → SHIP`.
1. **Validator pass (only if `VALIDATE=true`)** — see [../optional-phases.md](../optional-phases.md) § Validator Pass.
   - Extract findings JSON-lines, dispatch `$FLOWCTL <backend> validate --findings-file ... --receipt ...`
   - If all findings drop → verdict upgrades to SHIP automatically (exit fix loop;
     autonomy markers only - interactive returns host_judges JSON and you judge survivors, fn-113)
   - Else → only surviving (kept) findings enter the fix loop in step 2
2. **Interactive walkthrough (only if `INTERACTIVE=true` AND verdict still NEEDS_WORK)** — see [../walkthrough.md](../walkthrough.md).
   - For each surviving finding, ask user via platform blocking question tool: Apply / Defer / Skip / Acknowledge / LFG-rest.
   - Deferred findings appended to `.flow/review-deferred/<branch-slug>.md`.
   - Skip / Acknowledge are no-ops beyond receipt logging.
   - Apply list restricts the fix loop below to just those findings.
   - Receipt gains `walkthrough: {applied, deferred, skipped, acknowledged}`.
3. **Parse issues** from reviewer feedback (Critical → Major → Minor)
4. **Fix code** and run tests/lints
5. **Commit fixes** (mandatory before re-review; RP backend uses the snapshot-scoped staging in [../workflow-rp.md](../workflow-rp.md) § Fix Loop (RP) — never blanket-stage with `git add --all`)
6. **Re-review**:
   - **Codex**: Re-run `flowctl codex impl-review` (receipt enables context)
   - **Copilot**: Re-run `flowctl copilot impl-review` (receipt enables context; must be `mode == "copilot"` to resume)
   - **Cursor**: Re-run `flowctl cursor impl-review` (receipt enables context; must be `mode == "cursor"` to resume)
   - **Host**: Continue through [../workflow-host.md](../workflow-host.md)'s selected
     re-review path.
   - **RP Classic**: `$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file <literal re-review path from workflow-rp.md's fix loop>` (NO `--new-chat`; stdout redirected to the same literal response file, Read once)
   - **RepoPrompt CE**: `$FLOWCTL rp chat-send --window "$W" --context-id "$T" --chat-id "$CHAT_ID" --mode review --message-file <literal re-review path>` (`T` is the canonical context binding, not visible-tab projection; NO `--tab`; same response-file rule)
7. **Repeat** until `<verdict>SHIP</verdict>` — or the MAX ITERATIONS cap breaks the loop (escalate with surviving findings)

**CRITICAL**: For RP, re-reviews must stay in the SAME chat so reviewer has context. Only use `--new-chat` on the FIRST review.
