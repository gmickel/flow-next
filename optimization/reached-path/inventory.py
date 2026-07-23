"""B0 fixture inventory for reached-path baselines (fn-130.1).

Each fixture is a sanitized branch description. Answer-key conclusions live
only under ``oracles`` / scorer side — never in subject-visible prompt text.
Hashes are filled by ``freeze_b0`` from ``git show BASELINE_COMMIT:<path>``
(not the live worktree).
"""

from __future__ import annotations

from typing import Any

BASELINE_COMMIT = "1e8d3a95cf12cf1f33fa5c6c7ee50e0998e04e4b"
B1_COMMIT = "8ed71a73ccc593a8a018dcdb805a86f396dcf76f"

# Canonical skill roots (repo-relative).
S = {
    "setup": "plugins/flow-next/skills/flow-next-setup",
    "tracker": "plugins/flow-next/skills/flow-next-tracker-sync",
    "prime": "plugins/flow-next/skills/flow-next-prime",
    "plan_review": "plugins/flow-next/skills/flow-next-plan-review",
    "plan": "plugins/flow-next/skills/flow-next-plan",
    "work": "plugins/flow-next/skills/flow-next-work",
    "strategy": "plugins/flow-next/skills/flow-next-strategy",
    "make_pr": "plugins/flow-next/skills/flow-next-make-pr",
    "pilot": "plugins/flow-next/skills/flow-next-pilot",
}

TRACKER_COMMON = [
    f"{S['tracker']}/SKILL.md",
    f"{S['tracker']}/steps.md",
    f"{S['tracker']}/references/adapter-interface.md",
    f"{S['tracker']}/references/body-merge.md",
    f"{S['tracker']}/references/status-sync.md",
    f"{S['tracker']}/references/comments-sync.md",
    f"{S['tracker']}/references/identity.md",
]
TRACKER_ADAPTERS = {
    "linear_mcp": [
        f"{S['tracker']}/references/linear-ladder.md",
        f"{S['tracker']}/references/linear-mcp.md",
    ],
    "linear_graphql": [
        f"{S['tracker']}/references/linear-ladder.md",
        f"{S['tracker']}/references/linear-graphql.md",
    ],
    "github": [f"{S['tracker']}/references/github.md"],
    "gitlab": [f"{S['tracker']}/references/gitlab.md"],
    "jira": [f"{S['tracker']}/references/jira.md"],
}
ALL_TRACKER_ADAPTER_FILES = sorted(
    {p for paths in TRACKER_ADAPTERS.values() for p in paths}
)


# Deterministic B0 freeze provenance — these manifests are inventory hashes,
# not captured backend executions. Live smoke records use capture_kind=backend_run.
PROVENANCE_DETERMINISTIC_FREEZE = {
    "capture_kind": "deterministic_freeze",
    "capture_reason": (
        "route_manifest_inventory_hash_only; not a backend execution "
        "(model/cli_version intentionally null)"
    ),
    "model": None,
    "cli_version": None,
}


def _mirror_paths(canonical_paths: list[str], mirror_skill: str) -> list[str]:
    """Rewrite canonical skill paths to the regenerated Codex mirror tree."""
    # canonical: plugins/flow-next/skills/<name>/...
    # mirror:    plugins/flow-next/codex/skills/<name>/...
    prefix = "plugins/flow-next/skills/"
    out: list[str] = []
    for p in canonical_paths:
        if p.startswith(prefix):
            rest = p[len(prefix) :]  # <name>/...
            _name, _, tail = rest.partition("/")
            out.append(f"{mirror_skill.rstrip('/')}/{tail}" if tail else mirror_skill.rstrip("/"))
        else:
            out.append(p)
    return out


