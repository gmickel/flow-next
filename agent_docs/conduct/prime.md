# Conduct checklist — /flow-next:prime

A correct run classifies the repo, scans the eight pillars, verifies that the commands actually run, and leads with a verdict plus ranked next actions — offering fixes for agent readiness only.

- [ ] The report leads with the verdict headline — classification line, operability tier, hard-gate status, top-5 ranked next actions — and the maturity level sits below the scores table as secondary metadata.
- [ ] Scored criteria rest on executed, non-mutating probes rather than file existence. A "build passes" row with no command actually run in the transcript has broken this.
- [ ] `--classify-only` prints the classification block and exits: no scout dispatch, no verification, no report body, no remediation, and no other reference loaded.
- [ ] Fixes are offered for Pillars 1-5 only; Pillars 6-8 appear as informational findings with no remediation offer attached.
- [ ] Consent is collected through the blocking-question tool before existing files change, and `--fix-all` still stops at destructive overwrites, harness and structural artifacts, anything outside `ROOT`, and the glossary read-back gate.
- [ ] A `ROOT` other than the cwd is threaded through the classification probes, the Phase 2 verification commands, and every scout prompt, rather than silently assessing the current directory.
