---
title: Unattended detection uses the full autonomy marker namespace
date: "2026-09-26"
track: knowledge
category: conventions
module: skills
tags: [autonomy, mode:autonomous, tracker-sync, flow-auto, defer]
applies_when: "writing skill prose that asks, confirms or defers, or an inline wrapper called from a lifecycle stage"
---

## Rule

A skill step that may ask a human first decides whether the run is attended, from the whole autonomy marker namespace: `FLOW_RALPH`, `REVIEW_RECEIPT_PATH`, `FLOW_AUTONOMOUS=1`, `AUTONOMOUS=1`, or a `mode:autonomous` token. The canonical list is in the flow skill's "Autonomy refusal" section. Unattended, it never prompts: it takes the documented deferral (`flowctl sync defer` for tracker conflicts, a typed `NEEDS_HUMAN` elsewhere) and continues.

## Why

Skills that run as inline wrappers inside a lifecycle stage (tracker-sync is the main one) see no arguments of their own, so a check on their own `$ARGUMENTS` misses the stage's `mode:autonomous`. `flow --auto` dispatches every stage with that token, so an inline wrapper must use the calling stage's autonomy. Variable names such as tracker-sync's `RALPH=1` mean "any unattended run", not Ralph only.

## How it surfaced

fn-255 R15a (2026-09-26) added an ask-or-overwrite choice for a diverged tracker body. The first draft keyed it on Ralph and missed `flow --auto` stages and `AUTONOMOUS=1`. Gordon caught it; the fix aligned tracker-sync with the namespace and routed unattended runs to `flowctl sync defer`.

## Applies when

Writing or reviewing any skill prose that asks, confirms, or defers; any inline wrapper called from plan, capture, work, make-pr, qa or land. Read how the sibling skills already handle the same choice before writing new prose.
