# Conduct checklist — flow-next-drive

A correct run detects the UI surface, picks the highest available driver on the ladder, and drives observe → snapshot → act → verify → capture → release.

- [ ] The surface is classified before driving — web app, Chromium-backed desktop app, or true-native — and an Electron / WebView2 app is driven through the web ladder over its CDP debug port rather than routed to the native rung.
- [ ] Rungs above `agent-browser` are probed (`command -v`, MCP list, `uname -s`) before being planned around, and on a Cursor host `cursor-ide-browser` is probed by exact server id at least once (catalog omission is not absence). A failed attended probe asks once for `@Browser` (no space) or the Browser pane showing connected, then re-probes once before treating it as absent; unattended runs skip the ask. An absent driver degrades to the next rung or a documented limitation rather than ending the pass.
- [ ] Each verify checks the console is clean and no API/network request failed, alongside the expected text or state. A pass declared on a green-looking DOM while a request returned 500 has broken this.
- [ ] Evidence is captured at the moment of interest and on failure — screenshot plus console/network output — so a downstream `/flow-next:qa` verdict rests on captured artifacts rather than narration.
- [ ] Element refs are refreshed by re-snapshotting after any navigation, click, or submit, and a "ref not found" or `pointer-events: none` result is treated as a stale snapshot before it is reported as a bug.
- [ ] The session or tab is released when the pass is done, and an iOS/iPadOS request is declined as out of scope instead of spinning up a simulator.
