# Plan next-steps menu (interactive only)

Load this reference only when the Step 8 interactivity gate printed its
sentinel — no non-interactive marker is set. Autonomous, Ralph, and
receipt-driven runs never reach this file; they run Step 8.5 directly after
Step 6/7 complete.

**Above the numbered list, print exactly ONE recommendation line** — mandatory, never silently omitted — and re-judge it at every menu print: a go-deeper/simplify round changes the risk picture, and stale advice is worse than none.

```
Recommended next: /flow-next:<stage> fn-N-slug — <one-clause reason>; <named alternative when it applies>
```

Judge the line by reading [`plan-vs-no-plan.md`](../../flow-next-flow/references/plan-vs-no-plan.md) (a plan whose task set carries no positive plan signal is recommended back to `/flow-next:work fn-N-slug --no-plan`) and, when the question is plan-review versus work, [`gate-selection.md`](../../flow-next-flow/references/gate-selection.md): any remaining design risk recommends `/flow-next:plan-review` (the cheapest measured catch in the pipeline), and a skip recommendation names the reason. Judgment inputs: the task breakdown just produced, design risk surfaced during research, and blast radius. When signals genuinely conflict, the recommendation is `/flow-next:flow --explain fn-N-slug` with a "signals conflict" reason. The line is advisory - a recommendation with a reason, never a directive, gate, or blocking question; the numbered menu below stays verbatim.

Offer options under the spec summary Step 8 already printed:

```
Next steps:
1) Start work: `/flow-next:work fn-N-slug`
2) Refine via interview: `/flow-next:interview fn-N-slug`
3) Review the plan: `/flow-next:plan-review fn-N-slug`
4) Go deeper on specific tasks (tell me which)
5) Simplify (reduce detail level)
```

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

If user selects 4 or 5:
- **Go deeper**: Ask which task(s), then add more context/research to those specific tasks
- **Simplify**: Remove non-essential sections, tighten acceptance criteria, merge small tasks

Loop back to options after changes until user selects 1, 2, or 3. Any task or
dependency change re-runs Step 6 and recomputes the execution waves before the
final summary.

**On loop exit (user picked 1, 2, or 3):** run Step 8.5 BEFORE dispatching the chosen next step or finishing — never on first arrival at this menu. Options 4/5 mutate tasks; generating earlier would render a lens the user is still editing.
