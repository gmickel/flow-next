# Live QA section — `## Live QA` (fn-72)

Enabled-path reference for `workflow.md` §2.11b. Read this file only when the §2.11b
gate printed its sentinel (a `qa_verdict` receipt exists for this spec, or the probe
errored). With no receipt the section is omitted entirely and this file is never read.

Render `## Live QA` **only when** the QA receipt exists at `.flow/review-receipts/qa-<spec-id>.json` (the `/flow-next:qa` skill's default committed path; written when QA ran — via the opt-in pilot stage or a manual `/flow-next:qa` pass). With no receipt the section is omitted entirely (the §2.6 rule — most specs have no QA pass, so this is the common case and the body is byte-identical to today). This is the **R7 surfacing owner**: the QA stage advances even on `NEEDS_WORK`, so the findings reach a human only if make-pr renders them here.

**Read the receipt (guarded — a malformed/absent file omits the section, never aborts the body):**

```bash
QA_RECEIPT="$REPO_ROOT/.flow/review-receipts/qa-$SPEC_ID.json"
QA_PRESENT=0
if [ -f "$QA_RECEIPT" ] && jq -e . "$QA_RECEIPT" >/dev/null 2>&1; then
  QA_PRESENT=1
  QA_OUTCOME="$(jq -r '.qa_outcome // "unknown"' "$QA_RECEIPT")"
  QA_HEAD_SHA="$(jq -r '.head_sha // ""' "$QA_RECEIPT")"
  QA_BLOCKED_REASON="$(jq -r '.blocked_reason // ""' "$QA_RECEIPT")"
  QA_NA_REASON="$(jq -r '.na_reason // ""' "$QA_RECEIPT")"
  QA_COV_COVERED="$(jq -r '.rid_coverage.covered // "?"' "$QA_RECEIPT")"
  QA_COV_TOTAL="$(jq -r '.rid_coverage.total // "?"' "$QA_RECEIPT")"
fi

# Freshness — the receipt carries head_sha for exactly this reason. The QA receipt is
# keyed to the CODE head; Phase 1.5 may have already committed the pr.html artifact,
# which advanced HEAD — so compare against the PRE-ARTIFACT head (HEAD^ when HEAD is the
# artifact commit), never the post-artifact HEAD, or a fresh pass reads as stale.
# The receipt's head_sha is the head AT QA TIME. Bookkeeping commits land ABOVE the code
# head AFTER QA — pilot's `chore(flow): qa verdict <spec>` receipt commit, then Phase 1.5's
# `chore(flow): pr artifact <spec>`. So the branch tip is NOT the code head. Accept the
# receipt if its head_sha matches the tip OR any commit reached by peeling those leading
# bookkeeping commits (the code head and everything above it). Fail CLOSED on empty.
QA_FRESH_OK=0
if [ "$QA_PRESENT" = "1" ] && [ -n "$QA_HEAD_SHA" ]; then
  _s="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "")"
  while [ -n "$_s" ]; do
    [ "$_s" = "$QA_HEAD_SHA" ] && { QA_FRESH_OK=1; break; }
    git -C "$REPO_ROOT" log -1 --format='%s' "$_s" 2>/dev/null \
      | grep -qE '^chore\(flow\): (qa verdict|pr artifact) ' || break
    _s="$(git -C "$REPO_ROOT" rev-parse "$_s^" 2>/dev/null || echo "")"
  done
fi
[ "$QA_FRESH_OK" = 1 ] || QA_PRESENT=0   # stale or empty head_sha → omit the section
```

Read directly with `jq` (do NOT compose any free-form receipt field into shell-built JSON — surface the values as rendered markdown only). The receipt fields are exactly those task .1 added (`qa_outcome`, `head_sha`, `branch`, `rid_coverage`, `open_p0p1` as **objects**, plus the scoped `blocked_reason` / `na_reason`).

**Section body (when `QA_PRESENT=1`):**

```markdown
## Live QA

> **Outcome:** <qa_outcome> · **Ran against:** `<head_sha short>` · **R-ID coverage:** <covered>/<total>

<conditional outcome line — see field rules>

<open P0/P1 list — one checkbox bullet per open_p0p1[] object, only when the array is non-empty>
```

Field rules:

- **`<qa_outcome>`** — verbatim from `qa_outcome` (one of `SHIP` / `NEEDS_WORK` / `NA` / `BLOCKED`). Render the four-outcome value, **NOT** the Ralph-guard `verdict` projection (a `BLOCKED` receipt projects `verdict=NEEDS_WORK`; surfacing `verdict` here would mislabel "couldn't verify" as "found problems"). Read `qa_outcome`, never `verdict`.
- **`<head_sha short>`** — first 8 chars of `head_sha`; omit the "Ran against" clause if empty.
- **R-ID coverage** — `rid_coverage.covered`/`rid_coverage.total`; omit the clause if either is `?`.
- **Conditional outcome line:**
  - `SHIP` → `> Live QA passed: all derived scenarios passed on the running app with captured evidence; zero open P0/P1.`
  - `NA` → `> Live QA not applicable: <na_reason>` (no driveable user-visible AC — the common backend/CLI case).
  - `BLOCKED` → `> Live QA could not run: <blocked_reason>` (no local app reachable / no driver — **not** a failure; the augmenting pass was skipped).
  - `NEEDS_WORK` → `> Live QA found issues — see the open P0/P1 list below. (Advisory: this does not block merge; the human reviewer + land gate decide.)`
- **Open P0/P1 list** — only when `open_p0p1[]` is non-empty (typically the `NEEDS_WORK` outcome). One checkbox bullet per object, using its structured fields (`severity` ∈ `{P0,P1}`, `reason` one-line symptom, `file` surface/route, `id` finding id):

  ```markdown
  - [ ] **<severity>** — <reason> (`<file>`) — QA finding `<id>`
  ```

  Render the objects' fields verbatim as markdown text; never invent or paraphrase. If `open_p0p1` is empty, emit no list (a `SHIP`/`NA`/`BLOCKED` receipt has none).

**What this section MUST NOT do:**

- MUST NOT mark the PR blocked or change its draft/ready state on a `NEEDS_WORK` outcome — QA is advisory (fn-72 R7). It surfaces findings; merge stays the human's + land's decision.
- MUST NOT read `verdict` in place of `qa_outcome` — the projection collapses `BLOCKED` into `NEEDS_WORK`.
- MUST NOT inline free-form receipt text into any shell-composed JSON — render it as markdown only (the receipt was written safely by the QA skill; make-pr only *reads* it).
- MUST NOT fabricate a Live QA section when no receipt is present — absence of the receipt means QA never ran; the section is omitted (no sentinel line).

**Section purpose framing** — this is the live-app verification signal a static-review PR never carries: "does the running product actually work?" The QA stage advances the build loop on every outcome (including `NEEDS_WORK`), so this section is the only place a `NEEDS_WORK` live-QA result reaches the human reviewer before merge. It complements (never replaces) CI/staging/manual QA.

## Done when

- `## Live QA` renders the `qa_verdict` receipt summary — `qa_outcome` (NOT the `verdict` projection) + the persisted `open_p0p1` objects + BLOCKED/NA reason + `rid_coverage` — when the receipt is present, parses, and passes the freshness peel. Advisory only: never changes draft/ready state.
- Stale, unparseable, or empty-`head_sha` receipt ⇒ section omitted, body otherwise unchanged, no sentinel line in the body.
