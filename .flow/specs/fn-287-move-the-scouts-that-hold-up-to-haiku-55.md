# Move the scouts that hold up to Haiku 5.5

## Conversation Evidence

> user (turn 1): "haiku 5.5 is now out, figure out what this means for us. in terms of our scouts, any config stuff we have and ladders etc"
> user (turn 2): "but yes agree, do the mech changes and create a spec for the other stuff. there might be a subset of agents that we can switch"
> user (turn 3, part 1): "I sent one request with --model haiku and the override unset; Claude Code answered with claude-haiku-4-5-20251001. This build does know claude-haiku-5-5, but the bare alias doesn't point to it."
> user (turn 3, part 2): "If fn-287's eval should run on Haiku 5.5, name it explicitly (--model claude-haiku-5-5) rather than relying on the alias."

## Goal & Context
<!-- Source: 10% user / 40% [paraphrase] / 50% [inferred] -->

Claude Haiku 5.5 shipped on 2026-10-07. It is Anthropic's fastest model, and its input price is a twentieth of Sonnet 5.5's ($0.10 vs $2.00 per MTok for prompts up to 100K). It is also the first Haiku with effort levels. Every bundled scout, the flow gap analyst and plan-sync currently pin `sonnet`. Some of those agents may be able to move to `haiku` without missing what Sonnet finds, which would make scout-heavy steps such as prime and plan cheaper and faster. [paraphrase]

Haiku 5.5 still trails Sonnet 5.5 on agentic and terminal work:

| Benchmark | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| Terminal-Bench 4.0 | 39.2% | 70.6% |
| OSWorld 2.1 | 72.4% | 83.9% |
| GDPval-AA | 1620 | 1840 |

An earlier fact-scout evaluation found that the fastest tier at the time (Haiku 4.5) missed a load-bearing fact that the mid tier found on the same brief. A repin therefore waits for a measurement on flow-next's own scout work, and ships only for the agents that hold up. [inferred]

The work is for every flow-next user whose sessions dispatch the bundled scouts on Claude Code. [inferred]

## Architecture & Data Models
<!-- Source: 20% [paraphrase] / 80% [inferred] -->

- **Candidate agents.** There are two groups, and the change ships only for the agents in them that hold up. [paraphrase]
  - *Mechanical scanners:* prime's seven pillar scanners (build, env, observability, security, testing, tooling, workflow) and memory-scout. All eight pinned `haiku` until 6.4.0. [inferred]
  - *Retrieval scouts:* repo-scout, docs-scout, github-scout and practice-scout. [inferred]
- **Excluded.** Agents whose output is a judgment keep their current pin: spec-scout, claude-md-scout, docs-gap-scout, why-scout, flow-gap-analyst and plan-sync. quality-auditor stays on `opus`. The worker and the PR comment resolver keep inheriting the session model. [inferred]
- **Pin form (open).** The `haiku` alias resolves differently depending on the provider. On the Anthropic API, Claude Code 2.1.293 resolves it to Haiku 5.5 (probed 2026-10-07: the run was served by `claude-haiku-5-5`). Claude Code's model docs say it still resolves to Haiku 4.5 on Claude Platform on AWS, Amazon Bedrock, Google Cloud and Microsoft Foundry. A run elsewhere on the maintainer's machines also got Haiku 4.5. The explicit `claude-haiku-5-5` id reaches Haiku 5.5 on the Anthropic API, but it is not the provider-specific id those platforms use. Neither form reaches Haiku 5.5 for every user, so the pin form is a parked decision. [inferred]
- **Codex mirror.** The generator maps a `haiku` pin to the Codex fast tier, regardless of the intelligent-scouts list it applies to `sonnet` pins. Without a change, every repinned agent would move from the intelligent Codex model to the fast one, and this spec measures nothing on Codex. Generated Codex agents therefore keep their current model. The mirror stays generated from the canonical agent definitions and is never hand-edited. [inferred]
- **Measurement.** For each candidate agent, the eval runs both models on the same briefs against the same repositories. It records:
  - the findings each run produced, scored against the union of findings across both arms
  - wall time
  - token cost

  Each run records the model that actually served it, because an environment override can remap the `haiku` alias to another model. [inferred]

