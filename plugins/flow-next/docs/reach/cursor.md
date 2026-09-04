# Reach: Cursor

How this harness obtains a model for a [tier](../orchestration.md#tiers-what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers-what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** - chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes, but an agent definition's model field is ignored** - subagents inherit the session model. The escape hatch is caller-side: name the model in the dispatch itself, and the harness honors it (it also self-corrects a near-miss identifier). There is no mechanism that rewrites an agent definition's model into this harness's own naming, and none is planned. |
| Shell out to another CLI | **Yes** - the harness runs shell commands, so any installed, authenticated CLI is reachable, including this harness's own. |

## What is unavailable

Model selection carried by an agent definition. Every other reach mechanism is present.

## Degradation

With no caller-side model in the dispatch, every tier resolves to the session model - which is exactly the shipped default and needs no configuration. When a tier matters here (a reviewer from a family that did not write the diff, most often), name the model in the dispatch or shell out; otherwise let it degrade and say so once.

## Models observed (2026-09-05)

Cursor does not serve GPT-6 Astra, and it will not serve later OpenAI models either: OpenAI is winding down its Cursor contract after the SpaceX acquisition, with a proposed shutoff of 12 November 2026 ([OpenAI's decision](https://openai.com/index/our-decision-on-cursor-following-its-acquisition-by-spacex/)). A cross-family review from inside Cursor therefore runs on the `host` backend with a non-OpenAI model on the `reviewer` tier, or on the `codex` CLI backend invoked from outside Cursor.

## Discover, then invoke

This harness's CLI lists the models it can reach, and that list moves - ask it immediately before pinning one in a dispatch rather than copying an identifier from a document.