def _fx(
    fixture_id: str,
    cluster: str,
    *,
    skill: str,
    host: str = "claude",
    activation_form: str = "slash",
    args: list[str] | None = None,
    branch_inputs: dict[str, Any] | None = None,
    required_reads: list[str] | None = None,
    forbidden_reads: list[str] | None = None,
    prompt_files: list[str] | None = None,
    oracles: dict[str, Any] | None = None,
    mutation_targets: dict[str, Any] | None = None,
    sealed_holdout: bool = False,
    subjective: bool = False,
    borderline: bool = False,
    notes: str = "",
    mirror_skill: str | None = None,
) -> dict[str, Any]:
    req = list(required_reads or [])
    forb = list(forbidden_reads or [])
    prompts = list(prompt_files or req)
    # Codex fixtures hash/count the regenerated mirror, not canonical proxies.
    if mirror_skill:
        req = _mirror_paths(req, mirror_skill)
        forb = _mirror_paths(forb, mirror_skill)
        prompts = _mirror_paths(prompts, mirror_skill)
    # Every required read must be hashed and counted.
    for p in req:
        if p not in prompts:
            prompts.append(p)
    return {
        "fixture_id": fixture_id,
        "cluster": cluster,
        "baseline": "B0",
        "baseline_commit": BASELINE_COMMIT,
        "lineage": {
            "B0": BASELINE_COMMIT,
            "V1_B1": None,
            "candidate": None,
            "rule": "immutable B0; task 130.2 freezes V1/B1; later tasks compare to B1 only",
        },
        "host": host,
        "activation": {
            "form": activation_form,
            "skill": skill,
            "args": list(args or []),
        },
        "branch_inputs": dict(branch_inputs or {}),
        "required_reads": req,
        "forbidden_reads": forb,
        "prompt_files": prompts,
        "oracles": oracles
        or {
            "output": [],
            "tools": [],
            "writes": [],
            "receipts": [],
        },
        "mutation_targets": dict(mutation_targets or {}),
        "metrics": {
            "reached_path_chars": None,
            "reached_path_chars_div_4": None,
            "backend_telemetry": None,
        },
        "provenance": {
            "host": host,
            "date_utc": None,
            "fixture_hash": None,
            **PROVENANCE_DETERMINISTIC_FREEZE,
        },
        "ratchet": {
            "verdict": "baseline",
            "flat_or_noisy": "discard",
            "borderline_paired_n_min": 2,
            "subjective_majority_n": [3, 5],
        },
        "privacy": {
            "scrubbed": True,
            "no_live_tracker": True,
            "answer_key_separated": True,
        },
        "resume": {
            "parent": None,
            "sealed_holdout": sealed_holdout,
            "subjective": subjective,
            "borderline": borderline,
        },
        "mirror_skill": mirror_skill,
        "notes": notes,
        # Filled at freeze time:
        "prompt_hashes": {},
        "fixture_hash": None,
    }


def inventory() -> list[dict[str, Any]]:
    """Return every B0 fixture covering the task/spec cluster inventory."""
    out: list[dict[str, Any]] = []
    out.extend(_version_fixtures())
    out.extend(_setup_fixtures())
    out.extend(_tracker_fixtures())
    out.extend(_prime_fixtures())
    out.extend(_plan_review_fixtures())
    out.extend(_plan_fixtures())
    out.extend(_work_fixtures())
    out.extend(_strategy_fixtures())
    out.extend(_make_pr_fixtures())
    out.extend(_pilot_fixtures())
    out.extend(_cross_host_fixtures())
    return out


