# Plan selected review

Load this reference only when the user or autonomous defaults selected a review
mode other than `none`.

1. Invoke `/flow-next:plan-review` with the spec ID and selected mode. An
 `export` choice must use Plan Review's export mode; do not substitute the
 configured backend.
2. If review returns `Needs Work` or `Major Rethink`:
 - Re-anchor every iteration:
 ```bash
 $FLOWCTL show <spec-id> --json
 $FLOWCTL cat <spec-id>
 ```
 - Immediately fix the issues; the user already consented.
 - Re-run `/flow-next:plan-review`.
3. Repeat until review returns `Ship`.

No human gates here: the review-fix-review loop is fully automated. Re-anchoring
each iteration protects the fix pass from context loss. Recompute validation
and execution waves after any task or dependency fix.
