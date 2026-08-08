# Plan next-steps menu (interactive only)

Load this reference only when the Step 8 interactivity gate printed its
sentinel — no non-interactive marker is set. Autonomous, Ralph, and
receipt-driven runs never reach this file; they run Step 8.5 directly after
Step 6/7 complete.

Offer options under the spec summary Step 8 already printed:

```
Next steps:
1) Start work: `/flow-next:work fn-N-slug`
2) Refine via interview: `/flow-next:interview fn-N-slug`
3) Review the plan: `/flow-next:plan-review fn-N-slug`
4) Go deeper on specific tasks (tell me which)
5) Simplify (reduce detail level)
```

If user selects 4 or 5:
- **Go deeper**: Ask which task(s), then add more context/research to those specific tasks
- **Simplify**: Remove non-essential sections, tighten acceptance criteria, merge small tasks

Loop back to options after changes until user selects 1, 2, or 3. Any task or
dependency change re-runs Step 6 and recomputes the execution waves before the
final summary.

**On loop exit (user picked 1, 2, or 3):** run Step 8.5 BEFORE dispatching the chosen next step or finishing — never on first arrival at this menu. Options 4/5 mutate tasks; generating earlier would render a lens the user is still editing.