def _version_fixtures() -> list[dict[str, Any]]:
    """B0 Version oracles freeze current-main Plan precheck (commit BASELINE_COMMIT).

    Current Plan SKILL.md precheck (not the future 130.2 Plan-only contract):
      * copy mismatch interactive → AskUserQuestion options Refresh now /
        Remind me next version / Skip this run
      * Remind me next version → writes version_ack (or snippet_ack in plugin mode)
      * Skip this run → continue with no acknowledgement write
      * autonomous/Ralph markers → one-line stderr warn; continue
      * plugin mode → snippet contract ceremony (FLOW_SNIPPET_ASK), not absent
      * missing jq/meta/plugin version → silent continue (fail-open)

    Future 130.2 Plan-only expectations live under ``mutation_targets`` only —
    never as the B0 answer key.
    """
    plan_skill = f"{S['plan']}/SKILL.md"
    plan_steps = f"{S['plan']}/steps.md"
    plan_examples = f"{S['plan']}/examples.md"
    base_req = [plan_skill, plan_steps]
    # (fixture_id, branch, baseline_oracle_note, writes, mutation_targets)
    cases: list[tuple[str, dict[str, Any], str, list[dict[str, Any]], dict[str, Any]]] = [
        (
            "version.copy-match",
            {"mode": "copy", "versions": "match"},
            "versions equal → no FLOW_SETUP_ASK; silent continue",
            [],
            {},
        ),
        (
            "version.interactive-mismatch-refresh",
            {"mode": "copy", "versions": "mismatch", "choice": "refresh"},
            (
                "AskUserQuestion options exactly Refresh now / Remind me next version / "
                "Skip this run; Refresh now → pause and have user run /flow-next:setup"
            ),
            [{"kind": "no_version_ack_write", "when": "refresh_choice"}],
            {
                "task": "130.2",
                "note": "Plan-only copy-mode contract replaces duplicated ceremony",
                "target_output": (
                    "exact Refresh question/options; stop; instruct /flow-next:setup"
                ),
            },
        ),
        (
            # ID kept: "continue" here means Skip-this-run continue-without-ack
            # under current main — NOT the future warn-once Plan-only continue.
            "version.interactive-mismatch-continue",
            {"mode": "copy", "versions": "mismatch", "choice": "skip"},
            (
                "AskUserQuestion; Skip this run → continue planning with no "
                "acknowledgement write; next invocation asks again"
            ),
            [{"kind": "no_version_ack_write", "when": "skip_choice"}],
            {
                "task": "130.2",
                "note": "future Plan-only: warn once; continue; no acknowledgement write",
                "target_branch_choice": "continue",
                "target_output": "warn once; continue planning; no acknowledgement write",
            },
        ),
        (
            "version.interactive-mismatch-remind",
            {"mode": "copy", "versions": "mismatch", "choice": "remind"},
            (
                "AskUserQuestion; Remind me next version → write version_ack = "
                "plugin version then continue"
            ),
            [{"kind": "version_ack_write", "when": "remind_choice"}],
            {
                "task": "130.2",
                "note": "Plan-only contract drops acknowledgement writes from Plan path",
            },
        ),
        (
            "version.autonomous-mismatch",
            {"mode": "copy", "versions": "mismatch", "autonomous": True},
            "autonomy markers → one-line stderr differs notice; continue (non-blocking)",
            [{"kind": "no_version_ack_write"}],
            {},
        ),
        (
            "version.missing-setup-metadata",
            {"mode": "copy", "meta": "missing"},
            "missing .flow/meta.json → silent continue (fail-open)",
            [],
            {},
        ),
        (
            "version.missing-plugin-version",
            {"mode": "copy", "plugin_version": "unavailable"},
            "plugin version unavailable/unknown → silent continue (fail-open)",
            [],
            {},
        ),
        (
            "version.plugin-mode",
            {"mode": "plugin"},
            (
                "plugin mode: version compare skipped; snippet contract ceremony "
                "via FLOW_SNIPPET_ASK / stderr when sentinel ≠ v1"
            ),
            [{"kind": "snippet_ack_write_possible", "when": "remind_on_snippet_ask"}],
            {
                "task": "130.2",
                "target_output": "no runtime snippet/version ceremony in Plan",
                "note": "Setup continues owning setup-mode/snippet integrity",
            },
        ),
        (
            "version.unavailable-jq",
            {"mode": "copy", "jq": "unavailable"},
            "jq unavailable → silent continue (fail-open)",
            [],
            {},
        ),
        (
            "version.prior-acknowledgement-fields",
            {"mode": "copy", "version_ack": "present", "snippet_ack": "present"},
            (
                "existing version_ack/snippet_ack fields tolerated on read; "
                "when VERSION_ACK equals PLUGIN_VER, mismatch ask is suppressed"
            ),
            [{"kind": "no_new_ack_write_when_already_acked"}],
            {
                "task": "130.2",
                "target_output": "tolerate on read; do not write/use acknowledgement fields",
            },
        ),
    ]
    out = []
    for fid, branch, oracle_note, writes, mut in cases:
        out.append(
            _fx(
                fid,
                "version",
                skill="flow-next-plan",
                branch_inputs=branch,
                required_reads=base_req,
                forbidden_reads=[],
                prompt_files=base_req + [plan_examples],
                oracles={
                    "output": [{"kind": "behavior_note", "detail": oracle_note}],
                    "tools": [],
                    "writes": writes,
                    "receipts": [],
                },
                mutation_targets=mut,
                notes=(
                    "B0 freezes current-main Plan precheck observable behavior at "
                    f"{BASELINE_COMMIT}; 130.2 Plan-only targets are mutation_targets only."
                ),
            )
        )
    return out


