# capture — `--rewrite <spec-id>` mode (loaded on demand)

> Loaded ONLY when `REWRITE_TARGET` is non-empty (the invocation carried `--rewrite <spec-id>`).
> A fresh capture never reads this file. Read it once at Phase 0.6 — it governs the rewrite behavior
> in Phases 0, 4, 5 and 6.

Contents:

- [0.6 — Target validation](#06--target-validation-r8)
- [Phase 4 — rewrite read-back additions](#phase-4--rewrite-read-back-additions)
- [5.3 — Rewrite branch](#53--rewrite-branch)
- [Phase 6 — rewrite footer](#phase-6--rewrite-footer)

---

## 0.6 — Target validation (R8)

- Validate the target exists **and is a spec** (not a task — `flowctl show` accepts both, but capture only writes specs to spec IDs):

  ```bash
  out=$("$FLOWCTL" show "$REWRITE_TARGET" --json) || { echo "Error: --rewrite target $REWRITE_TARGET does not exist. Drop --rewrite to create a new spec, or pick an existing spec id." >&2; exit 2; }
  if echo "$out" | jq -e '.tasks' >/dev/null 2>&1; then
    : # spec — has .tasks array
  else
    echo "Error: --rewrite target $REWRITE_TARGET is a task, not a spec. Pass a spec id (fn-N-slug, no .M suffix)." >&2
    exit 2
  fi
  ```

- If the target is missing or is a task, exit 2 with the appropriate error message above.
- Read the existing spec. Phase 4 read-back will show a diff (existing → proposed) before write.

---

## Phase 4 — rewrite read-back additions

The print-then-ask contract (workflow.md §4.1/§4.2) gains one mandatory element in rewrite mode:

- **Print the existing → proposed diff** (unified style; changed sections in full) as ordinary markdown in the same message as the full draft, or in a second message immediately after it — **never only inside the ask**.
- The short ask's one-line pointer reads `Full draft + rewrite diff printed above.`
- Summary-payload item 5 — **rewrite-mode pointer** — one short clause, e.g. `Rewrite diff printed above.` (the full diff is already in the ordinary message; never paste it into the ask).
- Confidence tier `[your-call]` covers rewrite-mode with substantive divergence from the existing spec.
- **Forbidden:** never edit a `--rewrite` target without printing the diff as ordinary markdown before the short ask. The diff is non-optional in rewrite mode.

Mark-ready consent on a rewrite is target-aware — see `references/mark-ready.md` when that gate fires (a rewrite offers the question only when the target itself was ready before the rewrite; an unrelated ready spec never prompts on a draft rewrite).

---

## 5.3 — Rewrite branch

When `REWRITE_TARGET` is set:

```bash
SPEC_ID="$REWRITE_TARGET"

# Skip spec create — the spec already exists. Overwrite the spec body from the
# §4.1 draft file (literal path typed verbatim, per the path-persistence rule).
"$FLOWCTL" spec set-plan "$SPEC_ID" --file "${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<suffix>.md" --json

# Readiness reset — runs AFTER set-plan: a failed rewrite must not downgrade a
# blessed spec (Codex review, PR #170 P2). A rewrite is a full re-authoring; any
# prior blessing no longer applies once the new body lands. Unconditional call:
# the toggle is idempotent (fn-58.1) — a never-ready spec is a silent no-op (no
# write, no updated_at bump), so this does NOT turn every rewritten draft into a
# readiness-adopter. Announce, never confirm — --rewrite already carried the
# consent.
READY_RESET=$("$FLOWCTL" spec unready "$SPEC_ID" --json | jq -r '.changed // false')

# Run anchor for Phase 6's sync check — REQUIRED on the rewrite path: created_at
# is the spec's ORIGINAL creation time here (an earlier run), so an old
# `event: capture` receipt would false-OK the check and the retro-fire would
# never fire (Codex review, PR #169 P2).
date -u +%Y-%m-%dT%H:%M:%SZ > "${TMPDIR:-/tmp}/flow-capture-anchor-${SPEC_ID}"
```

When `READY_RESET=true` (the spec WAS ready), Phase 6's rewrite footer carries a one-line reset announcement. When `false`, no readiness line is printed — never announce a reset that didn't happen (zero noise for never-ready specs).

§5.4–§5.10 (branch name, tracker sync, glossary, readiness, HTML lens) run exactly as on the new-spec branch.

---

## Phase 6 — rewrite footer

If `REWRITE_TARGET` was set, the footer prefix changes (the `Tracker sync:` line stays mandatory):

```text
Spec rewritten at .flow/specs/<SPEC_ID>.md.
Readiness: spec rewritten — readiness reset to draft (re-bless when ready)
Tracker sync: <same four states>

Recommended next: /flow-next:<stage> <SPEC_ID> — <one-clause reason>; <named alternative when it applies>

Next:
  /flow-next:plan <SPEC_ID>      → re-plan tasks (existing tasks under the spec
                                    may need /flow-next:sync to align)
  /flow-next:interview <SPEC_ID> → refine via Q&A
  /flow-next:visual <SPEC_ID>    → compact visual digest — review the spec at a glance
```

The `Recommended next:` line follows the base-footer rule (workflow.md §Phase 6) and is MANDATORY here too — a rewrite is precisely when the route may change, so re-judge the rewritten spec's risk and remaining unknowns (readiness state, open `[inferred]` criteria, Parked unknowns) against the smallest-sufficient rule in [docs/pipeline-variations.md](../../../../docs/pipeline-variations.md). Same legal targets (`/flow-next:interview`, `/flow-next:plan` optionally noting `work` may suffice, `/flow-next:guide` on genuinely conflicting signals); informational only — never a plain-text numbered prompt.

The `Readiness:` announcement line appears ONLY when §5.3's reset actually changed the flag (`READY_RESET=true`). Never-ready specs print no readiness line — an announcement is not a confirmation prompt, and it must not claim a reset that didn't happen.
