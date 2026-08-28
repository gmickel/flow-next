# Conduct checklist — /flow-next:audit

A correct run walks `.flow/memory/` plus the glossary, verifies each entry against current code, and decides Keep / Update / Consolidate / Replace / Delete / Harden per entry.

- [ ] The full audit report is printed to stdout as markdown — the counts block (Scanned / Kept / Updated / Consolidated / Replaced / Deleted / Hardened / Marked stale / Skipped legacy) plus per-entry detail and the Glossary section. A run that summarizes internally and emits a one-liner has broken this.
- [ ] Legacy flat files at the memory root and any `_*` directory are skipped with a counted warning that points at `/flow-next:memory-migrate`, not audited in place.
- [ ] Under `mode:autofix`, Harden candidates appear only under Recommended — with gate type, draft artifact, evidence, and the `--gate-ref` that would be recorded — and no gate artifact is written and no entry is demoted.
- [ ] `flowctl memory mark-hardened` appears only after the transcript shows the gate verified live. A failed verification names the reason, leaves the entry active, and is reported as a failed graduation.
- [ ] No entry file is removed on Harden, and no superseded decision entry is `git rm`'d — a decision Replace writes the successor and edits the old entry to `decision_status: superseded` with `superseded_by`.
- [ ] Genuinely ambiguous classifications in autofix reach `flowctl memory mark-stale <id> --reason "..."` rather than a guessed action; borderline entries are never deleted on that track.
- [ ] Lessons arriving at the store pass the three intake filters: a mechanizable lesson surfaces as a gate proposal rather than a prose entry, a lesson banks only when it routes to a file, command, or decision the transcript actually touched, and a rule that existed but did not fire gets a retrieval fix (description, placement, module/tags), not a rewrite. A run that banks a mechanizable or evidence-free lesson as prose, or rewrites an unfired-but-correct rule, has broken this.
