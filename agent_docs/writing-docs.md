# Writing the docs

How to write `plugins/flow-next/docs/**` and [flow-next.dev](https://flow-next.dev). This is a documentation specialization of the artifact-prose contract in [`../plugins/flow-next/docs/prose.md`](../plugins/flow-next/docs/prose.md); the ten generic rules live there and are not restated here. What follows is the doc-specific machinery: how to frame a claim, how to shape a page, and what must stay true about navigation.

The sibling specialization for release notes is the [changelog writing gate](releasing.md#changelog-writing-gate).

## Frame by capability, bound by honesty

The rule that decides how a sentence is shaped:

| Kind of claim | Frame | Example |
|---|---|---|
| Capability | positive, name what you can do | "Every arrangement keeps the same execution, evidence, and review contracts" |
| Bound, limit, or refusal | negative, state it plainly | "QA never marks PASS by reading source" |

**Capability claims never define the product by what it is not.** "A menu, not a rail" teaches the reader the word *rail*; "compose the pipeline" teaches them what to do. A page titled by an objection makes the objection the first thing a reader learns, including the readers who never had it.

**Bounds stay negative, and stripping them is a defect.** Rule 10 of the prose contract requires honest limits: what a stage refuses, what a loop will not do, what a benchmark does not test. A doc that hides its bounds is marketing.

Two negations earn an exception:

- A **precise distinction against a named alternative**, used once: "projection, not coordination" only works because a coordination-driven tracker is a real thing a reader may assume.
- An **anti-pattern list**, where the negation is the lesson: "that is assignment, not dependency."

Anything else that reads `X, not Y` in a title, an H2, or a page's first paragraph is a rewrite.

**Do not sell relief; sell the capability that produces it.** "Reviews stop being where work waits" describes a pain leaving. "Open a PR that already makes its argument" describes a thing you now have. The second is checkable, and checkable is this project's whole pitch.

## One page, one job

- **A page answers one question**, and its title is close to that question. Reference belongs in reference, doctrine in an understanding page, and steps in a guide. A page that argues, instructs, and specifies at once will be skimmed for none of the three.
- **The index is a lookup surface.** A `What's in it` cell is one line. If it needs a parenthetical, the detail belongs on the page.
- **Orientation prose is a smell.** A paragraph explaining how this page relates to its three siblings usually means the siblings should be one page, or that the section needs a landing page.
- **Every long reference opens with a contents list.** Over roughly 200 lines, generate it from the real headings.

## Navigation is a contract

- **A heading is an anchor.** Rewording one breaks every citation of it. Run `python3 scripts/check_doc_anchors.py` (`--fix` repairs anchors that differ only by hyphen runs), which also runs in CI.
- **A moved slug gets a redirect** on the site, in `astro.config.ts`, in the same change. No moved page 404s.
- **Relative repo paths only** in `plugins/flow-next/docs/**`, so a fork and an offline clone both keep working. The Codex mirror rewrites what it must; do not hand-write absolute URLs into that tree.
- **Nav lives in one place** on the site (`src/lib/site.ts`), and a page that is not in it is invisible.

## Words to keep out

Beyond the prose contract's style bans:

- **Em dashes.** House style is a plain hyphen or a comma. The exceptions are literal product output and pinned contract strings, both of which the test suite protects.
- **Internal spec ids in lookup tables.** `(fn-200, #359)` sits between a reader and the answer. In prose, an id that points at a decision record earns its place.
- **Version stamps that are not compatibility information.** "since 4.5.1" is useful; "(fn-72, 2.2.0+)" in a config table is noise.
- **`## What this is not` as a heading.** State the boundary: `## Where it stops`.

## Which surface owns what

| Surface | Owns |
|---|---|
| `plugins/flow-next/docs/**` | The offline-resilient reference. Contracts, schemas, CLI, per-harness reach. Read by agents and by maintainers. |
| flow-next.dev | The reading experience. Journey ordering, landing pages, the marketing surface. |
| Root `README.md` | The pitch and the 5-command path. Its "What you get" headings stay in lockstep with the homepage cards. |

When the same fact lives on two surfaces, one of them is canonical and the other links to it. The canonical sentence for supported platforms lives in [`platforms.md`](../plugins/flow-next/docs/platforms.md) for exactly this reason.

## Before you hand off

- `python3 scripts/check_doc_anchors.py`
- `./scripts/sync-codex.sh` twice, and commit the mirror diff with the canonical change
- `python3 scripts/run_tests_parallel.py` (docs content is pinned by several tests)
- On the site: `pnpm build` and `pnpm check:links`
