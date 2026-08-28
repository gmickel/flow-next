# Conduct checklist — /flow-next:prose

A correct run applies the shipped prose contract (`plugins/flow-next/docs/prose.md`) to ONE substantial reply, report, review walkthrough, or summary at draft time, and touches nothing else.

- [ ] The transcript shows a Read of `docs/prose.md` (resolved relative to the SKILL.md) before the governed reply is drafted; if the doc is absent, the reply still lands and a fabricated rules recitation never substitutes for it.
- [ ] The governed reply contains zero em dashes and zero clause-splicing colons (structural colons in list introductions and table cells are allowed).
- [ ] Quoted material, code blocks, command output, and the user's own words are byte-unchanged in the governed reply; the skill rewrote only prose it authored.
- [ ] The reply leads with the answer (softened rule 8) and never invents an outcome, number, or measurement to satisfy a rule; honesty (rule 10) is visible — bounds and misses stated, not softened.
- [ ] Nothing out of scope was touched: no trigger on a short conversational turn or tool-call narration, no rewrite of a visual digest, and no rewrite of output destined for a file, PR, or tracker (those surfaces carry their own pointers).
- [ ] On explicit `/flow-next:prose` invocation the run is read-only: no Write or Edit tool use, no flowctl state mutation, no commit, no other workflow invoked. On ambient application mid-session, the skill itself performs no tool use beyond the `docs/prose.md` Read and mutates no flowctl state (the surrounding session's own edits are out of scope for this row).