def _setup_fixtures() -> list[dict[str, Any]]:
    root = f"{S['setup']}/SKILL.md"
    wf = f"{S['setup']}/workflow.md"
    templates = [
        f"{S['setup']}/templates/claude-md-snippet.md",
        f"{S['setup']}/templates/agents-md-snippet.md",
        f"{S['setup']}/templates/claude-md-snippet-plugin.md",
        f"{S['setup']}/templates/model-routing-snippet.md",
    ]
    hosts = ["claude", "codex", "droid", "cursor", "grok"]
    out = []
    for mode in ("copy-first-install", "copy-refresh", "plugin-mode", "autonomous"):
        out.append(
            _fx(
                f"setup.{mode}",
                "setup",
                skill="flow-next-setup",
                branch_inputs={"setup_mode": mode},
                required_reads=[root, wf],
                forbidden_reads=[],
                prompt_files=[root, wf, *templates],
                oracles={
                    "output": [{"kind": "marker_safe_writes"}],
                    "tools": [],
                    "writes": [{"kind": "setup_mode_stamp"}],
                    "receipts": [],
                },
                notes="B0 force-loads workflow.md; host/mode branch routing is task 130.3.",
            )
        )
    out.append(
        _fx(
            "setup.customized-snippet-keep",
            "setup",
            skill="flow-next-setup",
            branch_inputs={"customized": True, "choice": "keep"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf, *templates],
        )
    )
    out.append(
        _fx(
            "setup.customized-snippet-overwrite",
            "setup",
            skill="flow-next-setup",
            branch_inputs={"customized": True, "choice": "overwrite"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf, *templates],
        )
    )
    out.append(
        _fx(
            "setup.malformed-metadata",
            "setup",
            skill="flow-next-setup",
            branch_inputs={"meta": "malformed"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf],
        )
    )
    for h in hosts:
        out.append(
            _fx(
                f"setup.host-{h}",
                "setup",
                skill="flow-next-setup",
                host=h,
                branch_inputs={"target_host": h},
                required_reads=[root, wf],
                forbidden_reads=[],
                prompt_files=[root, wf, *templates],
                notes="B0: all host branches live inside workflow.md; later routing loads only selected host.",
            )
        )
    out.append(
        _fx(
            "setup.model-routing-accepted",
            "setup",
            skill="flow-next-setup",
            branch_inputs={"model_routing": "accepted"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf, templates[3]],
        )
    )
    out.append(
        _fx(
            "setup.model-routing-skipped",
            "setup",
            skill="flow-next-setup",
            branch_inputs={"model_routing": "skipped"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf],
        )
    )
    out.append(
        _fx(
            "setup.ralph-available",
            "setup",
            skill="flow-next-setup",
            branch_inputs={"ralph": "available"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf],
        )
    )
    out.append(
        _fx(
            "setup.ralph-unsupported",
            "setup",
            skill="flow-next-setup",
            branch_inputs={"ralph": "unsupported"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf],
        )
    )
    return out


