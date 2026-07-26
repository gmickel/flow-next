"""Normalized state vocabulary + the shared slot-assignment algorithm (fn-139.6).

Shared with fn-66's status policy: `backlog`, `todo`, `in_progress`,
`in_review`, `done`, `cancelled`. Only `todo`, `in_progress`, `done` are
REQUIRED - many real Jira workflows lack backlog or cancelled entirely, so
requiring them makes completeness unreachable.

Ambiguity is per normalized SLOT, not per provider: Linear's `type: started`
covers both In Progress and In Review, so both slots are ambiguous until a
human picks one at a time (`--select`, repeatable, one slot per call).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

REQUIRED_SLOTS = ("todo", "in_progress", "done")
OPTIONAL_SLOTS = ("backlog", "in_review", "cancelled")
#: Canonical resolution order: required first, deterministic conflict order.
ALL_SLOTS = REQUIRED_SLOTS + OPTIONAL_SLOTS

_NAME_TO_SLOT = {
    "todo": "todo", "to do": "todo",
    "in progress": "in_progress",
    "in review": "in_review",
    "done": "done",
    "backlog": "backlog",
    "cancelled": "cancelled", "canceled": "cancelled",
}


def normalize_name(name: str) -> str:
    return " ".join(str(name).lower().split())


@dataclass
class Assignment:
    """The outcome of one slot-assignment run."""

    mapping: dict = field(default_factory=dict)          # slot -> id
    #: First ambiguous REQUIRED slot (canonical order) + its live candidates -
    #: the typed `conflict` details variant. None when no required ambiguity.
    conflict: Optional[dict] = None
    #: Required slots with no candidate at all (workflow lacks the category).
    missing_required: list = field(default_factory=list)
    #: Kept-but-unnatural selections (a slot whose chosen id is outside its
    #: natural candidate pool) - recorded, never silent.
    aliases: dict = field(default_factory=dict)          # slot -> id
    warnings: list = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return (self.conflict is None and not self.missing_required
                and all(s in self.mapping for s in REQUIRED_SLOTS))


def assign_slots(pools: dict, live: dict, existing: Optional[dict] = None) -> Assignment:
    """One deterministic pass over the vocabulary.

    `pools[slot]` - the slot's NATURAL candidates, `[{id, name, ...}]` (Linear:
    states of the mapped type; Jira: statuses of the mapped category).
    `live` - every live state/status by id (validation set for kept entries).
    `existing` - prior `stateIds`/`statusIds` entries (a previous resolution or
    a human's `--select` tiebreak). Kept where the id is still live - a refresh
    must not clobber a human decision; dropped WITH A WARNING where dead.
    """
    out = Assignment()
    used: set = set()

    # 0) Keep still-valid existing entries (human tiebreaks survive refresh).
    for slot in ALL_SLOTS:
        prior = (existing or {}).get(slot)
        if prior is None:
            continue
        if prior in live:
            out.mapping[slot] = prior
            used.add(prior)
            if prior not in {c["id"] for c in pools.get(slot, [])}:
                out.aliases[slot] = prior
        else:
            out.warnings.append(
                f"dropped {slot}: previous id {prior!r} no longer resolves to a "
                "live state")

    # 1) Exact-name matches inside the natural pool.
    for slot in ALL_SLOTS:
        if slot in out.mapping:
            continue
        named = [c for c in pools.get(slot, [])
                 if _NAME_TO_SLOT.get(normalize_name(c.get("name", ""))) == slot
                 and c["id"] not in used]
        if len(named) == 1:
            out.mapping[slot] = named[0]["id"]
            used.add(named[0]["id"])

    # 2) Single-remaining-candidate rule; multiple -> ambiguous.
    for slot in ALL_SLOTS:
        if slot in out.mapping:
            continue
        remaining = [c for c in pools.get(slot, []) if c["id"] not in used]
        if len(remaining) == 1:
            out.mapping[slot] = remaining[0]["id"]
            used.add(remaining[0]["id"])
        elif len(remaining) > 1 and slot in REQUIRED_SLOTS and out.conflict is None:
            out.conflict = {"normalized": slot, "candidates": remaining}
        elif not remaining and slot in REQUIRED_SLOTS:
            out.missing_required.append(slot)
        # optional slot with 0 or >1 remaining candidates stays unfilled -
        # never auto-aliased (aliasing is a HUMAN act via --select).

    return out


def validate_select(slot: str, chosen_id: str, pools: dict, live: dict) -> Optional[str]:
    """Validate one `--select slot=id` against LIVE candidates.

    Returns an error message, or None when valid. A selection outside the
    slot's natural pool is an ALIAS - allowed (workflows with fewer states
    need it) and recorded by the caller, but the id must exist at all.
    """
    if slot not in ALL_SLOTS:
        return f"unknown normalized slot {slot!r}; slots are {ALL_SLOTS}"
    if chosen_id not in live:
        return (f"{chosen_id!r} is not a live state/status id for this "
                f"destination; candidates for {slot!r}: "
                f"{[c['id'] for c in pools.get(slot, [])]}")
    return None


def is_alias(slot: str, chosen_id: str, pools: dict) -> bool:
    return chosen_id not in {c["id"] for c in pools.get(slot, [])}
