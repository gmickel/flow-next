# capture — HTML render lens (loaded on demand, opt-in)

> Loaded ONLY when `artifacts.html.enabled` is true. The default capture run reads the one-line
> config gate (in workflow.md §5.10) and, when off, never touches this file — so its ~57 lines are
> not part of the always-loaded prompt.

### 5.10 — HTML render lens (opt-in) — spec artifact + link line

**Gated on `artifacts.html.enabled` — this check is the ONLY addition when the mode is off.** Runs last in Phase 5 (after 5.7–5.9 have settled the spec body and metadata), so the lens renders the final state.

```bash
HTML_LENS=$("$FLOWCTL" config get artifacts.html.enabled --json | jq -r 'if .value == true then "true" else "false" end')
```

When `HTML_LENS != true` (off or unset): **skip this entire section.** Load no reference file, write no artifact, open no session, print no artifact-related output — the gate read above is the only cost.

When `HTML_LENS = true`:

1. **Load the disclosure reference** [`plugins/flow-next/references/html-artifacts.md`](../../references/html-artifacts.md) (relative cross-link — resolves from this skill dir in every install layout, same shape as the spec-template link). It owns ALL design and generation rules — hard rules, design contract, spec-lens content, DAG discipline, Lavish flow, pre-publish checklist. Never duplicate its rules here; follow it top to bottom.
2. **Generate the artifact** at the fixed path (reference §1.3):

   ```bash
   mkdir -p ".flow/artifacts/${SPEC_ID}"
   # Host agent generates .flow/artifacts/${SPEC_ID}/spec.html per the reference.
   ```

   ONE pathway, state-dependent (reference §4): a fresh capture renders the spec-only view (no tasks exist yet); a `--rewrite` of an already-planned spec (tasks exist under it) renders the plan layer too — same generator, same path.
3. **Update the artifact link line in the spec markdown** per reference §1.4: find the `<!-- flow-next:artifact-link -->` marker and replace that whole line in place; if absent, insert once after the H1 title. Link target follows ignore status (reference §4):

   ```bash
   if git check-ignore --no-index -q ".flow/artifacts/${SPEC_ID}/spec.html"; then
     LINK_MODE=local   # file ignored (dir, glob, or exact-path rule) → local-open guidance, never a blob link that 404s
     # --no-index: an already-tracked artifact still honors a later ignore rule
   else
     LINK_MODE=repo    # tracked → repo-relative link
   fi
   # Idempotency check — exactly one marker line after EVERY run. Non-fatal
   # (best-effort contract below): warn and continue, never abort the capture.
   MARKER_COUNT=$(grep -c 'flow-next:artifact-link' ".flow/specs/${SPEC_ID}.md" || true)
   if [ "${MARKER_COUNT:-0}" -ne 1 ]; then
     echo "warn: artifact link line check failed (${MARKER_COUNT:-0} markers in .flow/specs/${SPEC_ID}.md) — link needs manual fix" >&2
   fi
   ```
4. **Run the reference's pre-publish checklist (§8)**, including the self-containment self-check grep (§2) — it must print `OK: self-contained` before the footer may claim the artifact.
5. **Lavish session — interactive runs only** (reference §7). The guard is in the snippet, not just prose — open and poll sit INSIDE it:

   ```bash
   LAVISH_OK=true
   [[ "${MODE:-interactive}" != "interactive" ]] && LAVISH_OK=false   # MODE from SKILL.md mode-detection — autofix never opens
   [[ -n "${FLOW_AUTONOMOUS:-}" || -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]] && LAVISH_OK=false
   if [[ "$LAVISH_OK" == "true" ]] && command -v lavish-axi >/dev/null 2>&1; then
     lavish-axi "$(pwd)/.flow/artifacts/${SPEC_ID}/spec.html"   # absolute path — sessions key on it
     # ...then poll for feedback in the background via `lavish-axi poll` — ONLY inside this guard
   fi
   ```

   Each drained annotation maps to an edit of the spec markdown (never the HTML), then the lens regenerates at the same path. `lavish-axi` absent → plain artifact, zero mention of Lavish, never an error.

   **Autofix / non-interactive runs generate only** (`mode:autofix`, or any non-interactive marker — `FLOW_AUTONOMOUS=1`, `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH`; capture is Ralph-blocked anyway, so autofix is the live case; treat the marker *family* as the gate, not a rigid var list): `LAVISH_OK=false` — never open a session, never poll; at most one stderr line noting pending prompts.
6. **Record the footer line for Phase 6:** `Artifact: .flow/artifacts/<SPEC_ID>/spec.html (render lens — regenerable; markdown is the record)`.

Best-effort: artifact generation failure is non-fatal — skip the link line, print one stderr note, never block the capture (the spec is already on disk; markdown is the record).
