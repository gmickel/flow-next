---
satisfies: [R7, R11]
---

## Description
Document the fix + immediate workaround + broken-install bootstrap, fix the portable CI example, stage the CHANGELOG. Covers R7 (CI example) and R11 (troubleshooting/platforms + workaround). Downstream `flow-next.dev` is a separate out-of-repo workstream (CLAUDE.md) — note it, don't do it here.

**Size:** M
**Files:** `plugins/flow-next/docs/troubleshooting.md`, `plugins/flow-next/docs/platforms.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/ci-workflow-example.yml`, `README.md`, `CHANGELOG.md`

## Approach
- **troubleshooting.md:** new Windows "`python3` not found / Store stub" section (model: "Copilot review backend on Windows" ~`:75`): the alias stub + exit-9009, the `py`-launcher fix, and TWO recovery paths — (1) manual alias workaround (Settings → Apps → Advanced app settings → App execution aliases → OFF for `python.exe`/`python3.exe`), (2) the **bootstrap for an already-broken `.flow/bin/flowctl`** (plan-review Major): `py -3 .flow/bin/flowctl.py init` (or `python …`), or re-run `/flow-next:setup`.
- **platforms.md:** new "Windows: Python discovery" subsection near `:216` + a caveat on the Python 3.8+ row (`:229`): probe order, `flowctl.cmd` dual launcher, alias pitfall, and **"Ralph mode requires Git Bash on Windows"** (cursor-review Major).
- **flowctl.md:** add `flowctl.cmd` to the `.flow/bin/` layout (`:42-44`) + note `init` self-heal writes it.
- **README.md:** `Python 3.8+` (`:357`) gains "(or the `py` launcher on Windows)".
- **ci-workflow-example.yml (R7) — EXACT replacement (cursor-review Minor):** the example's Option 2 downloads only `flowctl.py`, so `.flow/bin/flowctl` may not exist. So either (a) download `flowctl.cmd` alongside `flowctl.py` and call `flowctl.cmd` on Windows runners, OR (b) wrap the downloaded `flowctl.py` in a small `py -3` / `python` probe (`py -3 flowctl.py … || python flowctl.py …`). Do NOT leave a bare `.flow/bin/flowctl` that the scenario never created.
- **CHANGELOG.md:** create a fresh `## Unreleased` with a `### Fixed` entry (keep-a-changelog; 2.4.0 block is the model). Batched-unreleased — NO version bump.
- Cite: Microsoft `learn/python/faqs` (stub + "py not included with Store Python" + disable-alias), python.org using-windows (`py -3`), PEP 397.

## Investigation targets
**Required:**
- `plugins/flow-next/docs/troubleshooting.md:75`
- `plugins/flow-next/docs/platforms.md:216,229`
- `plugins/flow-next/docs/flowctl.md:42-44`
- `plugins/flow-next/docs/ci-workflow-example.yml` — read the FULL file incl. the Option-2 download block, so the replacement matches what's actually downloaded
- `README.md:357`
- `CHANGELOG.md:1-30`

## Acceptance
- [ ] troubleshooting.md has a Windows `python3`-stub section with BOTH the disable-alias workaround AND the broken-install bootstrap
- [ ] platforms.md documents probe order + `flowctl.cmd` + alias pitfall + "Ralph requires Git Bash on Windows"; README notes the `py` launcher
- [ ] flowctl.md lists `flowctl.cmd` in the `.flow/bin/` layout
- [ ] ci-workflow-example.yml replacement is EXACT — the command it runs matches the files the example actually downloads (flowctl.cmd alongside flowctl.py, or a `py -3`/`python` probe around downloaded flowctl.py); no bare `.flow/bin/flowctl` that the scenario didn't create
- [ ] `## Unreleased` `### Fixed` CHANGELOG entry staged; no version bump
- [ ] flow-next.dev noted as a follow-up (not done in-repo)

## Done summary
Documented the fn-77 Windows `python3` Store-alias-stub fix (R7 + R11): new troubleshooting.md section (probe fix + both recovery paths — re-stamp via `py -3 .flow/bin/flowctl.py init` and the disable-App-Execution-Aliases workaround), a "Windows: Python discovery" subsection in platforms.md (probe order, `flowctl.cmd` dual launcher, alias pitfall, "Ralph requires Git Bash on Windows") plus a Python 3.8+ caveat, `flowctl.cmd` added to the flowctl.md `.flow/bin/` layout with the `init` self-heal note, a `py`-launcher note on the README requirement line, an interpreter-probe replacement for the bare `python3 flowctl.py` in ci-workflow-example.yml, and a fresh `## Unreleased` / `### Fixed` CHANGELOG entry. Docs-only, no version bump (batched). flow-next.dev docs are a separate out-of-repo downstream follow-up per CLAUDE.md.
## Evidence
- Commits: b372067b70c83d9be4b7fa34766b1e7398b1a397
- Tests: bash plugins/flow-next/scripts/smoke_test.sh (138 passed / 0 failed), bash plugins/flow-next/scripts/glossary_smoke_test.sh (80 passed / 0 failed), python3 -c 'import yaml; yaml.safe_load(open("plugins/flow-next/docs/ci-workflow-example.yml"))' (parses OK)
- PRs: