# Optional task decomposition and consistent spec-owned work

## Goal & Context
Make execution through Flow-Next work without a separate task-planning stage the recommended route for an implementation-ready, cohesive spec and a capable coding agent. Preserve planning where dependencies, separate ownership, staged delivery or execution constraints make decomposition useful. The spec remains the contract. This is a guidance-led change with bounded routing consistency fixes, not a new routing engine.

## Architecture & Data Models
Host agents judge spec readiness and the value of decomposition. Keep deterministic helpers responsible for durable state and truthful next-step facts. Reuse the existing no_plan choice and task machinery; add only minimal provenance if required to distinguish the direct owner from an intentional plan. Do not infer model identity or introduce capability classifiers, new configuration systems or new worker types.

## API Contracts
Keep work --no-plan and recorded spec intent explicit. Ordinary planned tasks and explicitly requested design reviews remain authoritative. A zero-task direct spec is work awaiting its implicit task, never an empty completed run. Keep next consumers fail-closed when a real task is not available.

## Edge Cases & Constraints
Cover flag-only and field-only entry, interactive and unattended continuation, duplicate mint, restart before/after claim, completion, stale direct flags on intentional plans, explicit plan-review requests, added requirements/tasks, unknown model identity, and unchanged configured review/QA/approval behavior. No fake SHIP statuses. Readiness is still an authorized signal, not an agent score. Implementation details may remain for the owner to resolve; unresolved material product or authority choices require spec refinement.

## Acceptance Criteria
- **R1:** Canonical routing guidance recommends Flow-Next work --no-plan for a ready cohesive spec where decomposition adds no coordination value. It explains when to refine the spec, review its design, plan dependencies, and verify the implementation. Risk or multi-file scope alone does not require task decomposition. Unknown model identity does not create a detector or blocking question. [user]
- **R2:** An accepted direct-route choice is durably carried through mint, resume and pilot continuation; subsequent ticks do not demand automatic plan-review merely because the implicit task now exists. Existing intentional plans, conflicting signals, explicit review requests and atomic duplicate-mint protections remain respected. No review verdict is fabricated to bypass routing. [user]
- **R3:** flowctl next reports an explicit zero-task direct spec consistently with the recorded route, with meaningful regression tests. Preserve explicitly requested plan-review and completion-review gates and make affected legacy consumers handle spec-level/no-task output safely. Do not modernize unrelated Ralph behavior. [user]
- **R4:** The implicit owner task retains the complete spec acceptance contract and normal configured implementation review, coverage, completion-review policy and QA behavior. Spec/design review can consume a spec without task files. Document QA's opt-in and draft-PR behavior accurately; claim no guarantee that review/QA removes every regression. [user]
- **R5:** Update current pipeline variations, guide, capture/interview/work/pilot guidance, orchestration/reference docs, README, glossary and strategy where affected. Name the route as execution through Flow-Next work, not ambiguous bare implementation. Public changelog may state that internal benchmarking showed the direct route can produce higher-scoring implementations with capable frontier models, with no private benchmark details or model-wide superiority claim. Preserve truthful historical release entries. [user]
- **R6:** Run focused behavioral tests and the repository final gates, regenerate required manifests and Codex mirrors twice for idempotency, validate links and affected installed consumer layouts, and complete configured implementation review on green source. Preserve G1/G2 and existing source/consumer ownership. [inferred]
- **R7:** Complete the maintainer-required downstream documentation chain in the same workstream, including the public docs site, methodology/onboarding material and canonical knowledge notes. Keep private/client material and benchmark details out of public outputs. Verify each affected property with its own build/check and retrieval requirements; report publication state separately from source completion. [user]

## Boundaries
No new model registry, readiness scorer, worker type, UI redesign, broad review redesign, lowered gates, changed QA defaults, fabricated performance guarantees or wholesale legacy-harness rewrite. No unrelated repository cleanup. Do not publish a new version before the release's actual gates. Private downstream policy and evidence stay outside public artifacts.

## Decision Context
The user approved this complete implementation and downstream work after an audit demonstrated route-choice persistence and pilot-prose gaps plus a deterministic next-selector mismatch. One owner coordinates the coherent change and may delegate bounded work across owned surfaces. Source review and behavioral evidence are independent of the choice to decompose tasks.

## Validation
Focused CLI lifecycle and review/coverage tests, full parallel repository suite, Ruff, generated mirror idempotency, documentation anchors and consumer-layout smoke. Public-site build/tests/link/SEO checks, rendered exports and appropriate local HTTP/browser verification. Downstream source/render parity and knowledge retrieval checks. Keep exact evidence and distinguish remaining blockers from completed checks.