## Edge Cases & Constraints
<!-- Source: 100% [inferred] -->

- **Haiku 4.5 behind the alias.** Users who reach Claude through a third-party provider, and users on a Claude Code older than 2.1.293, get Haiku 4.5 from `haiku`, which scores 0.0% on Terminal-Bench 4.0. Haiku 5.5's results do not carry over to those users. [inferred]
- **User overrides.** A routing block's `fast scout` / `thinking scout` lines, or an explicit invocation argument, still override the agent default. So does a user's own environment mapping of the `haiku` alias. [inferred]
- **Effort.** Haiku 5.5 defaults to `medium` effort. The eval runs each agent at the effort it would ship with, so the measured quality is the quality users get. [inferred]

## Acceptance Criteria

- **R1:** An eval compares Sonnet 5.5 and Haiku 5.5 on every candidate agent, using the same briefs and repositories, and names Haiku 5.5 by its explicit id rather than the alias. It records findings, wall time and token cost per agent and per arm, plus the model that served each run. Errors: a run served by a model other than its arm's model is discarded and re-run. A run that fails or times out counts as a miss for its arm and is never silently dropped. [inferred]
- **R2:** An agent moves to `haiku` only when its Haiku arm loses no load-bearing finding that its Sonnet arm found, across replicated runs; otherwise it stays on `sonnet`. The eval record keeps negative results, including agents that did not hold. If no candidate holds, no pin changes. [inferred]
- **R3:** Excluded agents keep their pins: spec-scout, claude-md-scout, docs-gap-scout, why-scout, flow-gap-analyst, plan-sync and quality-auditor. The worker and the PR comment resolver still inherit the session model (no error surface beyond the agent definitions). [inferred]
- **R4:** User-facing docs that name scout tiers state which agents run on Haiku, and which Claude Code versions and providers get Haiku 5.5 from the shipped pin. That covers the orchestration tier table and its rationale, and the flow-next.dev pages that repeat them. The CHANGELOG entry for the release does the same (no error surface beyond R2's outcome). [inferred]
- **R5:** Every generated Codex agent keeps its current model, including the repinned ones. A clean regeneration matches the committed mirror byte for byte (no error surface beyond the mirror freshness check). [strategy:Cross-platform parity]

## Boundaries

- No new routing mechanism, config key, or model-selection logic; this spec changes default pins only. [inferred]
- No change to the generated Codex agents' models. [inferred]

## Decision Context
<!-- Source: 30% [paraphrase] / 70% [inferred] -->

Two other options were considered:

- *Repin from the published benchmarks:* rejected, because the Terminal-Bench gap is in the dimension scouting depends on, and the last fast-tier eval on scout work found a load-bearing miss. [inferred]
- *Repin the whole fleet:* rejected, because judgment scouts degrade most on a fast tier. [inferred]

Gating the repin on a per-agent eval keeps the savings where they are real. The maintainer agreed to track this separately from the mechanical ladder update (the review ladders and the Copilot triage judge gaining Haiku 5.5), which shipped on its own. [paraphrase]

The existing pins use aliases, which follow future releases. For Haiku, though, the alias lags on third-party providers, so the choice of pin form is parked below rather than assumed. [inferred]

## Parked unknowns

- **Pin form.** Should repinned agents use the `haiku` alias, which gives third-party-provider users Haiku 4.5, or the explicit `claude-haiku-5-5` id, whose behavior on providers that need provider-specific ids is unverified? Or should the repin wait until the alias moves on every provider? Resolved by the maintainer's choice, informed by a probe of the explicit id on one third-party provider. [inferred]

## Strategy Alignment

Serves **Cross-platform parity**: the canonical agent definitions stay the single source, and the Codex mirror stays generated from them (R5). [strategy:Cross-platform parity]

## Strategy Conflicts

None found.
