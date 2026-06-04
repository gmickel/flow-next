# Autoresearch — repo-scout (Tier 1)

Eval-driven optimization of `plugins/flow-next/agents/repo-scout.md` per Karpathy/autoresearch
methodology (olelehmann100kMRR/autoresearch-skill). Goal: **accuracy + token efficiency**.

Harness: the prompt-under-test is run as a read-only `Explore` subagent against a FROZEN snapshot
of this repo (HEAD of `opt/autoresearch-tier1`), on 3 fixed test inputs. Each output is scored
against 4 binary evals. One mutation at a time, keep-if-better-else-revert.

Files: test-inputs.md · evals.md · results.tsv · changelog.md · repo-scout.md.baseline
