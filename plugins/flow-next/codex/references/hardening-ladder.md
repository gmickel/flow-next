# Hardening ladder

Read when a mistake agents keep repeating is to become something that fails instead of advice
that can be skipped: flow's repeated-mistake route, or audit's Harden path.

Assume the next contributor is an agent that sees only the files it opened, copies the nearest
example, and takes the shortest path that compiles. A change that looks right from one file
should be right for the whole repository.

## A class, not an instance

A mistake class counts once it has two recorded occurrences: reverts, fixes that re-land,
review remarks, memory entries re-taught, comments that exist to excuse a workaround. One
occurrence is a defect; fix it as one.

## Fix each class at the highest level that works

1. **Remove the opening.** Give each piece of state one owner and each task one supported way.
   Make internals unreachable from outside their module, so the wrong import fails. Keep one
   list and derive every other copy from it, or make the build fail when copies disagree.
   Delete the old way an agent would copy.
2. **Make the bad state unwritable** with the type system, where the language has one.
3. **A lint or CI check whose message names the fix.** "`retry_jitter` is not in
   `settings.schema.json`; add it there and read it through `settings.get()`" teaches the next
   agent; "invalid key" does not. When the pattern is already common, fail only when a change
   adds a new occurrence.
4. **A behaviour test** that fails on the recorded occurrence.
5. **Instruction text, last,** and only for a class that needs judgment no check can encode.
   Write it with an example of the failure. Nothing fails when an agent skips it.

Say why a higher level did not work when you settle for a lower one.

## Prove each check

- Run the new check against a recorded past occurrence (check out or replay the commit that made
  the mistake) and see it fail; then see it pass on the fixed tree. A check that never failed on
  a real occurrence is not proven.
- The check runs through the same command locally and in CI.
- An exception sits on the offending line with its reason, an expiry date and the person who
  approved it.