def _tracker_fixtures() -> list[dict[str, Any]]:
    out = []
    # B0: SKILL.md force-links every adapter — baseline required_reads include all.
    b0_all = TRACKER_COMMON + ALL_TRACKER_ADAPTER_FILES
    out.append(
        _fx(
            "tracker.inactive",
            "tracker",
            skill="flow-next-tracker-sync",
            branch_inputs={"tracker": "inactive", "live_tracker": False},
            required_reads=b0_all,
            forbidden_reads=[],
            prompt_files=b0_all,
            oracles={
                "output": [{"kind": "noop_or_inactive"}],
                "tools": [{"kind": "no_live_tracker"}],
                "writes": [],
                "receipts": [{"kind": "sync_receipt_optional"}],
            },
            notes="B0 force-loads every adapter ref; 130.4 routes selected adapter only. Fake transports only.",
        )
    )
    for name, paths in TRACKER_ADAPTERS.items():
        # B0: current Tracker SKILL.md force-reads every adapter/reference.
        # Selected-adapter narrowing is a 130.4 mutation_target, not B0 prompt_files.
        out.append(
            _fx(
                f"tracker.{name.replace('_', '-')}",
                "tracker",
                skill="flow-next-tracker-sync",
                branch_inputs={
                    "tracker": name,
                    "live_tracker": False,
                    "transport": "fake",
                },
                required_reads=b0_all,
                forbidden_reads=[],
                prompt_files=b0_all,
                oracles={
                    "output": [{"kind": "normalized_request_receipt"}],
                    "tools": [{"kind": "fake_transport_only"}],
                    "writes": [],
                    "receipts": [{"kind": "sync_receipt"}],
                },
                mutation_targets={
                    "task": "130.4",
                    "selected_adapter_files": paths,
                    "target_prompt_files": TRACKER_COMMON + paths,
                    "note": "route selected adapter only; other adapters become cold",
                },
                notes=(
                    f"Selected adapter files for later routing: {paths}. "
                    "B0 hashes/counts every current force-linked adapter ref."
                ),
            )
        )
    for op in ("push", "pull", "reconcile", "create-if-unlinked"):
        out.append(
            _fx(
                f"tracker.op-{op}",
                "tracker",
                skill="flow-next-tracker-sync",
                args=[op],
                branch_inputs={"op": op, "live_tracker": False, "transport": "fake"},
                required_reads=b0_all,
                forbidden_reads=[],
                prompt_files=b0_all,
            )
        )
    for conflict in ("body", "status", "comments", "dependency"):
        out.append(
            _fx(
                f"tracker.conflict-{conflict}",
                "tracker",
                skill="flow-next-tracker-sync",
                branch_inputs={
                    "conflict": conflict,
                    "live_tracker": False,
                    "transport": "fake",
                },
                required_reads=b0_all,
                forbidden_reads=[],
                prompt_files=b0_all,
            )
        )
    out.append(
        _fx(
            "tracker.malformed-config",
            "tracker",
            skill="flow-next-tracker-sync",
            branch_inputs={"config": "malformed", "live_tracker": False},
            required_reads=b0_all,
            forbidden_reads=[],
            prompt_files=b0_all,
            notes="Fail open toward safety/common instructions.",
        )
    )
    return out


def _prime_fixtures() -> list[dict[str, Any]]:
    root = f"{S['prime']}/SKILL.md"
    wf = f"{S['prime']}/workflow.md"
    classification = f"{S['prime']}/classification.md"
    pillars = f"{S['prime']}/pillars.md"
    remediation = f"{S['prime']}/remediation.md"
    playbooks = f"{S['prime']}/playbooks.md"
    stacks = f"{S['prime']}/stacks.md"
    harness = f"{S['prime']}/harness.md"
    topologies = [
        "greenfield",
        "greenfield-x-constellation",
        "tier-a-siblings",
        "tier-b-home-base",
        "workspace-parent",
        "worktree-sibling",
        "real-repo-flow-next",
    ]
    out = []
    out.append(
        _fx(
            "prime.classify-only",
            "prime",
            skill="flow-next-prime",
            args=["--classify-only"],
            branch_inputs={"route": "classify-only"},
            required_reads=[root, wf, classification],
            forbidden_reads=[pillars, remediation],
            prompt_files=[root, wf, classification, pillars, remediation, playbooks, stacks, harness],
            notes=(
                "B0 intent: cheap mode should avoid pillars/remediation; "
                "current prose may still over-link — mutation in 130.5."
            ),
        )
    )
    out.append(
        _fx(
            "prime.report-only",
            "prime",
            skill="flow-next-prime",
            branch_inputs={"route": "report-only"},
            required_reads=[root, wf, classification, playbooks],
            forbidden_reads=[remediation],
            prompt_files=[root, wf, classification, pillars, remediation, playbooks, stacks],
        )
    )
    out.append(
        _fx(
            "prime.full-no-fixes",
            "prime",
            skill="flow-next-prime",
            branch_inputs={"route": "full", "fixes": False},
            required_reads=[root, wf, classification, pillars, playbooks, stacks],
            forbidden_reads=[],
            prompt_files=[root, wf, classification, pillars, remediation, playbooks, stacks, harness],
        )
    )
    out.append(
        _fx(
            "prime.full-fixes",
            "prime",
            skill="flow-next-prime",
            branch_inputs={"route": "full", "fixes": True},
            required_reads=[root, wf, classification, pillars, remediation, playbooks, stacks],
            forbidden_reads=[],
            prompt_files=[root, wf, classification, pillars, remediation, playbooks, stacks, harness],
        )
    )
    out.append(
        _fx(
            "prime.unknown-classification",
            "prime",
            skill="flow-next-prime",
            branch_inputs={"route": "unknown"},
            required_reads=[root, wf, classification],
            forbidden_reads=[],
            prompt_files=[root, wf, classification],
        )
    )
    out.append(
        _fx(
            "prime.auth-unavailable",
            "prime",
            skill="flow-next-prime",
            branch_inputs={"auth": "unavailable"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf],
            oracles={
                "output": [{"kind": "auth_unavailable_surface"}],
                "tools": [],
                "writes": [],
                "receipts": [],
            },
        )
    )
    for topo in topologies:
        out.append(
            _fx(
                f"prime.topology-{topo}",
                "prime",
                skill="flow-next-prime",
                branch_inputs={"topology_fixture": topo},
                required_reads=[root, wf, classification],
                forbidden_reads=[],
                prompt_files=[root, wf, classification, pillars, playbooks, stacks],
                notes=f"Maps to optimization/prime/fixtures/{topo}.json judgment cell.",
            )
        )
    return out


