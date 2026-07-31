---
satisfies: [R24, R25, R41]
---
# fn-151-front-door-overhaul-value-first-landing.4 mickel.tech alignment

## Description
Align the mickel.tech flow-next page and app-registry entry with the recomposed front doors. This is alignment, not a rewrite: the page's job stays credibility plus a funnel to flow-next.dev.

**Size:** S/M
**Files:** `app/apps/flow-next/page.tsx`, `lib/apps.ts` (both in `/Users/gordon/work/mickel.tech`)

### Approach

Six changes.

1. **Version.** `APP_DATA.version` at `page.tsx:23` says `2.20.0`. Ship `3.9.0`.
2. **Problems section.** The `problems` array at `page.tsx:220-241` is mechanism-named: "Unbounded context", "Vague work units", "No adversarial loop", "Invisible evidence". Restate as pain the reader recognises having, mirroring the six outcomes. The mechanism becomes the description line, never the title.
3. **Platform statuses.** The `platforms` array at `page.tsx:243-332` runs its own vocabulary (Primary, Full, Full, Works, Works, Experimental) that matches neither the repository nor the docs site. Converge on the canonical sentence task 4 writes into `plugins/flow-next/docs/platforms.md`: first-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, and xAI Grok Build, with OpenCode as the community port. Also correct the Cursor install guidance: the recommended route is the team-marketplace repo import, with `install-cursor.sh` as the fallback.
4. **Counts.** This page is a front door, so counts come out of selling prose: "22 named subagents" at `page.tsx:253`, "22 multi-agent roles" at `page.tsx:283`, "twenty-eight agent-native skills" at `page.tsx:55`, and "60+ verified recipes" at `page.tsx:1058` (the cookbook currently holds 73 recipe cards, so the number is both stale and unnecessary). Replace with the capability and a link.
5. **Breadth and honest asymmetry.** The page already carries its own breadth paragraph at `page.tsx:934-949`. Align its wording with the landing's and add the honest-asymmetry paragraph, in this page's client-and-employer register.
6. **Registry entry.** `lib/apps.ts:45-56`: restate the description in the outcome-first register rather than the mechanism list it currently repeats, and add Grok Build to the `tags` array, which lists Cursor but omits Grok.

### Investigation targets

**Required:**
- `app/apps/flow-next/page.tsx:17-26` - `APP_DATA`, stale version
- `app/apps/flow-next/page.tsx:220-332` - `problems` and `platforms` arrays
- `app/apps/flow-next/page.tsx:928-975` - the existing breadth paragraph and testimonial block
- `lib/apps.ts:45-56` - the registry entry
- `CLAUDE.md` in mickel.tech - the ship checklist and build gate

**Optional:**
- `plugins/flow-next/docs/platforms.md` in the flow-next repo - the canonical tiering sentence task 4 writes

### Design context

This is a Next.js page using the Atelier component set (`AtelierAppHero`, `AtelierAppSection`, `AtelierFeatureGrid`, `AtelierSpecList`). Do not restructure the sixteen numbered sections or introduce new components; this task changes copy and data, not layout. Keep every `<Image>` alt text meaningful per the repo ship checklist.

### Key context

Register is client and employer credibility, distinct from the README's skeptical staff engineer and the docs site's practitioner voice. Outcomes and business consequence, not mechanism.

Build gate is `bun run build` plus `bun x biome check .`; lefthook runs `bun x ultracite fix` on pre-commit and fails the commit on lint errors. This repository has no CI, so the local gate is the only gate.

Commit in the mickel.tech repository separately and report the SHA as evidence.

Copy rules apply: no em dashes (this file currently has zero, keep it that way), straight quotes outside verbatim quotations, flat present-tense claims with no hedging, no "not X but Y" construction, none of the banned phrases listed in task 1, no client names, sector descriptors only.

## Acceptance
- [ ] `APP_DATA.version` reads `3.9.0`
- [ ] The `problems` array states reader-recognisable pain in its titles, with mechanism relegated to the description
- [ ] Platform statuses match the canonical tiering sentence; Cursor's recommended install is the team-marketplace import
- [ ] No count appears in selling prose: the two 22-subagent claims, the 28-skills claim, and the 60+ recipes claim are replaced by capability plus link
- [ ] The breadth paragraph matches the landing's wording and the honest-asymmetry paragraph is present, in this page's register
- [ ] `lib/apps.ts` description is outcome-first and its tags include Grok Build
- [ ] No layout restructure; the sixteen numbered sections and Atelier components are unchanged
- [ ] `bun run build` and `bun x biome check .` both pass
- [ ] Committed separately in the mickel.tech repository, SHA reported as evidence
- [ ] No em dashes, no client names, no banned phrases, no hedging


## Done summary
Aligned the mickel.tech flow-next page and its `/apps` registry entry with the recomposed front doors: version corrected to 3.9.0, problem titles restated as pain the reader recognises having with the mechanism demoted to the description line, platform statuses converged on the canonical harness-tiering sentence (first-class on Claude Code, OpenAI Codex, Factory Droid, Cursor and xAI Grok Build; community port for OpenCode) with Cursor's team-marketplace import as the recommended route, every inventory count removed from selling prose, and the breadth paragraph aligned to the landing's wording with the honest-asymmetry paragraph added in this page's client-and-employer register.

Committed separately in the mickel.tech worktree at `/Users/gordon/work/fn151-mickel` (branch `fn-151-alignment`) as `c4192b2afdce447893d482af5f7779c9f00524fb`. No layout restructure: the sixteen numbered sections and every Atelier component are unchanged.
## Evidence
- Commits: mickel.tech:c4192b2afdce447893d482af5f7779c9f00524fb
- Tests: cd /Users/gordon/work/fn151-mickel && bun run build -> PASS (exit 0; /apps/flow-next prerendered static; requires RESEND_API_KEY + RESEND_FROM to be set, placeholder values used), cd /Users/gordon/work/fn151-mickel && bun x biome check . -> PASS (exit 0; 205 files, no fixes applied), lefthook pre-commit `bun x ultracite fix` -> PASS (205 files, no fixes applied), baseline before edits: bun x biome check . -> PASS; bun run build -> PASS with RESEND_API_KEY/RESEND_FROM placeholders (RED without them, pre-existing env requirement unrelated to this task), grep -ri 'PSVI|Velocity Index' app/apps/flow-next lib/apps.ts -> no output (clean), grep -riwf ~/.claude/flow-next-client-names.txt app/apps/flow-next lib/apps.ts -> no output (clean), grep -c '—' app/apps/flow-next/page.tsx lib/apps.ts -> 0, 0 (no em dashes), rendered-page check on the production build: breadth + honest-asymmetry paragraphs, four restated problem cards, and the canonical tiering lede all present; document horizontal overflow = 0px
- PRs: