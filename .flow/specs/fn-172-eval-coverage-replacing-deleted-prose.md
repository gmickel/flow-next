# Eval coverage for skill behaviors that lost prose-pin tests (STUB)

## Goal & Context
<!-- scope: business -->

STUB - direction is likely ad-hoc eval-suite building by the maintainer; this spec parks the idea and the grounding so it isn't lost. Supersede or absorb freely.

The 2026-08-07 cleanup deleted ~150 sentence-level prose assertions (commits 1fb48680, 2e056636). Per the same-session 4-agent census, ~130-140 were "quality pins" - the skill must still TEACH a behavior - which grep cannot judge. `.flow/criteria.md` G2 now forbids re-pinning prose. The intents deserve coverage again; the instrument is behavioral evals per `agent_docs/optimizing-skills.md` (frozen fixtures + binary checks + answer keys, on-demand, never CI).

Candidate clusters, from the census's worst deleted offenders:
1. Parallel-work conductor eval (was test_parallel_work_prose.py): claim-before-dispatch, no-worker-done, join-then-verify, shared-file serialization, handover fields.
2. Capture contract evals (extend the existing capture eval suite): compaction refusal, readiness-offer gating, readback print-before-ask.
3. Prime negative-control eval: never recommends test-running pre-commit hooks; headroom warns, never blocks.

## Boundaries
<!-- scope: business -->

- Never wired into CI or the unit suite (CI stays deterministic and fast).
- No prose pins in any form (G2).
- Cluster-B/D token pins stay deterministic - out of scope.

## Decision Context
<!-- scope: both -->

Parked as a stub 2026-08-07: maintainer leaning toward building a general eval suite ad-hoc rather than executing this as a planned spec. If that happens, close this spec against that work.
