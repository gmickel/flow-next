# Plan HTML render lens

Load this reference only after Step 8.5 derives
`artifacts.html.enabled == true` from the Step 0 config snapshot.

1. **Load the disclosure reference** [`plugins/flow-next/references/html-artifacts.md`](../../../references/html-artifacts.md). It owns all design and generation rules: hard rules, design contract, spec-lens content, DAG discipline, Lavish flow, and the pre-publish checklist. Follow it top to bottom.
2. **Regenerate the artifact** at the same fixed path Capture uses (disclosure reference §1.3). Tasks now exist, so render the plan layer too: dependency DAG with critical path, R-ID → task coverage matrix, and plan dials.

   ```bash
   mkdir -p ".flow/artifacts/<spec-id>"
   # Host agent regenerates .flow/artifacts/<spec-id>/spec.html per the reference.
   ```
3. **Late mutation:** if anything after generation mutates tasks in this Plan session (review fixes or reopened go-deeper/simplify), regenerate at the same path before final output. Never create a second artifact.
4. **Update the artifact link marker** in the spec per disclosure reference §1.4. Replace `<!-- flow-next:artifact-link -->` in place, or insert it once after H1 when absent. Choose link mode from the exact artifact path:

   ```bash
   if git check-ignore --no-index -q ".flow/artifacts/<spec-id>/spec.html"; then
     LINK_MODE=local
   else
     LINK_MODE=repo
   fi
   MARKER_COUNT=$(grep -c 'flow-next:artifact-link' ".flow/specs/<spec-id>.md" || true)
   if [ "${MARKER_COUNT:-0}" -ne 1 ]; then
     echo "warn: artifact link line check failed (${MARKER_COUNT:-0} markers in .flow/specs/<spec-id>.md) — link needs manual fix" >&2
   fi
   ```

   `--no-index` ensures a tracked artifact still honors a later ignore rule.
5. **Run the disclosure reference's pre-publish checklist (§8)**, including the self-containment grep (§2). It must print `OK: self-contained` before output may claim the artifact.
6. **Lavish is interactive-only.** The guard must contain both open and poll:

   ```bash
   LAVISH_OK=true
   [[ "${AUTONOMOUS:-0}" == "1" || -n "${FLOW_AUTONOMOUS:-}" || -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]] && LAVISH_OK=false
   if [[ "$LAVISH_OK" == "true" ]] && command -v lavish-axi >/dev/null 2>&1; then
     lavish-axi "$(pwd)/.flow/artifacts/<spec-id>/spec.html"
     # ...then poll in the background via `lavish-axi poll`, only inside this guard.
   fi
   ```

   Each drained annotation edits spec/task markdown, never HTML, then regenerates
   the same lens. Missing `lavish-axi` is silent. Any non-interactive marker in
   the family disables open/poll and permits at most one stderr line about
   pending prompts.
7. Append `Artifact: .flow/artifacts/<spec-id>/spec.html (render lens — regenerable; markdown is the record)` to the Plan summary.

Best-effort: generation failure is non-fatal. Skip the link update, print one
stderr note, and never block planning; markdown remains the record.
