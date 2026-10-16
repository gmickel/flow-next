# Re-check after a prior pass (gated reference)

> Read from [workflow.md](../workflow.md) §1.4 only when the spec has a QA receipt from an earlier head.

A scenario that passed live on a surface nothing has touched since does not need driving again.
Drive what could have changed and carry the rest, cited with the head and evidence it was
captured at.

## Use the prior receipt only when it fits

Run in full, as on a first pass, unless the prior receipt's `id` is this spec, its `branch` is the
current branch, its `head_sha` is still a commit here (`git cat-file -e <head_sha>^{commit}`), and
it lists `scenarios` with their outcomes.

Compare trees, not history, so a rebase's base changes count:

```bash
git diff --name-only <prior head_sha> HEAD
```

Also run in full when the diff touches shared code broadly (styles, layout, state stores,
routing, auth, a component most pages use, dependencies or build config), when the spec's
acceptance criteria changed since the prior pass (`git diff <prior head_sha> HEAD -- <the spec
file>` adds, removes or rewords one), or when you cannot tell what a surface depends on.

## Re-run or carry

Derive the scenarios as §2.1 says, keeping the prior receipt's scenario ids for the ones it
already had. Then sort them:

- **Re-run** every scenario that failed or was blocked last time; every scenario whose surface the
  diff touches, counting the code it drives through and the shared code it depends on; and one
  load-bearing scenario that exercises the whole app as the smoke run.
- **Carry** a scenario that passed last time, on a surface the diff does not touch.

Drive the smoke scenario first. When it fails, file it as usual and run every scenario in full.

## Record what carried

A carried scenario is not driven. Record it in the receipt as `{"id": "<prior id>", "run":
"carried"}`; `flowctl qa receipt` copies its outcome, R-IDs, evidence and original head from the
prior receipt and refuses one that did not pass there. A criterion all of whose scenarios carried
reads `carried` in the coverage table. Never record a carried scenario as live.
