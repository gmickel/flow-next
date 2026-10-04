# Plan selected review

Load this reference only when the user or autonomous defaults selected a review
mode other than `none`.

Invoke `$flow-next-plan-review` once with the spec ID and selected mode.
Plan Review owns the fix and re-review loop
([working-rules.md](../../../references/working-rules.md), Review): act on the
result it returns, and recompute validation and execution waves after any task or
dependency fix it made.
