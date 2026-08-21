# Project Glossary

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


`GLOSSARY.md` is a human-readable, project-canonical terminology file shipped in v0.39.0. Lives at the **repo root** (and optionally subdirectories), NOT inside `.flow/`. Survives `rm -rf .flow/` — terminology is the project's, not flow-next's.

> Vocabulary discipline for this repo: [`../../../GLOSSARY.md`](https://github.com/gmickel/flow-next/blob/main/GLOSSARY.md) — a compact dictionary of load-bearing terms with `_Avoid_` aliases, not an encyclopedia (its retired long-form text is archived at [`../../../agent_docs/archive/GLOSSARY-full.md`](https://github.com/gmickel/flow-next/blob/main/agent_docs/archive/GLOSSARY-full.md)).
> Glossary files are written/maintained via the `flowctl glossary` subcommands (`add` / `list` / `read` / `remove`), driven by `/flow-next:interview`, `/flow-next:audit`, and `/flow-next:sync`. (There is no standalone `flow-next-glossary` skill — `flowctl glossary` is the mechanism.)

## Format

H2-per-term markdown aligned with `open-gitops/documents` and `glossarify-md` so generic markdown tooling reads it cleanly. Optional `_Avoid_:` and `_Relates to_:` italic lines surface aliases and cross-references. Multi-line definitions are supported; fenced code blocks inside definitions are masked during parse so example terms in code don't get parsed as headings.

## Resolution

Nearest-ancestor walk from cwd up to repo root, first match wins (same shape as `tsconfig.json` / EditorConfig). Capped at 32 levels with cycle detection.

## Subcommands

```bash
# Add or update a term — single-line, file, or stdin
flowctl glossary add <term> --definition "Short definition."
flowctl glossary add <term> --definition-file body.md
flowctl glossary add <term> --definition-file -

# Optional alias / relates-to flags
flowctl glossary add <term> --definition "..." --avoid "alt1,alt2" --relates-to "x,y"

# List defined terms (grouped by file, nearest first)
flowctl glossary list                # text mode
flowctl glossary list --json         # {groups, file_count, total_terms}

# Read a term — walks ancestors, first match wins
flowctl glossary read <term>
flowctl glossary read <term> --json  # {path, term, definition, avoid, relates_to}

# Remove a term — last-term remove leaves an `# Glossary` H1 husk on disk
flowctl glossary remove <term>
```

## Husk semantics

Last-term `remove` leaves a `# Glossary` H1 husk on disk — the file is **never** deleted. R18 (survives uninstall) covers both the file living outside `.flow/` AND the file persisting after the last term is removed. Doc-aware autodetect branches on `total_terms > 0`, not on `[[ -f GLOSSARY.md ]]` — the latter would falsely activate doc-aware mode on an empty husk.

## How the rest of flow-next uses it

- **`/flow-next:interview`** doc-aware mode (autodetect when `total_terms > 0` or `knowledge/decisions/` is non-empty): looks up canonical wording before terminology questions; surfaces user-vs-canonical conflicts to a `## Glossary Conflicts` spec section; writes new terms via `flowctl glossary add` when the user picks update-glossary.
- **`/flow-next:audit`** Phase 0.5: walks every `GLOSSARY.md` on the ancestor chain and audits each term against the current code (any references intact? renamed? gone?).
- **`/flow-next:sync`** Phase 3b.1: glossary renames replace `_Avoid_` aliases with the canonical term inline across downstream task specs, with a `<!-- Updated by plan-sync: glossary rename ... -->` breadcrumb.
- **`docs-gap-scout`** in the planning phase: reads `GLOSSARY.md` on the ancestor chain to surface canonical terminology in the planning context; flags terminology mismatches between the proposed feature description and the glossary.

## Forbidden vocabulary (R17)

A small list of jargon terms is grep-guarded out of canonical skill / agent / command / flowctl prose by `ci_test.sh` section 5c (canonical scan, prints `file:line` on hit), and out of the Codex mirror by `scripts/sync-codex.sh` validation block (mirror scan, prints count + remediation hint). The forbidden list is enumerated only inside the grep pattern itself; documentation refers to "the R17 forbidden list" without re-enumeration to avoid teaching the very vocabulary it's meant to suppress.

## See also

- [`../../../GLOSSARY.md`](https://github.com/gmickel/flow-next/blob/main/GLOSSARY.md) — this repo's own glossary: 18 load-bearing terms (Spec, Task, R-ID, Receipt, Gate, plan-sync, Tier, Reach, ...) with `_Avoid_` aliases. Long-form text: [`../../../agent_docs/archive/GLOSSARY-full.md`](https://github.com/gmickel/flow-next/blob/main/agent_docs/archive/GLOSSARY-full.md).
- [`strategy.md`](strategy.md) — peer doc for the repo-root `STRATEGY.md` file.
- [`memory-schema.md`](memory-schema.md) — categorized memory schema; the `knowledge/decisions/` subtree pairs naturally with glossary as terminology + load-bearing choices.
