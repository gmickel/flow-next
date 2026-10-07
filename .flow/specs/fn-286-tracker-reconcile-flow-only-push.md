# Tracker reconcile flow-only push

## Goal & Context

GitHub issue #519 (reported by @TechupBusiness). With `tracker.perEvent.interview: reconcile`, refine's tracker step tells the agent the tracker-sync wrapper "makes exactly one lifecycle call: `tracker sync <spec> --op "$OP" --event interview <legal file flags>`". Followed literally after `--prepare`, the agent reconciles with the prepared tracker snapshot as `--body-file`, which the facade treats as the final tracker body. When only the local spec changed (`flow-only`), the call succeeds, both merge bases advance, and the issue keeps its pre-refine body; a later `sync-body --direction push` then reports `noop`. tracker-sync's own `steps.md` §4 already says the right thing: prepare first, and for reconcile's `flow-only` class call push without body inputs. Capture's and plan's tracker steps carry the same misleading "one call with `$OP`" wording.

## Acceptance Criteria

- **R1:** Refine's, capture's and plan's tracker steps direct the reconcile path through tracker-sync `steps.md` §4: prepare first, call `--op push` without body inputs on a `flow-only` classification with no genuine comments, and reconcile with the authored files otherwise. No error surface beyond the facade's existing results.

## Boundaries

- make-pr's tracker finalize keeps its body-preserving reconcile; it never overwrites issue prose.
- No facade change (no new warning or refusal).

## Decision Context

The facade already behaves as documented in tracker-sync's input matrix; the defect is in three call sites that paraphrase the call and drop §4's branch. Fixing the call sites is the smallest correct change. The reporter's optional facade warning is left out: the instructions now name the correct call, and a facade-level rule would have to exempt make-pr's deliberate body-preserving reconcile.
