# Adopt cua browser-use in drive/qa: rung-2 upgrade, Electron exception, cua.md re-validation, isolated-profile default

## Goal & Context
<!-- scope: business -->

cua-driver grew a full CDP-based browser capability between 0.9.0 and 0.19.0 (the `browser_*` tool family: exact native-window-to-CDP-target binding that refuses ambiguity, background input without focus steal, semantic_v2 snapshots with typed action refs, consent-token-gated attach to signed-in profiles, driver-owned isolated profiles). flow-next's drive/qa driver model predates all of it: `flow-next-drive/references/cua.md` is provenance-pinned at 0.6.8 and documents only the AX-tree loop, and the web ladder's rationale prose for excluding cua from Chromium targets ("slower, lower fidelity") is now factually wrong.

Decisions made (2026-08-07, maintainer-ratified):
1. **Web ladder: cua browser-use upgrades the rung-2 slot** (the "attach to real Chrome" role currently held by chrome-devtools-mcp) - exact-or-refuse tab binding, consent-gated profile attach, and no-focus-steal evidence capture beat the incumbent. agent-browser stays rung 1 and the only assumed-present driver.
2. **Electron: web-ladder default stands, with a cua exception** for exactly two cases - no-focus-steal driving matters, or native shell chrome (menus/tray - a documented web-ladder limitation) must be reached. The old "slower, lower fidelity" rationale is deleted wherever it appears.
3. **cua.md gets the full live re-validation treatment**, not an addendum - the file's value is measured-live claims; bump the provenance pin to the validated version and re-run the drift discipline the file itself prescribes.
4. **Isolated profile is the mandated default** for any flow-next-driven cua browser session; existing-profile attach is explicit operator opt-in, mirroring the sandbox cloud opt-in pattern. QA evidence never rides a signed-in session by default.

## Architecture & Data Models
<!-- scope: technical -->

Surfaces: `plugins/flow-next/skills/flow-next-drive/SKILL.md` (ladder + routing rules ~lines 14-79), `flow-next-drive/references/cua.md` (full re-validation + new browser section + consent prose), `flow-next-qa` prose where agent-browser commands are hardcoded (workflow.md ~259-303 - generalize to per-rung equivalents only where a second web driver becomes real; QA evidence tuple already accepts free-form rung values, no schema change). Codex mirror via sync-codex (twice); Cursor/Droid consume canonical as-is - keep tool references host-portable.

Ladder philosophy note (maintainer question, answered): the ladder stays CAPABILITY-ordered, not host-ordered - host bias is already implicit because rungs are probed and missing ones skip (cursor-ide-browser only probes true in Cursor). The one host-aware refinement worth carrying: in the nothing-installed branch, prefer an already-present host-native rung over instructing an install. No reordering by host identity.

## Edge Cases & Constraints
<!-- scope: technical -->

- cua browser tools are Chromium-only; surface C (WKWebView/Tauri-on-macOS, true native) is untouched.
- Trusted background input is platform-honest (works Windows Chrome/Edge + embedded Electron; macOS/Linux standalone Chrome may refuse with `browser_input_trust_unavailable` + unverifiable-DOM fallback) - the skill prose must carry this honestly, never promise background input universally.
- Headless/CI web stays agent-browser; cua sandbox line is out of scope.
- All cua rungs remain probe-and-optional; consent prose must cover permission modes, `browser-approve` tokens, and the isolated-vs-existing profile boundary.
- Re-validation is live-measured (like the 0.6.8 pass) - claims not verified against the installed version do not enter cua.md.

## Acceptance Criteria
<!-- scope: both -->

- R1: Drive's web ladder documents cua browser-use in the rung-2 role with probe + graceful-absence, agent-browser unchanged as rung 1; stale "slower, lower fidelity" rationale removed everywhere. Errors: probe-absent -> next rung, never block.
- R2: Electron routing keeps the web-ladder default and adds the two-case cua exception (no-focus-steal, shell chrome), stated as an exception, not a new default. Errors: no error surface beyond routing prose review.
- R3: cua.md re-validated live against the installed cua-driver: provenance pin bumped, browser_* section added, AX-loop content re-verified, consent section covers permission modes/approval tokens/profile boundary. Errors: unverifiable claims are omitted or marked unverified, never asserted.
- R4: Isolated-profile default + existing-profile opt-in stated wherever a flow-next skill can open a cua browser session; QA prose notes the no-focus evidence capture path. Errors: no error surface beyond review.
- R5: Nothing-installed branch prefers an already-present host-native rung over an install instruction; ladder order otherwise unchanged. Errors: no error surface beyond routing prose review.
- R6: sync-codex run twice, mirror committed; platforms.md noted if host behavior differs. Errors: sync guards must stay green.

## Boundaries
<!-- scope: business -->

- NOT reordering the ladder by host identity; capability order stands.
- NOT touching surface C (true-native) routing or the cua sandbox line.
- NOT adding cua to CI/headless paths.
- NOT a general driver-plugin framework.

## Decision Context
<!-- scope: both -->

Grounded in the 2026-08-07 research briefing (cua 0.9.0-0.19.0 release sweep + local 0.19.0 CLI probe + flow-next drive/qa file map). All four open decisions resolved by the maintainer going with the session's recommendations; the host-bias question was raised and answered as "probe economics, not rank order" (R5).
