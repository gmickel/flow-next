# Prose contract for agent-emitted artifacts

## Goal & Context

flow-next skills emit user-facing prose at known points — PR bodies from make-pr, tracker comments from tracker-sync, spec prose from capture/interview, changelog entries at release. Today the prose discipline for those artifacts is scattered (releasing.md owns changelog ordering; other surfaces have none) and AI-tell patterns land in shipped artifacts. The rules that matter are known and stable: the portability test (a sentence that could appear unchanged in another project's docs says nothing about this one), name-the-mechanism-or-the-number instead of a feeling, user-outcome-first ordering with machinery last, and a small set of style bans.

The fix: one compact prose-contract reference doc shipped in the plugin docs tree, cited with one-line pointers at each emission point. Product improvement for all flow-next users, not just this repo.

## Architecture & Data Models

A single reference doc in the plugin docs tree (`plugins/flow-next/docs/prose.md` — the location is part of the decision: shipped with the plugin so every host installs it, not maintainer-local agent_docs). Content: roughly ten rules that matter for agent-emitted artifacts (portability test; name the mechanism or the number, not the feeling; negative-parallelism ban; no inline-header restating; active voice with named actor; user-outcome-first ordering, machinery last) plus an explicit scope-boundary paragraph: this contract governs artifact prose (PR bodies, specs, comments, changelogs), and makes no claim about code-quality decay (prompt-side quality rules are an intercept intervention per SlopCodeBench, arXiv 2603.24755 — cite the paper, claim nothing beyond it).

Consuming skills carry a one-line pointer to the doc at their prose-emission step — pass the identity (the doc path), never a copied payload. The doc follows the repo docs conventions: a row in the docs README index tables, relative links only, a `## See also` list, reference shape (the GLOSSARY companion doc is the pattern anchor).

The doc states an explicit precedence rule: the emitting surface's structural contracts supersede prose-shape rules — dedup markers stay the first line and unchanged, envelopes and projection-only source-truth constraints are never overridden, and outcome-first ordering applies only when a sourced outcome exists in the payload (never invent outcome prose to satisfy a prose rule).

Rule ownership with `agent_docs/releasing.md`: prose.md owns the generic principles; releasing.md keeps its changelog-specific machinery — the ordering algorithm, the hard rejection test with its worked examples, and the docs-site register — as an explicitly labeled changelog specialization of the generic rules, and gains a cite of the shared doc. Generic restatements in releasing.md are replaced by the cite; a labeled specialization is not duplication.

## Quick commands

```bash
./scripts/sync-codex.sh && ./scripts/sync-codex.sh   # twice — idempotency + link guards
cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q
```

Full gate at the end (per repo rules): `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`

## Edge Cases & Constraints

- Skill-prose edits are taxed: G1 (prose growth must be justified) applies to every pointer line; keep pointers to one line each.
- Prompt-pinned surfaces: none of the target files carry prompt-text pins (verified at plan time), so no hash updates are expected; if an edit strays into a pinned constant, the pin updates in the same commit with the prose rationale.
- Cross-platform: the new doc and every pointer must survive the sync-codex mirror — the docs tree is auto-mirrored; pointer links from skill files must use the standard canonical relative-link shape so the mirror's link-depth rewrite and the hard-fail link-closure guard cover them.
- Direction of citation is one-way: the shipped doc (`plugins/flow-next/docs/prose.md`) must never cite maintainer-local files (`agent_docs/*`) — that link would dangle on every non-maintainer install. `releasing.md` → `prose.md` is fine; the reverse is not.
- Silent degrade: each pointer is a non-blocking aside ("follow docs/prose.md; proceed without it if absent"), never a precondition — Cursor/Droid/Grok read canonical prose as-is and cannot check doc presence.
- Docs-tree changes still run the full gate in this repo (classifier tier-B is not a skip licence).
- Conduct checklists: a pointer edit in capture/make-pr/tracker-sync triggers each skill's conduct-checklist pass (three skills, three passes).

## Acceptance Criteria

- **R1:** A compact prose-contract reference doc ships in the plugin docs tree, containing the artifact-prose rule set and an explicit scope-boundary paragraph (artifact prose, not a code-quality claim), and is registered in the docs README index and the root CLAUDE.md "Where to look" table. The doc's own prose passes its own rules. Errors: no error surface beyond docs link guards (R4).
- **R2:** The prose emission points cite the doc with a one-line pointer at the step that drafts user-facing prose: make-pr body rendering, tracker-sync comment composition, capture spec-prose synthesis. No rule text is duplicated into skill prose. Errors: on hosts where the doc isn't reachable at the cited path, the pointer degrades silently — phrased as a non-blocking aside, never a precondition; skills keep working. Boundary: the emitting surface's structural contracts supersede prose-shape rules — tracker-comment dedup markers stay first-line and unchanged, projection-only source-truth is never overridden, and outcome-first applies only when a sourced outcome exists in the payload (no invented outcome prose).
- **R3:** Rule ownership is single-copy by layer: prose.md owns the generic prose-craft principles; `agent_docs/releasing.md` cites prose.md and keeps only its changelog-specific machinery (ordering algorithm, hard rejection test with worked examples, docs-site register), explicitly labeled as a changelog specialization. Generic restatements in releasing.md are replaced by the cite; the same generic rule never lives spelled out in both files. Errors: no error surface beyond review judgment.
- **R4:** `./scripts/sync-codex.sh` runs twice cleanly with the new doc and pointers in place; the mirror's docs-link guards (link resolution + installed-docs link universe) pass. Errors: a guard failure is load-bearing — fix content or extend the transform, never relax the guard.

## Boundaries

- No new skill and no per-skill rule dump — pointers only; this stays a one-or-two-task change.
- No claim that the contract improves code quality or maintainability decay — artifact prose only.
- No enforcement machinery (no linter, no test pinning prose sentences — G2 forbids it); this is reviewed prose guidance.
- Interview's spec write-back, resolve-pr's reply composition, and the visual digest are prose surfaces too — deliberately not in this pass; extend the pointer set in a follow-up once the doc proves itself (one line each, same pattern).
- make-pr's existing hallucination guardrails stay where they are (canonical, load-bearing); prose.md cross-links them, never re-derives them.
- Downstream properties (flow-next.dev, docs guide) are follow-on work in the same workstream, not R-IDs here.
- No version bump in this change — CHANGELOG entry stages under `## Unreleased` per the batched-release rule.

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — the doc ships inside the plugin docs tree so every host installs it; pointers use canonical link shapes covered by the sync-codex mirror guards.

## Decision Context

Doc-plus-pointers over the alternatives: a new always-on prose skill was rejected (scope creep, G1 context cost, repo rule against unrequested skills); per-skill rule dumps were rejected (duplication, prompt-pin churn, sync-codex tax); baking rules only into releasing.md was rejected (changelog-only reach — make-pr and tracker-sync would stay uncovered). A cited reference doc fits the repo's architecture doctrine: the host agent reads the doc at the emission point — pass identity, not payload.

Plan-time decisions: cite-not-absorb for releasing.md (its changelog gate and worked examples are battle-tested; generic restatements collapse into the cite, the changelog-specific machinery stays as a labeled specialization — trimming, not restructuring). Review-hardened (codex round 1): the byte-intact framing was dropped because releasing.md already restates generic rules — ownership is by layer, not by byte range; and the structural-precedence boundary was added because tracker comments carry contracts (marker-first, projection-only) that prose-shape rules must never override. Interview/resolve-pr/visual pointer coverage deferred to a follow-up rather than widening this pass (the request named three surfaces; the pattern extends in one line per surface later).

## Early proof point

Task fn-207-prose-contract-for-agent-emitted.1 validates the core approach (the doc lands, reads as a compact reference, and the releasing.md cite removes duplication without damaging the changelog gate). If the generic/changelog-specific split turns out murky, re-evaluate cite-vs-absorb before wiring pointers in .2.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Doc ships + indexed + self-consistent | fn-207-prose-contract-for-agent-emitted.1 | — |
| R2 | One-line pointers at three emission points | fn-207-prose-contract-for-agent-emitted.2 | — |
| R3 | releasing.md single-copy cite | fn-207-prose-contract-for-agent-emitted.1 | — |
| R4 | sync-codex twice clean + link guards | fn-207-prose-contract-for-agent-emitted.2 | — |

## References

- Docs index + conventions: `plugins/flow-next/docs/README.md` (index tables; R17 cross-link discipline)
- Pattern anchor for reference shape: `plugins/flow-next/docs/glossary.md`
- GLOSSARY.md "Emission point" term — the pointer discipline (path citation, never payload)
- Changelog prose rules to cite from: `agent_docs/releasing.md` (changelog writing gate; docs-site register)
- Mirror machinery: `scripts/sync-codex.sh` (docs-tree mirror; link-depth rewrite; link-closure hard-fail guard)
