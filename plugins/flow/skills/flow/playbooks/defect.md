# Defect

Reproduce the failure before diagnosing or editing, on the surface the report names. Reading source can suggest a hypothesis, not confirm a cause. If the defect cannot be reproduced, stop, report what was tried, and do not ship a guessed fix.

When the report names several surfaces—such as a page and an API, or two platforms—verify every named surface before and after the fix; proving only the easiest surface misses broken siblings. Where the defect appears in a running app, reproduce and verify it live using `prove-live.md`.

Trace past the nearest symptom to confirm the underlying mechanism from runtime evidence, and decide whether the triggering state should legitimately occur before adding a guard or fallback. When two fixes built on the same idea have failed, question the idea before trying a third. Fix the cause with a test that fails on the unchanged code and passes after the fix (or, where no assertion test is practical, the same surface reproduction failing before and passing after). Commit the reproducing test before the fix so history shows it failing and then passing; if a hook or repository rule refuses a failing-test commit, commit them together without bypassing the hook. In the reply, state the failing run on base and the passing run on head, short and verbatim from runs already made.
