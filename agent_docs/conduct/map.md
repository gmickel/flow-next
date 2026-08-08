# Conduct checklist — /flow-next:map

A correct run wraps `clawpatch map` as a thin shell-out — detect install, init when absent, invoke provider-free by default — and leaves a semantic feature index at `.clawpatch/features/*.json`.

- [ ] The run opens with the four-line config-state echo (clawpatch version + `--source`, `CLAWPATCH_PROVIDER`, flow-next review backend as informational, `.clawpatch/` last-mapped) before any other work.
- [ ] With clawpatch absent, the run prints the install instructions and stops. A transcript showing the skill running `pnpm add -g` itself has broken this.
- [ ] A clawpatch version outside the supported range produces one stderr warning naming expected vs found, and the map still runs. A blocked run on a pre-1.0 minor bump has broken this.
- [ ] `--source heuristic` is passed explicitly and is never silently upgraded; a zero-feature heuristic result surfaces the `--source=auto|agent` suggestion instead of opting up on the user's behalf.
- [ ] With `FLOW_RALPH` or `REVIEW_RECEIPT_PATH` set, the skill declines on its first line and writes nothing to the receipt path — the receipt belongs to the upstream review caller.
- [ ] Any ignore rules written land in `.clawpatch/.gitignore`, self-contained inside that directory; the repo `.gitignore` is unchanged and an existing customized skeleton is left alone.
