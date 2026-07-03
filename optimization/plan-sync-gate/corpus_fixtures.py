#!/usr/bin/env python3
"""Declarative drift-POSITIVE fixture table for the plan-sync gate corpus.

Consumed by builders.py (`build_fixture`). Each fixture:
  seed:  {path: content} committed as the pre-task state
  work:  ordered commit steps: {"msg", "write": {path: content},
         "mv": [[old, new]], "rm": [path]}
  flow:  spec/task/downstream markdown + optional other_specs
`{head}` in the task markdown is substituted with the real head SHA.
APPEND-ONLY like scenarios.json — see README.md.
"""

from __future__ import annotations


_SPEC_MD_TEMPLATE = """# {title}

## Overview

{overview}

## Approach

{approach}

## Acceptance Criteria

- **R1:** {r1}
"""


def _task_md(description: str, files_line: str, acceptance: str,
             done_summary: str, inv_targets: str = "") -> str:
    inv = ("\n## Investigation targets\n\n" + inv_targets + "\n") if inv_targets else ""
    return (
        "## Description\n\n" + description + "\n\n"
        + "**Size:** S\n**Files:** " + files_line + "\n" + inv
        + "\n## Acceptance\n\n- [x] " + acceptance + "\n"
        + "\n## Done summary\n" + done_summary + "\n"
        + "\n## Evidence\n- Commits: {head}\n- Tests: none\n- PRs:\n"
    )


def _downstream_md(description: str, files_line: str, body: str,
                   acceptance: str) -> str:
    return (
        "## Description\n\n" + description + "\n\n"
        + "**Size:** S\n**Files:** " + files_line + "\n\n"
        + body + "\n"
        + "\n## Acceptance\n\n- [ ] " + acceptance + "\n"
        + "\n## Done summary\nTBD\n\n## Evidence\n- Commits:\n- Tests:\n- PRs:\n"
    )