def _plan_review_fixtures() -> list[dict[str, Any]]:
    root = f"{S['plan_review']}/SKILL.md"
    wf = f"{S['plan_review']}/workflow.md"
    prompt_ref = f"{S['plan_review']}/references/plan-review-prompt.md"
    flowctl_ref = f"{S['plan_review']}/flowctl-reference.md"
    backends = ["none", "export", "host", "codex", "copilot", "cursor", "rp", "unavailable"]
    out = []
    for b in backends:
        # B0: workflow.md contains every backend path inline.
        req = [root, wf]
        forb: list[str] = []
        if b == "export":
            forb = []  # export must not load configured-backend guidance post-mutation
        out.append(
            _fx(
                f"plan-review.{b}",
                "plan-review",
                skill="flow-next-plan-review",
                args=[] if b == "none" else [f"--review={b}"],
                branch_inputs={"backend": b},
                required_reads=req,
                forbidden_reads=forb,
                prompt_files=[root, wf, prompt_ref, flowctl_ref],
                notes=(
                    "B0 packs all backends into workflow.md; 130.6 splits selected "
                    "backend into a single reference."
                ),
            )
        )
    out.append(
        _fx(
            "plan-review.corpus-risky",
            "plan-review",
            skill="flow-next-plan-review",
            branch_inputs={"corpus": "risky"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf, prompt_ref],
            subjective=True,
            notes="Real-engine risky corpus; majority N=3–5 on subjective cells.",
        )
    )
    out.append(
        _fx(
            "plan-review.corpus-clean",
            "plan-review",
            skill="flow-next-plan-review",
            branch_inputs={"corpus": "clean"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf, prompt_ref],
            notes="Over-flag guard on clean corpus.",
        )
    )
    out.append(
        _fx(
            "plan-review.user-edited-spec",
            "plan-review",
            skill="flow-next-plan-review",
            branch_inputs={"spec": "user-edited"},
            required_reads=[root, wf],
            forbidden_reads=[],
            prompt_files=[root, wf],
            oracles={
                "output": [{"kind": "grounds_in_user_edits"}],
                "tools": [],
                "writes": [],
                "receipts": [],
            },
        )
    )
    return out


