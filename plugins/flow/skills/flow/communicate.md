# Communicate

Apply these rules automatically to specs, PR bodies, and long replies so a reader arriving cold can act in one scan.

## Prose

Lead with the conclusion or outcome, then give the mechanism, path, or number that backs it. Cut any sentence that could be pasted unchanged into another project's PR or doc. Replace vague intensifiers ("significantly faster", "substantially cleaner") with the concrete mechanism or before-and-after measurement; if you have neither, drop the claim.

Write short paragraphs in active voice with a named actor. State what something is rather than contrasting what it is not, unless you are correcting a likely misreading. Do not repeat the heading in the opening sentence or restate the question before answering it. Use plain words ("use" over "utilize", "to" over "in order to"), define domain terms at first use, and drop filler and hedging beyond real uncertainty.

Be plain about limits and gaps: state what was not verified, where you looked, and what could not be read. Never soften a failure or missing check. When a surface requires an exact heading, bullet prefix, or marker, that contract overrides prose style.

## Visual shapes

Use plain markdown shapes that render identically in terminals and on every forge; never emit images or HTML. Add a shape only when it lands faster than a paragraph, place it beside the one or two sentences it supports, and include only the nodes needed for the current question. Every path, symbol, or relationship must come from files or state you actually read.

- **Table:** comparing options or listing short enumerable facts; keep explanations in surrounding prose, not inside cells.
- **Indented text tree:** file layout, module ownership, or a call or component hierarchy, with one-line roles.
- **Diff-fenced sketch (`diff`):** a before-and-after change to an existing tree, control flow, or state machine.
- **Types or signatures:** new or changed public interfaces, flags, or schemas before code exists.
- **Short flow or pseudocode:** a sequence, branch rule, or algorithm.

Pick one or two shapes that fit the question, never all of them.

## Spec digest

End every spec write with a one-screen digest:

1. Lead with `[inferred]` requirements so assumptions are reviewed first.
2. State the thesis in one sentence.
3. Show the acceptance criteria at a glance, the in/out boundaries, and any open questions with their owner role.
