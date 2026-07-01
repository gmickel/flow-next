---
satisfies: [R7, R11]
---

## Description
Document the fix + the immediate user workaround + the broken-install bootstrap, fix the portable CI example, and stage the CHANGELOG. Covers R7 (CI example) and R11 (troubleshooting/platforms + workaround). Downstream `flow-next.dev` is a separate out-of-repo workstream (CLAUDE.md) — note it, don't do it here.

**Size:** M
**Files:** `plugins/flow-next/docs/troubleshooting.md`, `plugins/flow-next/docs/platforms.md`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/ci-workflow-example.yml`, `README.md`, `CHANGELOG.md`

## Approach
- **troubleshooting.md:** new Windows "`python3` not found / Store stub" section modeled on the "Copilot review backend on Windows" entry (~`:75`): the App Execution Alias stub + exit-9009, the `py`-launcher fix, and TWO recovery paths — (1) the manual alias workaround (Settings → Apps → Advanced app settings → App execution aliases → OFF for `python.exe`/`python3.exe`), and (2) the **bootstrap self-heal for an already-broken `.flow/bin/flowctl`** (plan-review Major): run `py -3 .flow/bin/flowctl.py init` (or `python .flow/bin/flowctl.py init`), or re-run `/flow-next:setup` — since a broken bash launcher can't fix itself.
- **platforms.md:** new "Windows: Python discovery" subsection near "Windows + Copilot review backend" (`:216`) + a caveat on the Python 3.8+ row (`:229`): probe order, `flowctl.cmd` dual launcher, alias pitfall.
- **flowctl.md:** add `flowctl.cmd` to the `.flow/bin/` layout (`:42-44`) + note `init` self-heal writes it.
- **README.md:** `Python 3.8+` (`:357`) gains "(or the `py` launcher on Windows)".
- **ci-workflow-example.yml (R7):** `:31` (+ commented `:27`) — replace bare `python3 flowctl.py` with `.flow/bin/flowctl validate …` (or explicit `py -3`/probe) so it's Windows-runner-portable.
- **CHANGELOG.md:** create a fresh `## Unreleased` with a `### Fixed` entry (keep-a-changelog; 2.4.0 block is the model). Batched-unreleased — NO version bump (CLAUDE.md).
- Cite: Microsoft `learn/python/faqs` (stub + "py not included with Store Python" + disable-alias), python.org using-windows (`py -3`), PEP 397.

## Investigation targets
**Required:**
- `plugins/flow-next/docs/troubleshooting.md:75` — Windows-fix entry pattern
- `plugins/flow-next/docs/platforms.md:216,229` — Windows section + requirements table
- `plugins/flow-next/docs/flowctl.md:42-44` — `.flow/bin/` layout + `init`
- `plugins/flow-next/docs/ci-workflow-example.yml:27,31` — the bare `python3` lines
- `README.md:357` — Python prereq
- `CHANGELOG.md:1-30` — 2.4.0 entry as the `## Unreleased` model

## Acceptance
- [ ] troubleshooting.md has a Windows `python3`-stub section with BOTH the disable-alias workaround AND the broken-install bootstrap (`py -3 .flow/bin/flowctl.py init` / re-run setup)
- [ ] platforms.md documents the probe order + `flowctl.cmd` + alias pitfall; README notes the `py` launcher
- [ ] flowctl.md lists `flowctl.cmd` in the `.flow/bin/` layout
- [ ] ci-workflow-example.yml no longer calls bare `python3 flowctl.py` (Windows-portable form)
- [ ] `## Unreleased` `### Fixed` CHANGELOG entry staged; no version bump
- [ ] flow-next.dev noted as a follow-up (not done in-repo)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
