---
satisfies: [R1, R2, R3, R4, R6, R7]
---

## Description

Add the **local Cua Driver** as a detected, opt-in option on flow-next-drive's Native rung (Step 4), and author its per-rung reference. Everyday rung (background driving) + the **early proof point** — the full loop was validated live (cua-driver 0.6.8).

**Pure host-driven MCP actuation — NO flowctl/Python, no deterministic probe engine, no AX-tree parsing in code.** Detection is a `command -v` / MCP-list probe the host runs inline; the host reads the AX tree directly. Mirror the `/flow-next:map`↔`clawpatch` detect-and-instruct precedent.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-drive/SKILL.md`, `plugins/flow-next/skills/flow-next-drive/references/cua.md` (new)

## Approach

- **SKILL.md Step 4** (`flow-next-drive/SKILL.md:62-68`): add a CUA detect/route line + `→ Read references/cua.md` pointer. Keep ALL command detail OUT of SKILL.md. Surface table (`:18-22`) + routing (`:27-30`) unchanged.
- **`references/cua.md`** mirrors `references/computer-use.md` section order (`:22-178`): scope → the local Cua Driver surface → detect availability (`command -v cua-driver`, MCP-registered, `cua-driver doctor`, `cua-driver permissions status`) → driving loop (AX-tree, snapshot-before-each-indexed-action invariant, goal-not-pixels) → safety/hygiene → degradation table (`computer-use.md:144-156`) → **drift/verify-at-build** (R6) → limits. Carry a provenance line.
- **HOST-AGNOSTIC wiring (correct basis):** skill-local `references/cua.md` rides the skill-dir copy in `sync-codex.sh:136` + the path/ToolSearch rewrite passes — it is **NOT** the plugin-level byte-identical `references/` (`:155-156`). The rewrites won't translate a Claude-only `claude mcp add`, so present MCP wiring for **both hosts** (Claude `claude mcp add … cua-driver mcp` AND Codex `[mcp_servers.cua-driver]` in `~/.codex/config.toml`) — multi-host, not Claude-only-as-the-sole-form. Verify by inspecting the generated Codex mirror reads coherently.
- **Native-rung precedence** (R4) as explicit prose: attended → cua-driver background → Codex/Claude Computer Use → documented-limitation.
- **Licensing** (R7): default driving path = MIT `cua-driver` MCP only; document `cua-agent[omni]`→ultralytics (AGPL-3.0) + OmniParser CC-BY, and **never auto-install** them (per map/clawpatch).
- **Permission split** (validated): Accessibility unlocks driving; Screen Recording unlocks screenshots — separate grants; daemon must restart to pick up a grant; grant attributed to `com.trycua.driver` (LaunchServices); ad-hoc-signed rebuilds reset grants. Screen-Recording-absent ⇒ surface "AX-only evidence" (R6), not a silent empty screenshot.
- **Evidence tuple** (R6): `cua-driver` slots into QA's free-form `driver_rung` string (`flow-next-qa/SKILL.md:89`) with NO schema/code change; do NOT edit the fn-51↔fn-53 seam.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-drive/SKILL.md:62-78` — Step 4 + degradation (insertion point)
- `plugins/flow-next/skills/flow-next-drive/references/computer-use.md:22-178` — reference TEMPLATE
- `plugins/flow-next/skills/flow-next-map/SKILL.md:76,95-104` — detect-and-instruct / never-auto-install
- `scripts/sync-codex.sh:136,155-156` — skill-dir copy vs plugin-level byte-identical references (the multi-host basis)
- `plugins/flow-next/skills/flow-next-qa/SKILL.md:89` — evidence tuple + fn-51↔fn-53 seam
**Optional:**
- cua-driver README: https://github.com/trycua/cua/blob/main/libs/cua-driver/README.md

## Acceptance
- [ ] Step 4 documents the local Cua Driver as a detected, optional rung with only a detect/route line + `references/cua.md` pointer.
- [ ] `references/cua.md` exists, mirrors computer-use.md section order incl. degradation table + drift/verify-at-build; **MCP wiring shown for both Claude and Codex (multi-host, not Claude-only)**; `sync-codex.sh` regenerates and the generated Codex mirror reads coherently (verified by inspection — not a byte-identical `cmp` claim).
- [ ] Detection probe-based + graceful; absent ⇒ fall to Computer Use → documented-limitation; never assumed, never imported by flowctl.
- [ ] Native-rung precedence stated as an explicit ordered list (attended path).
- [ ] Licensing: default path MIT-only; AGPL/CC-BY extras flagged + never auto-installed.
- [ ] Permission-split evidence mode documented: Screen-Recording-absent ⇒ AX-only evidence surfaced.
- [ ] `cua-driver` is a valid `driver_rung`; fn-51↔fn-53 seam unchanged.
- [ ] NO flowctl/Python added (grep confirms no `flowctl cua` / Python CUA wrapper).

## Done summary
Added the local Cua Driver as a detected, opt-in native-rung driver on flow-next-drive (SKILL.md Step 4: probe Cua Driver → Computer Use → documented-limitation) and authored `references/cua.md` — pure host-driven MCP prose mirroring `computer-use.md`, with multi-host wiring (Claude `claude mcp add` + Codex `[mcp_servers.cua-driver]`), the macOS Accessibility-vs-Screen-Recording permission-split evidence mode, MIT-only default path, and a drift/verify-at-build section. No flowctl/Python added; Codex mirror regenerated and verified coherent.
## Evidence
- Commits: cd325107e8bb1635c54b8d1741d7daba609c1927
- Tests: bash scripts/sync-codex.sh (29 skills, all validations pass, idempotent), diff canonical vs codex mirror of references/cua.md (whitespace-only normalization; multi-host wiring intact), grep -rn flowctl cua (no flowctl/Python CUA wrapper)
- PRs: