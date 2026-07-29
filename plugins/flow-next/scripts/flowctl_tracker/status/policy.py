"""fn-66 merge-evidence gate + who-wins ladder (fn-140.3).

Ports status-sync.md faithfully into the CLI six-slot vocabulary
(backlog|todo|in_progress|in_review|done|cancelled). Legacy names map:
planned→todo, in-progress→in_progress, done/verified→done (verified keeps
its evidence distinction in the gate, not the slot name), deferred/wontfix→
cancelled-family (surfaced, never auto-applied).

Deadlock check fires FIRST — a terminal×in_progress pair matches BOTH
single-field rules; reordering silently auto-closes (reordering test must fail).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from ..types import ErrorClass, Request, Response, TrackerError
from ..lifecycle.helpers import Execute

#: CLI vocabulary (fn-139).
SLOTS = frozenset({"backlog", "todo", "in_progress", "in_review", "done", "cancelled"})
TERMINAL = frozenset({"done"})  # verified collapses to done at the slot layer
EARLY = frozenset({"backlog", "todo"})
ACTIVE_IN_PROGRESS = "in_progress"
NEEDS_HUMAN_EVIDENCE = frozenset({"closed-unmerged", "ambiguous", "probe-error"})
PR_EVIDENCE = frozenset({
    "merged", "open", "closed-unmerged", "none", "ambiguous", "probe-error",
})
CONFLICT_TIEBREAKS = frozenset({"always-ask", "flow-wins", "tracker-wins"})

#: GitHub close/reopen reasons — docs list completed|not_planned|reopened;
#: undocumented `duplicate` is accepted live; anything else is invalid_input
#: BEFORE a mutation request is issued (GitHub would 422).
GITHUB_REASONS = frozenset({"completed", "not_planned", "duplicate", "reopened"})

DecisionKind = str  # apply | noop | defer | conflict | invalid_input


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    target_slot: Optional[str] = None
    reason: Optional[str] = None
    details: dict = field(default_factory=dict)
    close_reason: Optional[str] = None  # github state_reason when applying terminal


def validate_to_reason(requested_to: Any, reason: Optional[str]
                       ) -> Optional[TrackerError]:
    if not isinstance(requested_to, str) or requested_to not in SLOTS:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"--to must be one of {sorted(SLOTS)}, got {requested_to!r}",
            subtype="to",
        )
    if reason is None:
        return None
    if reason not in GITHUB_REASONS:
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"invalid --reason {reason!r}; allowed: {sorted(GITHUB_REASONS)}",
            subtype="reason",
        )
    # Reason/slot pairing follows the normalized read surface. GitHub reports
    # not_planned as cancelled, while completed/duplicate normalize to done.
    if reason == "reopened" and requested_to == "done":
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "--reason reopened is not valid with --to done",
            subtype="reason",
        )
    if reason == "not_planned" and requested_to != "cancelled":
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            "--reason 'not_planned' requires --to cancelled",
            subtype="reason",
        )
    if reason in {"completed", "duplicate"} and requested_to != "done":
        return TrackerError(
            ErrorClass.INVALID_INPUT,
            f"--reason {reason!r} requires --to done",
            subtype="reason",
        )
    return None


def validate_conflict_tiebreak(config: dict) -> str | TrackerError:
    """Return the exact configured deadlock policy, defaulting only if absent.

    Runtime config is user-editable. A malformed persisted value must fail
    before any claim or sequence work rather than silently changing authority.
    """
    tracker = config.get("tracker")
    if not isinstance(tracker, dict) or "conflictTiebreak" not in tracker:
        return "always-ask"
    value = tracker["conflictTiebreak"]
    if isinstance(value, str) and value in CONFLICT_TIEBREAKS:
        return value
    return TrackerError(
        ErrorClass.INVALID_INPUT,
        f"tracker.conflictTiebreak must be one of "
        f"{sorted(CONFLICT_TIEBREAKS)}, got {value!r}",
        subtype="conflict_tiebreak",
    )


# ---------------------------------------------------------------------------
# merge evidence (gh pr list — probes the REPO, not the tracker type)
# ---------------------------------------------------------------------------

def merge_evidence(config: dict, spec_data: dict, execute: Execute) -> str:
    """Probe `gh pr list --head <branch>` via the executor CLI route.

    Returns one of: merged|open|closed-unmerged|none|ambiguous|probe-error.
    Empty/missing branch_name → probe-error (never none, never merged).
    """
    branch = spec_data.get("branch_name")
    if not isinstance(branch, str) or not branch.strip():
        return "probe-error"
    branch = branch.strip()
    # Run in the current Git checkout and let gh resolve THAT repository.
    # tracker.perTracker.repo may intentionally point at an out-of-tree issue
    # repository; PR merge evidence belongs to the code repository instead.
    argv = ["gh", "pr", "list", "--head", branch, "--state", "all",
            "--json", "url,state,number,isDraft"]
    result = execute(Request(
        provider="github", op="merge-evidence", method="GET",
        url_or_argv=argv, idempotent=True,
    ))
    if isinstance(result, TrackerError):
        return "probe-error"
    if not isinstance(result, Response):
        return "probe-error"
    # Non-200 / empty-failed body → probe-error (executor may return Response
    # with status for CLI failures before classify wraps them — bound path
    # usually returns TrackerError; be defensive).
    if result.status and result.status >= 400:
        return "probe-error"
    try:
        rows = json.loads(result.body or b"[]")
    except (ValueError, TypeError):
        return "probe-error"
    if not isinstance(rows, list):
        return "probe-error"
    return _classify_pr_rows(rows)


def _classify_pr_rows(rows: list) -> str:
    merged = open_ = closed = draft = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        state = str(row.get("state") or "").upper()
        if state == "MERGED":
            merged += 1
        elif state == "OPEN":
            # Drafts are not clean open evidence - counted separately so a
            # draft-only branch classifies ambiguous per status-sync.md.
            if row.get("isDraft"):
                draft += 1
            else:
                open_ += 1
        elif state == "CLOSED":
            closed += 1
    # Canonical buckets, status-sync.md verbatim: BOTH an open AND a
    # closed-unmerged PR is explicitly named ambiguous, as is "a draft-only
    # result where no clear merge/open/closed signal dominates" (a host
    # "recreate-PR" simplification was reverted here - the doc decides, not
    # intuition).
    if merged >= 1:
        return "merged"
    if open_ >= 1 and closed == 0:
        return "open"
    if open_ >= 1 and closed >= 1:
        return "ambiguous"
    if draft >= 1:
        # Draft-only (possibly alongside closed rows): no clear signal
        # dominates - ambiguous, never clean open or closed-unmerged.
        return "ambiguous"
    if closed >= 1:
        return "closed-unmerged"
    if not rows:
        return "none"
    return "ambiguous"


# ---------------------------------------------------------------------------
# flow → normalized (8-row table; prEvidence first; CLI slots)
# ---------------------------------------------------------------------------

def flow_to_normalized(spec_data: dict, pr_evidence: str,
                       completion_review_configured: bool,
                       *, tasks: Optional[list] = None) -> str:
    """8-row table from status-sync.md, emitting CLI slots.

    Row order is load-bearing: PR signal rows (1–6) beat local task rows (7–8).
    Terminal (`done`) is reachable ONLY from pr_evidence == merged.
    `verified` (row 2) maps to the `done` slot; ship evidence is kept for the
    caller (completion_review_status), not as a separate slot name.
    """
    if pr_evidence not in PR_EVIDENCE:
        pr_evidence = "probe-error"
    spec_status = str(spec_data.get("status") or "open")
    review = str(spec_data.get("completion_review_status") or "unknown")
    task_list = tasks if tasks is not None else list(spec_data.get("tasks") or [])

    # Rows 1–3: merged
    if pr_evidence == "merged":
        if spec_status == "done":
            if not completion_review_configured:
                return "done"  # row 1
            if review == "ship":
                return "done"  # row 2 (verified → done slot)
            return "in_review"  # row 3 (configured, not ship)
        # Merged PR + still-open spec: PR signal wins over local task rows.
        return "in_review"

    # Row 4: open PR — any local status
    if pr_evidence == "open":
        return "in_review"

    # Rows 5–6: done + non-terminal evidence
    if spec_status == "done":
        # none / closed-unmerged / ambiguous / probe-error → in_review (NOT terminal)
        return "in_review"

    # Rows 7–8: open spec, no PR signal. `blocked` counts as work underway:
    # status-sync.md says blocked tasks do not change the spec-level
    # normalized status - "the issue stays in-progress" - so an all-blocked
    # spec must not regress to todo (that would conflict against an
    # already-in-progress tracker or hide that work started).
    statuses = [_task_status(t) for t in task_list]
    if not task_list:
        return "backlog"  # row 8 — no tasks
    if any(s in ("in_progress", "done", "blocked") for s in statuses):
        return "in_progress"  # row 7
    return "todo"  # row 8 — all todo (planned→todo)


def _task_status(task: Any) -> str:
    if isinstance(task, dict):
        return str(task.get("status") or "todo")
    return "todo"


# ---------------------------------------------------------------------------
# who-wins decide (deadlock FIRST)
# ---------------------------------------------------------------------------

def is_deadlock(flow_norm: str, tracker_norm: str) -> bool:
    """Terminal on one side × in_progress on the other — matches BOTH rules."""
    return (
        (tracker_norm in TERMINAL and flow_norm == ACTIVE_IN_PROGRESS)
        or (flow_norm in TERMINAL and tracker_norm == ACTIVE_IN_PROGRESS)
    )


def terminal_wins_matches(flow_norm: str, tracker_norm: str) -> bool:
    """Single-field rule: tracker terminal (used by the reordering test)."""
    return tracker_norm in TERMINAL


def in_progress_wins_matches(flow_norm: str, tracker_norm: str) -> bool:
    """Single-field rule: flow in_progress vs early tracker."""
    return flow_norm == ACTIVE_IN_PROGRESS and tracker_norm in EARLY


def decide(requested_to: str, reason: Optional[str], flow_norm: str,
           tracker_norm: str, pr_evidence: str,
           conflict_tiebreak: str = "always-ask") -> Decision:
    """`--to` is a REQUEST, not an authority — the gate decides.

    Order (load-bearing):
      0. validate --to/--reason
      1. cancelled-family request → defer (never auto-apply)
      2. DEADLOCK CHECK FIRST
      3. closed-unmerged / ambiguous / probe-error → defer (needs-human)
      4. terminal request refused by merge-evidence gate → conflict
      5. noop / terminal-wins / in-progress-wins / preserve / push / surface
      6. residual → conflict (never silent default)
    """
    bad = validate_to_reason(requested_to, reason)
    if bad:
        return Decision("invalid_input", reason=bad.subtype,
                        details={"message": bad.message, "error": bad})

    if requested_to == "cancelled" or tracker_norm == "cancelled":
        return Decision(
            "defer", reason="cancelled-family",
            details={"flow": flow_norm, "tracker": tracker_norm,
                     "requested": requested_to},
        )

    # ── DEADLOCK FIRST ──────────────────────────────────────────────
    if is_deadlock(flow_norm, tracker_norm):
        if conflict_tiebreak == "flow-wins":
            close = (
                reason
                if reason in {"completed", "duplicate"}
                else "completed"
            )
            return Decision(
                "apply",
                target_slot=flow_norm,
                close_reason=close if flow_norm in TERMINAL else None,
                details={
                    "who": "flow-wins",
                    "flow": flow_norm,
                    "tracker": tracker_norm,
                    "requested": requested_to,
                },
            )
        if conflict_tiebreak == "tracker-wins":
            if tracker_norm in TERMINAL:
                return Decision(
                    "apply_local",
                    target_slot=tracker_norm,
                    details={
                        "who": "tracker-wins",
                        "flow": flow_norm,
                        "tracker": tracker_norm,
                        "requested": requested_to,
                    },
                )
            return Decision(
                "conflict",
                reason="status-deadlock-unrepresentable",
                details={
                    "flow": flow_norm,
                    "tracker": tracker_norm,
                    "requested": requested_to,
                    "policy": conflict_tiebreak,
                    "unrepresentable": True,
                    "both_sides": {
                        "flow": flow_norm,
                        "tracker": tracker_norm,
                    },
                },
            )
        return Decision(
            "conflict", reason="status-deadlock",
            details={"flow": flow_norm, "tracker": tracker_norm,
                     "requested": requested_to,
                     "both_sides": {"flow": flow_norm, "tracker": tracker_norm}},
        )

    # ── CLOSED-UNMERGED / AMBIGUOUS / PROBE-ERROR — genuinely ambiguous
    #    evidence is a CONFLICT for the skill's recovery surface (R7), never
    #    a successful defer envelope. Evaluated BEFORE the equality
    #    no-op AND the terminal fold: non-clean merge evidence must reach a human even when the
    #    tracker side happens to read terminal. ──
    if pr_evidence in NEEDS_HUMAN_EVIDENCE and (
        requested_to == "done" or flow_norm == "in_review"
    ):
        return Decision(
            "conflict", reason=pr_evidence,
            details={"flow": flow_norm, "tracker": tracker_norm,
                     "pr_evidence": pr_evidence, "requested": requested_to},
        )

    # ── ALREADY IN AGREEMENT: a synchronized pair is a no-op BEFORE any
    #    folding - re-writing it would advance lastSyncedAt and emit a receipt
    #    for a sync that did not happen (R6 no-op invariant). ──
    if flow_norm == tracker_norm:
        return Decision("noop", target_slot=tracker_norm,
                        details={"who": "already-agree"})

    # ── TRACKER-TERMINAL WINS: fold into LOCAL state (no tracker write).
    #    After the agreement no-op and the evidence conflicts; deadlock
    #    (terminal x in_progress) was caught above, so this branch is a REAL
    #    local disagreement with clean evidence - a PM closing the issue is
    #    authoritative for closure. ──
    if tracker_norm in TERMINAL and flow_norm != ACTIVE_IN_PROGRESS:
        return Decision("apply_local", target_slot=tracker_norm,
                        details={"who": "tracker-terminal"})

    # Merge-evidence gate: --to done is refused unless flow_norm is terminal
    if requested_to == "done" and flow_norm not in TERMINAL:
        return Decision(
            "conflict", reason="merge-evidence-gate",
            details={"flow": flow_norm, "tracker": tracker_norm,
                     "requested": requested_to, "pr_evidence": pr_evidence},
        )

    if flow_norm == tracker_norm and (
        requested_to == tracker_norm
        or (requested_to == "done" and tracker_norm in TERMINAL)
    ):
        return Decision("noop", target_slot=tracker_norm)

    # flow wins in-progress — push when tracker is early
    if flow_norm == ACTIVE_IN_PROGRESS and tracker_norm in EARLY:
        if requested_to in (ACTIVE_IN_PROGRESS, "todo", "backlog") or requested_to == flow_norm:
            return Decision("apply", target_slot=ACTIVE_IN_PROGRESS)
        # caller asked for something else the ladder would not push → conflict
        return Decision(
            "conflict", reason="unmapped",
            details={"flow": flow_norm, "tracker": tracker_norm,
                     "requested": requested_to},
        )

    # S-G: no-PR preserve — locally done projects in_review but do not force
    if (flow_norm == "in_review" and pr_evidence == "none"
            and tracker_norm in EARLY | {ACTIVE_IN_PROGRESS, "in_review"}):
        if requested_to == "done":
            return Decision(
                "conflict", reason="merge-evidence-gate",
                details={"flow": flow_norm, "tracker": tracker_norm,
                         "pr_evidence": pr_evidence},
            )
        return Decision("noop", target_slot=tracker_norm,
                        details={"who": "no-pr-preserve"})

    # open-PR (or gated in_review) push - one branch; --to done was already
    # refused by the merge-evidence gate above, so every path lands in_review.
    if flow_norm == "in_review" and tracker_norm in EARLY | {ACTIVE_IN_PROGRESS}:
        return Decision("apply", target_slot="in_review")

    # flow terminal, tracker pre-terminal (not in_progress → not deadlock)
    if flow_norm in TERMINAL and tracker_norm in EARLY | {"in_review"}:
        close = reason if reason in {"completed", "not_planned", "duplicate"} else "completed"
        return Decision("apply", target_slot="done", close_reason=close)

    if tracker_norm == requested_to:
        return Decision("noop", target_slot=tracker_norm)

    # Unmapped / residual — conflict, never silent
    return Decision(
        "conflict", reason="unmapped",
        details={"flow": flow_norm, "tracker": tracker_norm,
                 "requested": requested_to, "pr_evidence": pr_evidence},
    )


def decision_as_error(decision: Decision) -> Optional[TrackerError]:
    if decision.kind == "invalid_input":
        err = decision.details.get("error")
        if isinstance(err, TrackerError):
            return err
        return TrackerError(ErrorClass.INVALID_INPUT,
                            decision.details.get("message") or "invalid input",
                            subtype=decision.reason or "input")
    if decision.kind == "conflict":
        return TrackerError(
            ErrorClass.CONFLICT,
            f"status conflict ({decision.reason or 'unmapped'}): "
            f"flow={decision.details.get('flow')!r} "
            f"tracker={decision.details.get('tracker')!r}",
            subtype=decision.reason or "status",
            details={
                "normalized": "status",
                "candidates": [
                    {"side": "flow", "slot": decision.details.get("flow")},
                    {"side": "tracker", "slot": decision.details.get("tracker")},
                    {"side": "requested", "slot": decision.details.get("requested")},
                ],
                **{k: v for k, v in decision.details.items()
                   if k not in {"error"}},
            },
        )
    return None