FIXTURES: dict = {
    "pos_rename_morph": {
        "seed": {
            "src/auth/handler.py": (
                "def alpha_handler(request):\n"
                "    raise NotImplementedError  # implemented by fn-9.1\n"
            ),
            "src/cli/main.py": "def main():\n    return 0\n",
        },
        "work": [{
            "msg": "feat(auth): request handler (fn-9.1)",
            "write": {
                "src/auth/handler.py": (
                    "def alpha_handler_v2(request):\n"
                    "    return {\"ok\": True, \"who\": request}\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Auth handler pipeline",
            "spec_overview": "Add the auth request handler and wire the CLI to it.",
            "spec_approach": "fn-9.1 implements `alpha_handler` in src/auth/handler.py; fn-9.2 wires the CLI entrypoint to it.",
            "spec_r1": "CLI requests are served through the auth handler.",
            "task_md": _task_md(
                "Implement `alpha_handler(request)` in `src/auth/handler.py` returning an ok-dict.",
                "`src/auth/handler.py`",
                "alpha_handler returns an ok-dict for a request",
                "Implemented the handler as `alpha_handler_v2` (renamed during implementation — the v1 name was reserved by a legacy shim).",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Wire the CLI entrypoint to the auth handler.",
                    "`src/cli/main.py`",
                    "Call alpha_handler from `main()` and print the ok flag.",
                    "CLI calls the handler and prints ok",
                ),
            },
        },
    },
    "pos_rename_plainword": {
        "seed": {
            "src/reader.py": "def parse(line):\n    return line\n",
            "src/cli/table.py": "def rows():\n    return []\n",
        },
        "work": [{
            "msg": "feat(reader): line reader (fn-9.1)",
            "write": {
                "src/reader.py": "def read(line):\n    return line\n",
            },
        }],
        "flow": {
            "spec_title": "fn-9 Line reader",
            "spec_overview": "Provide a line reader consumed by the CLI table view.",
            "spec_approach": "fn-9.1 ships the reader in src/reader.py; fn-9.2 renders its output as a table.",
            "spec_r1": "Reader output renders in the CLI table.",
            "task_md": _task_md(
                "Implement the line helper named `parse` in `src/reader.py`.",
                "`src/reader.py`",
                "the helper accepts a line and returns it",
                "Shipped the helper but named it `read` instead of `parse` (matches the sibling io module naming).",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Render reader output as a CLI table.",
                    "`src/cli/table.py`",
                    "Feed each line through the parse helper before adding it as a row.",
                    "table rows come from the helper output",
                ),
            },
        },
    },
    "pos_api_signature_invtargets": {
        "seed": {
            "src/api/users.py": (
                "def fetch_user(user_id):\n"
                "    return {\"id\": user_id}\n"
            ),
            "src/web/routes.py": "ROUTES = []\n",
        },
        "work": [{
            "msg": "feat(api): scoped user fetch (fn-9.1)",
            "write": {
                "src/api/users.py": (
                    "def fetch_user(user_id, *, scope):\n"
                    "    return {\"id\": user_id, \"scope\": scope}\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 User API",
            "spec_overview": "Serve user records to the web routes.",
            "spec_approach": "fn-9.1 hardens fetch_user; fn-9.2 mounts the web route on top of it.",
            "spec_r1": "Web route returns the user record.",
            "task_md": _task_md(
                "Harden `fetch_user(user_id)` in `src/api/users.py` (validation only, keep the signature).",
                "`src/api/users.py`",
                "fetch_user returns the user dict",
                "Added a REQUIRED keyword-only `scope` parameter while hardening — callers must now pass scope explicitly (beyond the task's keep-the-signature instruction).",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Mount the user web route.",
                    "`src/web/routes.py`",
                    "Route handler delegates to the user fetch API.",
                    "GET route returns the user record",
                    ),
            },
        },
        "downstream_inv_targets": {
            "fn-9.2": "**Required:**\n- `src/api/users.py:1-30` (call shape to preserve)",
        },
    },
    "pos_deviation_only": {
        "seed": {
            "src/cache/store.py": "RESULTS = {}\n",
            "src/report/gen.py": "def weekly():\n    return \"report\"\n",
        },
        "work": [{
            "msg": "feat(cache): result store (fn-9.1)",
            "write": {
                "src/cache/store.py": (
                    "import json\n\n"
                    "PATH = \"var/results.json\"\n\n\n"
                    "def put(key, value):\n"
                    "    data = {key: value}\n"
                    "    with open(PATH, \"w\") as fh:\n"
                    "        json.dump(data, fh)\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Result cache",
            "spec_overview": "Cache computed results for the weekly report.",
            "spec_approach": "fn-9.1 keeps results in process memory; fn-9.2 renders the weekly report from them.",
            "spec_r1": "Weekly report renders from cached results.",
            "task_md": _task_md(
                "Cache computed results IN PROCESS MEMORY (a module-level dict; no persistence, no writes outside the process).",
                "`src/cache/store.py`",
                "results are served from process memory",
                "Persisted results to a JSON file on disk instead of process memory — restarts were losing results, so the store now survives them.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Render the weekly report.",
                    "`src/report/gen.py`",
                    "The generator assumes results live in process memory and are dropped on restart; render whatever the current process computed.",
                    "weekly report renders the current run only",
                ),
            },
        },
    },
    "pos_acceptance_semantics": {
        "seed": {
            "src/report/render.py": (
                "def render_summary(items):\n"
                "    return \"\\n\".join(items)\n"
            ),
            "src/notify/mail.py": "def send(body):\n    return True\n",
        },
        "work": [{
            "msg": "feat(report): structured summary (fn-9.1)",
            "write": {
                "src/report/render.py": (
                    "import json\n\n"
                    "__all__ = [\"render_summary\"]\n\n\n"
                    "def render_summary(items):\n"
                    "    return json.dumps({\"items\": items})\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Summary rendering",
            "spec_overview": "Render run summaries and mail them.",
            "spec_approach": "fn-9.1 renders plain-text summaries; fn-9.2 mails them line by line.",
            "spec_r1": "Summaries reach the mailer.",
            "task_md": _task_md(
                "`render_summary(items)` returns PLAIN TEXT, one item per line.",
                "`src/report/render.py`",
                "render_summary returns newline-joined plain text",
                "render_summary now returns a JSON document (structured consumers wanted machine-readable output) — NOT the plain text lines the spec described.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Mail the rendered summary.",
                    "`src/notify/mail.py`",
                    "Split the plain-text output of render_summary on newlines and mail each line.",
                    "parses the plain-text output of render_summary into mail lines",
                ),
            },
        },
    },
    "pos_file_rename_planned": {
        "seed": {
            "src/mod/alpha.py": "def entry():\n    return 1\n",
            "src/app/boot.py": "def boot():\n    return None\n",
        },
        "work": [{
            "msg": "refactor(core): relocate alpha module (fn-9.1)",
            "mv": [["src/mod/alpha.py", "src/core/alpha_core.py"]],
        }],
        "flow": {
            "spec_title": "fn-9 Core relocation",
            "spec_overview": "Move the alpha module into core, then extend it.",
            "spec_approach": "fn-9.1 relocates src/mod/alpha.py to src/core/alpha_core.py mechanically; fn-9.2 extends the module.",
            "spec_r1": "Alpha module lives under src/core/.",
            "task_md": _task_md(
                "Move `src/mod/alpha.py` to `src/core/alpha_core.py`. Mechanical move, no content changes.",
                "`src/mod/alpha.py`, `src/core/alpha_core.py`",
                "module relocated, git history preserved",
                "Moved exactly as planned; no content changes.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Extend the alpha module entry point.",
                    "`src/mod/alpha.py`",
                    "Add a second entry to the module (written before the relocation landed).",
                    "second entry point available",
                ),
            },
        },
    },
    "pos_cross_spec": {
        "seed": {
            "src/pipeline/dispatch.py": (
                "def dispatch(job):\n"
                "    return job\n"
            ),
            "src/docs/notes.py": "NOTES = []\n",
        },
        "work": [{
            "msg": "feat(pipeline): priority dispatch (fn-9.1)",
            "write": {
                "src/pipeline/dispatch.py": (
                    "def dispatch(job, priority=0):\n"
                    "    return (priority, job)\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Dispatch priorities",
            "spec_overview": "Add priorities to the pipeline dispatcher.",
            "spec_approach": "fn-9.1 adds priority dispatch; fn-9.2 documents it.",
            "spec_r1": "Jobs dispatch with priorities.",
            "task_md": _task_md(
                "Add priority support to `dispatch(job)` in `src/pipeline/dispatch.py`.",
                "`src/pipeline/dispatch.py`",
                "dispatch accepts a priority",
                "dispatch now returns a (priority, job) tuple instead of the bare job — the return SHAPE changed beyond the task wording.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Document the dispatcher.",
                    "`src/docs/notes.py`",
                    "Write usage notes for the docs module.",
                    "notes cover the dispatcher",
                ),
            },
            "other_specs": {
                "fn-10": (
                    "open",
                    "# fn-10 Batch runner\n\n## Overview\n\n"
                    "Run batches through the pipeline.\n\n## Approach\n\n"
                    "Consume the dispatcher in `src/pipeline/dispatch.py` — the runner "
                    "treats its return value as the job itself.\n",
                ),
            },
        },
    },
    "pos_prose_shared_contract": {
        "seed": {
            "src/auth/result.py": (
                "class AuthResult:\n"
                "    def __init__(self, token):\n"
                "        self.token = token\n\n\n"
                "def login(tok):\n"
                "    return AuthResult(token=tok)\n"
            ),
            "src/session/mgr.py": "SESSIONS = {}\n",
        },
        "work": [{
            "msg": "feat(auth): rename credential field (fn-9.1)",
            "write": {
                "src/auth/result.py": (
                    "class AuthResult:\n"
                    "    def __init__(self, access_token):\n"
                    "        self.access_token = access_token\n\n\n"
                    "def login(tok):\n"
                    "    return AuthResult(access_token=tok)\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Auth result contract",
            "spec_overview": "Ship the login result object consumed by sessions.",
            "spec_approach": "fn-9.1 ships AuthResult with a `token` field; fn-9.2 persists it in the session manager.",
            "spec_r1": "Login yields a persistable credential.",
            "task_md": _task_md(
                "Ship `AuthResult` with a `token` attribute in `src/auth/result.py`.",
                "`src/auth/result.py`",
                "login returns AuthResult with the credential",
                "Renamed the field to `access_token` (OAuth vocabulary) — AuthResult.token no longer exists.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Persist login credentials in the session manager.",
                    "`src/session/mgr.py`",
                    "After login, persist the AuthResult.token value into the session map.",
                    "session map holds the credential",
                ),
            },
        },
    },
    "pos_schema_key_rename": {
        "seed": {
            "src/api/serialize.py": (
                "def to_wire(user):\n"
                "    return {\"user_id\": user[\"id\"], \"name\": user[\"name\"]}\n"
            ),
            "src/client/sdk.py": "def get(url):\n    return {}\n",
        },
        "work": [{
            "msg": "feat(api): compact wire form (fn-9.1)",
            "write": {
                "src/api/serialize.py": (
                    "def to_wire(user):\n"
                    "    return {\"uid\": user[\"id\"], \"name\": user[\"name\"]}\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Wire schema",
            "spec_overview": "Serialize users for the client SDK.",
            "spec_approach": "fn-9.1 ships the wire serializer; fn-9.2 parses it in the SDK.",
            "spec_r1": "SDK round-trips a user record.",
            "task_md": _task_md(
                "Serialize users with a `user_id` key in `src/api/serialize.py`.",
                "`src/api/serialize.py`",
                "wire dict carries the user id",
                "Shipped the wire key as `uid` instead of `user_id` (payload-size review) — the wire schema differs from the spec.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Parse wire users in the client SDK.",
                    "`src/client/sdk.py`",
                    "Expected payload:\n\n```json\n{\"user_id\": 7, \"name\": \"ada\"}\n```",
                    "SDK reads the id from the wire dict",
                ),
            },
        },
    },
    "pos_dir_restructure_planned": {
        "seed": {
            "src/util/strings.py": "def slug(s):\n    return s\n",
            "src/util/dates.py": "def today():\n    return \"2026-07-03\"\n",
            "src/app/main.py": "def run():\n    return 0\n",
        },
        "work": [{
            "msg": "refactor(common): consolidate helpers (fn-9.1)",
            "mv": [
                ["src/util/strings.py", "src/common/strings.py"],
                ["src/util/dates.py", "src/common/dates.py"],
            ],
        }],
        "flow": {
            "spec_title": "fn-9 Helper consolidation",
            "spec_overview": "Consolidate scattered helpers under src/common/.",
            "spec_approach": "fn-9.1 moves the src/util/ helpers to src/common/ mechanically; fn-9.2 rewires the app imports.",
            "spec_r1": "Helpers live under src/common/.",
            "task_md": _task_md(
                "Move both helper modules from `src/util/` to `src/common/`. Mechanical move only.",
                "`src/util/strings.py`, `src/util/dates.py`, `src/common/strings.py`, `src/common/dates.py`",
                "helpers relocated",
                "Moved exactly as planned; no content changes.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Rewire app imports to the helpers.",
                    "`src/app/main.py`",
                    "Import the helpers from `src/util/` into the app entrypoint (written before the consolidation landed).",
                    "app imports resolve",
                ),
            },
        },
    },
    "pos_glossary_rename": {
        "seed": {
            "src/loop/engine.py": (
                "def start():\n"
                "    return None  # loop engine lands in fn-9.1\n"
            ),
            "GLOSSARY.md": (
                "# Glossary\n\n"
                "## Feedback Loop\n"
                "The periodic re-evaluation pass that re-reads collected "
                "signals and re-plans the batch.\n\n"
                "_Avoid_: polling cycle, tick\n"
            ),
        },
        "work": [{
            "msg": "feat(loop): feedback loop engine (fn-9.1)",
            "write": {
                "src/loop/engine.py": (
                    "def run_feedback_loop(signals):\n"
                    "    return list(signals)\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Loop engine",
            "spec_overview": "Ship the signal re-evaluation engine.",
            "spec_approach": "fn-9.1 starts a new polling cycle after each batch; fn-9.2 adds backoff to it.",
            "spec_r1": "Signals are re-evaluated after every batch.",
            "task_md": _task_md(
                "Start a new polling cycle after each batch in `src/loop/engine.py`.",
                "`src/loop/engine.py`",
                "each batch triggers a re-evaluation pass",
                "Implemented as `run_feedback_loop` — the glossary's canonical term (the spec's 'polling cycle' is a listed avoid-alias).",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Add backoff to the loop.",
                    "`src/loop/engine.py`",
                    "Extend the polling cycle with exponential backoff between batches.",
                    "backoff applied between batches",
                ),
            },
        },
    },
    "pos_multi_commit_fix_loop": {
        "seed": {
            "src/billing/calc.py": (
                "def compute_total(lines):\n"
                "    return sum(lines)\n"
            ),
            "src/invoice/pdf.py": "def render(total):\n    return b\"\"\n",
        },
        "work": [
            {
                "msg": "feat(billing): grand total (fn-9.1)",
                "write": {
                    "src/billing/calc.py": (
                        "def compute_grand_total(lines, tax=0):\n"
                        "    return sum(lines) + tax\n"
                    ),
                },
            },
            {
                "msg": "fix: review notes r1 (fn-9.1)",
                "write": {"notes/review.md": "r1: naming approved\n"},
            },
            {
                "msg": "fix: review notes r2 (fn-9.1)",
                "write": {"notes/followup.md": "r2: follow-up logged\n"},
            },
        ],
        "flow": {
            "spec_title": "fn-9 Billing totals",
            "spec_overview": "Compute invoice totals.",
            "spec_approach": "fn-9.1 ships the total computation; fn-9.2 renders it into the invoice PDF.",
            "spec_r1": "Invoice shows the computed total.",
            "task_md": _task_md(
                "Implement `compute_total(lines)` in `src/billing/calc.py`.",
                "`src/billing/calc.py`",
                "total computed from line amounts",
                "Renamed to `compute_grand_total(lines, tax=0)` while adding tax support (review rounds 1-2 only touched notes).",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Render the total into the invoice PDF.",
                    "`src/invoice/pdf.py`",
                    "Sum via `compute_total` and place the figure in the PDF footer.",
                    "PDF footer shows the total",
                ),
            },
        },
    },
    "pos_config_key_rename": {
        "seed": {
            "src/config/loader.py": (
                "DEFAULTS = {\"retry_max\": 3}\n\n\n"
                "def load():\n"
                "    return dict(DEFAULTS)\n"
            ),
            "src/net/client.py": "def call():\n    return 200\n",
        },
        "work": [{
            "msg": "feat(config): retry settings (fn-9.1)",
            "write": {
                "src/config/loader.py": (
                    "DEFAULTS = {\"max_retries\": 3}\n\n\n"
                    "def load():\n"
                    "    return dict(DEFAULTS)\n"
                ),
            },
        }],
        "flow": {
            "spec_title": "fn-9 Retry configuration",
            "spec_overview": "Configurable network retries.",
            "spec_approach": "fn-9.1 ships the retry_max setting; fn-9.2 documents the setup command.",
            "spec_r1": "Retries are configurable.",
            "task_md": _task_md(
                "Ship the `retry_max` setting in `src/config/loader.py`.",
                "`src/config/loader.py`",
                "retry ceiling configurable",
                "Shipped the key as `max_retries` instead of `retry_max` (house naming) — setup commands using the old key are now no-ops.",
            ),
            "downstream": {
                "fn-9.2": _downstream_md(
                    "Document client setup.",
                    "`src/net/client.py`",
                    "Setup command to document:\n\n```bash\nmytool set retry_max=5\n```",
                    "setup docs configure retries",
                ),
            },
        },
    },
}