def _plan_fixtures() -> list[dict[str, Any]]:
    root = f"{S['plan']}/SKILL.md"
    steps = f"{S['plan']}/steps.md"
    examples = f"{S['plan']}/examples.md"
    html_ref = "plugins/flow-next/references/html-artifacts.md"
    out = []
    for name, branch in [
        ("p1-flow-native", {"fixture": "P1"}),
        ("p2-dociq", {"fixture": "P2", "repo": "DocIQ-Sphere"}),
        ("p3-hand-edited", {"fixture": "P3", "spec": "user-edited"}),
        ("p4-ordering-sizing", {"fixture": "P4"}),
    ]:
        out.append(
            _fx(
                f"plan.{name}",
                "plan",
                skill="flow-next-plan",
                branch_inputs=branch,
                required_reads=[root, steps, examples],
                forbidden_reads=[],
                prompt_files=[root, steps, examples],
                borderline=("p4" in name),
            )
        )
    out.append(
        _fx(
            "plan.sealed-holdout-nocode-research-mermaid",
            "plan",
            skill="flow-next-plan",
            branch_inputs={"fixture": "sealed-holdout", "paths": ["no-code", "research", "mermaid"]},
            required_reads=[root, steps],
            forbidden_reads=[],
            prompt_files=[root, steps, examples],
            sealed_holdout=True,
            notes="Sealed holdout — never edit to make a run pass. P4 sizing example is contaminated.",
        )
    )
    for flag, on in (("tracker", True), ("tracker", False), ("html", True), ("html", False), ("review", True), ("review", False)):
        forb = [] if on else ([html_ref] if flag == "html" else [])
        out.append(
            _fx(
                f"plan.{flag}-{'on' if on else 'off'}",
                "plan",
                skill="flow-next-plan",
                branch_inputs={flag: on},
                required_reads=[root, steps] + ([html_ref] if flag == "html" and on else []),
                forbidden_reads=forb,
                prompt_files=[root, steps, examples, html_ref],
                notes="Optional refs load only when selected (mutation target 130.7).",
            )
        )
    return out


def _work_fixtures() -> list[dict[str, Any]]:
    root = f"{S['work']}/SKILL.md"
    phases = f"{S['work']}/phases.md"
    delegation = f"{S['work']}/references/codex-delegation.md"
    tracker_tp = f"{S['work']}/references/tracker-touchpoints.md"
    out = []
    cases = [
        ("serial", {"parallel": False}, [root, phases], [delegation, tracker_tp]),
        ("parallel-eligible", {"parallel": True}, [root, phases], [delegation]),
        ("shared-file-conflict", {"conflict": "shared-file"}, [root, phases], [delegation]),
        ("worker-failure", {"worker": "failure"}, [root, phases], [delegation]),
        ("host-deferred-handover", {"review": "host-deferred"}, [root, phases], [delegation]),
        ("delegation-off", {"delegate": "off"}, [root, phases], [delegation]),
        ("delegation-on", {"delegate": "codex"}, [root, phases, delegation], []),
        ("delegation-declined", {"delegate": "declined"}, [root, phases], [delegation]),
        ("delegation-failure", {"delegate": "failure"}, [root, phases, delegation], []),
        ("tracker-off", {"tracker": False}, [root, phases], [tracker_tp]),
        ("tracker-on", {"tracker": True}, [root, phases, tracker_tp], []),
        ("tracker-error", {"tracker": "error"}, [root, phases, tracker_tp], []),
        ("plan-sync", {"plan_sync": True}, [root, phases], [delegation]),
        ("review", {"review": "codex"}, [root, phases], [delegation]),
    ]
    for name, branch, req, forb in cases:
        out.append(
            _fx(
                f"work.{name}",
                "work",
                skill="flow-next-work",
                branch_inputs=branch,
                required_reads=req,
                forbidden_reads=forb,
                prompt_files=[root, phases, delegation, tracker_tp],
                notes="Delegation-only + tracker-touchpoints stay cold when inactive (already gated; B0 proves).",
            )
        )
    return out


def _strategy_fixtures() -> list[dict[str, Any]]:
    root = f"{S['strategy']}/SKILL.md"
    interview = f"{S['strategy']}/references/interview.md"
    template = f"{S['strategy']}/references/strategy-template.md"
    cases = [
        ("absent", {"state": "absent"}, [root, interview, template], []),
        ("husk", {"state": "husk"}, [root, interview], []),
        ("foreign", {"state": "foreign"}, [root], [interview]),
        ("generated-first-run", {"state": "first-run"}, [root, interview, template], []),
        ("update", {"state": "update"}, [root, interview], []),
    ]
    return [
        _fx(
            f"strategy.{name}",
            "strategy",
            skill="flow-next-strategy",
            branch_inputs=branch,
            required_reads=req,
            forbidden_reads=forb,
            prompt_files=[root, interview, template],
        )
        for name, branch, req, forb in cases
    ]


