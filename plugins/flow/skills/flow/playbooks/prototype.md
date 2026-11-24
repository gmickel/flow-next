# Prototype

When a design or behaviour choice can be settled by observing it—such as behaviour, output, timing, or layout—build the smallest thing that settles it rather than asking the person. Run a probe only when it is read-only or disposable; anything that needs live or shared state, credentials, network access, or a destructive action (a migration, deployment, or write to an outside system) is a question for the person when attended, and a stop explaining why when unattended.

Build in a throwaway location; the prototype is evidence, not a deliverable, and is discarded unless the person says to keep it. When comparing competing options, run them under the same data and conditions so the comparison is honest.

Show the observed result, record the decision and what ran under `## Decision Context` when working on a spec, and then route the real build.
