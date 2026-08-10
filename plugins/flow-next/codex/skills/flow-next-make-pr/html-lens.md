# Make PR HTML render lens

Enabled-path reference for `workflow.md` Phase 1.5. Read this file only after
the workflow gate resolves `HTML_LENS=true`; the off, unset, and `--dry-run`
paths never load it.

The lens runs after the structured cognitive-aid phase and before Phase 2.
When a supported current v1 object exists, the lens is local-only: committing
an HTML file that embeds the current head would advance that head and
immediately stale its own authoritative input. The legacy fallback path may
still use the narrow committed-artifact mode because it makes no v1 currentness
claim.

1. **Load the disclosure reference** [`plugins/flow-next/references/html-artifacts.md`](../../references/html-artifacts.md) (relative cross-link — resolves from this skill dir in every install layout). It owns ALL design and generation rules; §5 is the PR-lens contract (read-only review instrument: masthead + dials, sticky review-progress bar, 90-second read, churn map by review intent, R-ID → evidence table, where-to-look checklist, risk register). Never duplicate its rules here; follow it top to bottom.
2. **Resolve structured input, then generate the artifact.** Before generation,
 query `flowctl pr-cognitive-aid current` with the export-time base/head
 identity. A supported `current` v1 object is the authoritative semantic input
 described by reference §5; preserve it exactly across the lens. Any other
 status uses the existing visibly labeled export/diff fallback and never
 mixes fields from the rejected/stale object.

 On `current`, write `.artifact` to a private mode-0600 temporary JSON file
 and invoke the deterministic semantic-carrier command:

 ```bash
 HTML_AID_STATUS=$(printf '%s' "$CURRENT_AID" | jq -r '.status')
 if [[ "$HTML_AID_STATUS" == "current" ]]; then
 HTML_AID_INPUT=$(mktemp "${TMPDIR:-/tmp}/flow-pr-aid.XXXXXX.json")
 chmod 600 "$HTML_AID_INPUT"
 printf '%s' "$CURRENT_AID" | jq '.artifact' > "$HTML_AID_INPUT"
 HTML_AID_CARRIER=$(mktemp "${TMPDIR:-/tmp}/flow-pr-aid.XXXXXX.html")
 chmod 600 "$HTML_AID_CARRIER"
 "$FLOWCTL" pr-cognitive-aid html-input --file "$HTML_AID_INPUT" \
 > "$HTML_AID_CARRIER"
 fi
 ```

 Embed `HTML_AID_CARRIER` verbatim in the generated document. Its
 `<script id="flow-next-pr-cognitive-aid" type="application/json">` payload is
 the executable parity surface: HTML consumers extract it and recover the
 exact validated object. Presentation markup may project those semantics but
 never replace the carrier. Remove both temporary files after generation.

 Generate at the fixed path (reference §1.3):

 ```bash
 mkdir -p ".flow/artifacts/${SPEC_ID}"
 # Host agent generates .flow/artifacts/${SPEC_ID}/pr.html per reference §5.
 ```

 Fallback inputs are `EXPORT_PAYLOAD` (R-IDs from `spec.spec_sections.acceptance_criteria`, `tasks[].satisfies[]` + `tasks[].evidence.commits[]`, `diff_summary` files/churn/modules) plus `git diff --stat "$MERGE_BASE"..HEAD` for any stat the payload lacks. **Diff-derived, never commit messages** — commit subjects/bodies are not lens input. The staleness stamp (reference §1.5, PR variant) uses HEAD **at payload-export time** — the code under review; the artifact commit below deliberately excludes itself from its own churn map.