def _make_pr_fixtures() -> list[dict[str, Any]]:
    root = f"{S['make_pr']}/SKILL.md"
    wf = f"{S['make_pr']}/workflow.md"
    create = f"{S['make_pr']}/create-and-finalize.md"
    mermaid = f"{S['make_pr']}/mermaid-rules.md"
    phases = f"{S['make_pr']}/phases.md"
    html_ref = "plugins/flow-next/references/html-artifacts.md"
    cases = [
        ("dry-run", {"dry_run": True}, [root, wf, mermaid], [create]),
        ("html-off", {"html": False, "dry_run": False}, [root, wf, create, mermaid], [html_ref]),
        ("html-on", {"html": True, "dry_run": False}, [root, wf, create, mermaid, html_ref], []),
        ("create", {"dry_run": False}, [root, wf, create, mermaid], []),
        ("finalize", {"finalize": True}, [root, wf, create], []),
        ("existing-pr", {"existing_pr": True}, [root, wf, create], []),
        ("push-retry", {"push": "retry"}, [root, wf, create], []),
    ]
    return [
        _fx(
            f"make-pr.{name}",
            "make-pr",
            skill="flow-next-make-pr",
            branch_inputs=branch,
            required_reads=req,
            forbidden_reads=forb,
            prompt_files=[root, wf, create, mermaid, phases, html_ref],
            notes="create-and-finalize.md cold on --dry-run (already gated in SKILL.md).",
        )
        for name, branch, req, forb in cases
    ]


def _pilot_fixtures() -> list[dict[str, Any]]:
    root = f"{S['pilot']}/SKILL.md"
    wf = f"{S['pilot']}/workflow.md"
    backlog = f"{S['pilot']}/references/backlog-mode.md"
    qa = f"{S['pilot']}/references/qa-stage.md"
    cases = [
        ("ready", {"autonomy": "ready"}, [root, wf], [backlog]),
        ("backlog", {"autonomy": "backlog"}, [root, wf, backlog], []),
        ("blocked", {"state": "blocked"}, [root, wf], [backlog]),
        ("deferred", {"state": "deferred"}, [root, wf], [backlog]),
        ("strike", {"state": "strike"}, [root, wf], [backlog]),
        ("failure", {"state": "failure"}, [root, wf], [backlog]),
        ("qa-on", {"qa": True}, [root, wf, qa], [backlog]),
        ("qa-off", {"qa": False}, [root, wf], [qa, backlog]),
    ]
    return [
        _fx(
            f"pilot.{name}",
            "pilot",
            skill="flow-next-pilot",
            branch_inputs=branch,
            required_reads=req,
            forbidden_reads=forb,
            prompt_files=[root, wf, backlog, qa],
        )
        for name, branch, req, forb in cases
    ]


def _cross_host_fixtures() -> list[dict[str, Any]]:
    """Cross-host evidence boundaries — unavailable hosts are surfaced, never silent pass."""
    out = []
    hosts = [
        ("claude", "slash", "canonical direct activation"),
        ("claude", "natural-language", "natural-language activation"),
        ("codex", "slash", "regenerated mirror; count mirror files"),
        ("cursor", "cli", "CLI/GUI smoke; no precise loader-trace contract"),
        ("cursor", "gui", "GUI smoke; unavailable precise traces → surface limitation"),
        ("droid", "slash", "Factory Droid canonical-as-is"),
        ("grok", "inspect", "inspect/TUI where authenticated"),
    ]
    skill = "flow-next-work"
    root = f"{S['work']}/SKILL.md"
    phases = f"{S['work']}/phases.md"
    for host, form, note in hosts:
        mirror = (
            "plugins/flow-next/codex/skills/flow-next-work" if host == "codex" else None
        )
        out.append(
            _fx(
                f"cross-host.{host}-{form}",
                "cross-host",
                skill=skill,
                host=host,
                activation_form=form,
                branch_inputs={"evidence": "smoke"},
                required_reads=[root, phases],
                forbidden_reads=[f"{S['work']}/references/codex-delegation.md"],
                prompt_files=[root, phases],
                mirror_skill=mirror,
                notes=note,
            )
        )
    return out
