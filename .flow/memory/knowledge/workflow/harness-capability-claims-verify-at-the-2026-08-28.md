---
title: "Harness capability claims: verify at the installer, not the generator"
date: "2026-08-28"
track: knowledge
category: workflow
module: platforms
tags: [scouts, opencode, installers, negative-claims]
applies_when: "Harness capability claims: verify at the installer, not the generator"
---

## Problem
During fn-207, a research pass concluded "OpenCode never ships plugins/flow-next/docs/" after reading only `plugins/flow-next/scripts/lib/opencode_generate.py` (the agents/commands generator). The claim was false and briefly landed in a spec: `scripts/install-opencode.sh` copies four SUPPORT_DIRS (`scripts templates references docs`) to the config root at plugin-root geometry, so relative docs links resolve on OpenCode exactly as on the canonical tree (proven live via `--dest` scratch install).

## The rule
- A harness reach/capability question is answered by the DELIVERY path, not one component of it. For OpenCode that is `install-opencode.sh` (scatter + SUPPORT_DIRS + manifest); the Python generator only makes agents/commands. For Codex it is `sync-codex.sh` + `install-codex.sh`. For Cursor the installers/marketplace import. Read the installer header comments first - they document the layout contract.
- A NEGATIVE claim ("X never does Y", "Z is not shipped") needs the same evidence bar as a positive one: name the files searched and the terms used. Absence-of-evidence from one file is not evidence of absence for the harness.
- When dispatching a scout on a harness question, anchor the prompt to the capability area ("how does the OpenCode install deliver files"), never to a single file you guessed - the scout will answer the file, not the question.

## Where the truth lives
`plugins/flow-next/docs/platforms.md` § OpenCode "Installed layout" table is canonical for the scatter contents; the CLAUDE.md host-roster row restates it (kept in step as of fn-207).