3. **R-ID verification (warn-in-artifact, never block).** Cross-check the payload before publishing: an R-ID whose owning tasks claim evidence commits absent from the diff range, an R-ID with no owning task (`tasks_summary.undeclared_r_ids` - NOT `uncovered_r_ids`, which also contains criteria a still-open task legitimately claims; those render as claimed-not-evidenced, never as a mismatch - fn-180, #301), or evidence commits touching no files in `diff_summary.files[]` — each renders as a **visibly flagged row** in the R-ID → evidence table (red R-ID cell + `mismatch` chip + one-line reason, reference §5.5). Never block make-pr on a mismatch, never silently drop the row.
4. **Run the reference's pre-publish checklist (§8)**, including the self-containment self-check grep (§2) — it must print `OK: self-contained` before the body may link the artifact.
5. **Link mode + narrow legacy commit.** A supported current v1 lens is always
 local-only so generation cannot mutate and stale the reviewed head. The
 fallback link strategy follows the ignore status of the EXACT artifact file
 (a repo can ignore `.flow/artifacts/**`, `*.html`, or the exact path without
 the directory itself matching). Every fallback git step is failure-guarded:

 ```bash
 ARTIFACT_PATH=".flow/artifacts/${SPEC_ID}/pr.html"
 LENS_OK=true # any failure below flips this — never aborts the skill
 if [[ "$HTML_AID_STATUS" == "current" ]]; then
 LINK_MODE=local # preserve the reviewed HEAD and v1 currentness
 elif git check-ignore --no-index -q "$ARTIFACT_PATH"; then
 LINK_MODE=local # file ignored (dir, glob, or exact-path rule) → local-open guidance, never a blob link that 404s
 # --no-index honors the ignore rule even when an earlier run already committed
 # the artifact (plain check-ignore skips tracked files → would re-commit forever)
 else
 LINK_MODE=repo
 # Stage ONLY the artifact file — NEVER `git add -A` / `git add .` (the
 # working tree may carry unrelated changes that are not make-pr's concern).
 if ! git add -- "$ARTIFACT_PATH" 2>/dev/null; then
 LENS_OK=false
 elif git diff --cached --quiet -- "$ARTIFACT_PATH" 2>/dev/null; then
 : # regeneration produced byte-identical content already in HEAD — blob link already resolves; no empty commit
 elif ! git commit -m "chore(flow): pr artifact ${SPEC_ID}" -- "$ARTIFACT_PATH"; then
 LENS_OK=false
 fi
 fi
 if [[ "$LENS_OK" != "true" ]]; then
 LINK_MODE="" # no body line — a blob link is only emitted for content that landed in a commit
 echo "HTML render lens skipped: artifact stage/commit failed — PR proceeds without the body link" >&2
 fi
 ```

 The fixed-message pathspec commit (`-- "$ARTIFACT_PATH"`) rides §4.6's `git push -u origin HEAD` — by creation time the blob URL resolves on the remote branch. Dirty-tree discipline: the pathspec confines the commit to the artifact even if unrelated changes happen to be staged.
6. **Record the body line for Phase 2 (§2.1).** It becomes a fifth line of the §2.1 summary blockquote. `LINK_MODE=repo` → absolute SHA-pinned blob URL per the §2.4b artifact row:

 ```markdown
 > **Render lens:** [`.flow/artifacts/<spec-id>/pr.html`](https://github.com/<owner>/<repo>/blob/<head-sha>/.flow/artifacts/<spec-id>/pr.html) — GitHub renders committed HTML as source; open locally in a browser. Regenerable; markdown is the record.
 ```

 `LINK_MODE=local` → local-open guidance only — either
 `` > **Render lens:** `.flow/artifacts/<spec-id>/pr.html` (v1 currentness preserved — open locally in a browser; regenerable) ``
 or the existing `gitignored — open locally` variant (`.flow/artifacts/<spec-id>/pr.html` as bare inline code). `LINK_MODE` empty (`LENS_OK=false`) → no body line at all. Never emit a blob link that 404s.
7. **No Lavish — ever.** The PR lens is a read-only review instrument (reference §5): make-pr never opens a `lavish-axi` session and never polls, **interactive AND autonomous alike** — review conversation belongs to the code host. There is no Lavish snippet in this skill by design; do not import one from capture §5.10 / plan Step 8.5.
8. **Failure is non-fatal — mechanically.** The stage/commit path is already guarded by step 5's `LENS_OK` flag. Generation or checklist failure (steps 2-4, host-agent actions) takes the same route: do NOT run step 5's stage/commit at all — set `LENS_OK=false`, `LINK_MODE=""`, print ONE stderr note (`HTML render lens skipped: <reason>`), and proceed to Phase 2 — the PR is the product, the lens is an extra. Exactly one stderr note total per skipped lens. Under Ralph ALL artifact messaging routes to stderr — the `PR_URL=<url>` single-line stdout contract (§5.4) and every receipt are untouched.

## Done when

- `.flow/artifacts/<spec-id>/pr.html` exists at the fixed path, derived from the export payload + real diff (**never commit messages**), pre-publish checklist (reference §8) passed incl. the self-containment grep → `OK: self-contained`, staleness stamp present.
- Supported current v1 input, when present, remains authoritative for identity/currentness, sources, ordered groups, file membership, change/attention dimensions, file-level links, deliberate non-changes, and verification; its HTML contains the verbatim deterministic semantic carrier, remains local-only, and leaves `HEAD` unchanged. Fallback is visibly labeled and never mixed.
- R-ID verification ran: payload-vs-diff mismatches (claimed evidence outside the diff range, uncovered R-IDs, evidence touching no diff files) render as visibly flagged rows (red R-ID cell + `mismatch` chip + reason) — warn-in-artifact, never blocks make-pr.
- Ignore probe ran against the EXACT artifact file (`git check-ignore --no-index -q "$ARTIFACT_PATH"` — `--no-index` so an already-tracked artifact still honors a later ignore rule), not the directory.
- `HTML_AID_STATUS=current`: `LINK_MODE=local`, no artifact commit, and `git rev-parse HEAD` still equals the cognitive aid's `headSha`.
- Legacy fallback with `LINK_MODE=repo`: exactly one narrow pathspec commit (`chore(flow): pr artifact <spec-id>` `--` artifact file only); byte-identical regeneration makes no empty commit.
- Every git step failure-guarded via `LENS_OK` — no unguarded `git add`/`git commit` that could abort the skill under `set -e`.
- Render-lens body line recorded for §2.1 (or skipped — `LINK_MODE=""` — with one stderr note on failure).
- NO `lavish-axi` session opened and NO poll — interactive AND autonomous alike (read-only review instrument; no Lavish snippet exists in this skill).
- Failure path: generation / checklist / stage / commit failure ⇒ `LENS_OK=false`, body line skipped, exactly ONE stderr note (`HTML render lens skipped: <reason>`), phase exits cleanly into Phase 2 — PR creation proceeds. Ralph `PR_URL=<url>` stdout contract + receipts untouched.
