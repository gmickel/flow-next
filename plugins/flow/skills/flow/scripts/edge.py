#!/usr/bin/env python3
"""Flow edge CLI: deterministic tracker and forge operations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.dont_write_bytecode = True

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _reconfigure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def get_repo_root() -> Path:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        return Path(res.stdout.strip())
    except (subprocess.CalledProcessError, OSError):
        return Path.cwd()


def get_flow_dir() -> Path:
    return get_repo_root() / ".flow"


def ensure_flow_exists() -> bool:
    return get_flow_dir().is_dir()


def error_exit(message: str, *, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message}))
    sys.exit(code)


def _with_forge_merge_read(module):
    import forge  # noqa: PLC0415
    from flowctl_tracker.status import policy  # noqa: PLC0415

    policy.forge_merge_read = forge._forge_merge_read
    return module


def cmd_tracker_resolve(args: argparse.Namespace) -> None:
    if not ensure_flow_exists():
        error_exit(".flow/ does not exist.")
    from flowctl_tracker import resolve_verb  # noqa: PLC0415

    payload, code = resolve_verb.run(
        get_flow_dir(),
        scope=getattr(args, "scope", None),
        refresh=bool(getattr(args, "refresh", False)),
        select=getattr(args, "select", None),
    )
    print(payload)
    sys.exit(code)


def cmd_tracker_wire(args: argparse.Namespace) -> None:
    if not ensure_flow_exists():
        error_exit(".flow/ does not exist.")
    from flowctl_tracker import wire as tracker_wire  # noqa: PLC0415

    payload, code = tracker_wire.run(
        get_flow_dir(),
        args.wire_verb,
        locator=getattr(args, "locator", None),
        title=getattr(args, "title", None),
        body_file=getattr(args, "body_file", None),
        comment_id=getattr(args, "comment_id", None),
        subject_id=getattr(args, "subject_id", None),
        blocked_stage=getattr(args, "blocked_stage", None),
        reason_code=getattr(args, "reason_code", None),
        question_slug=getattr(args, "question_slug", None),
        reply_settles=getattr(args, "reply_settles", False),
        add=getattr(args, "add", None),
        remove=getattr(args, "remove", None),
        file_path=getattr(args, "file", None),
        attachment_id=getattr(args, "attachment_id", None),
        out_path=getattr(args, "out", None),
        url=getattr(args, "url", None),
        any_lane=getattr(args, "any_lane", False),
        unlinked=getattr(args, "unlinked", False),
    )
    print(payload)
    sys.exit(code)


def cmd_tracker_lifecycle(args: argparse.Namespace) -> None:
    if not ensure_flow_exists():
        error_exit(".flow/ does not exist.")
    from flowctl_tracker import lifecycle as tracker_lifecycle  # noqa: PLC0415

    payload, code = tracker_lifecycle.run(
        get_flow_dir(),
        args.lifecycle_verb,
        spec_id=getattr(args, "spec_id", None),
        title=getattr(args, "title", None),
        body_file=getattr(args, "body_file", None),
        event=getattr(args, "event", None),
        retry_key=getattr(args, "retry_key", None),
        identifier=getattr(args, "identifier", None),
        durable_id=getattr(args, "durable_id", None),
        url=getattr(args, "url", None),
        source=getattr(args, "source", None),
        parent=getattr(args, "parent", None),
        project_id=getattr(args, "project_id", None),
        project_milestone_id=getattr(args, "project_milestone_id", None),
    )
    print(payload)
    sys.exit(code)


def cmd_tracker_create_first_key(args: argparse.Namespace) -> None:
    from flowctl_tracker.lifecycle import compute_create_first_key  # noqa: PLC0415

    body = ""
    if getattr(args, "body_file", None):
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            error_exit(f"cannot read --body-file: {exc}")
    key = compute_create_first_key(args.type, args.title, body, parent=args.parent)
    print(json.dumps({"ok": True, "key": key}))


def cmd_tracker_idea(args: argparse.Namespace) -> None:
    if not ensure_flow_exists():
        error_exit(".flow/ does not exist.")
    from flowctl_tracker import idea as tracker_idea  # noqa: PLC0415

    payload, code = tracker_idea.run(
        get_flow_dir(),
        args.idea_verb,
        idea=args.idea,
        parent=getattr(args, "parent_key", None),
        use=getattr(args, "use", None),
        body_file=getattr(args, "body_file", None),
    )
    print(payload)
    sys.exit(code)


def cmd_tracker_status(args: argparse.Namespace) -> None:
    if not ensure_flow_exists():
        error_exit(".flow/ does not exist.")
    from flowctl_tracker import status as tracker_status  # noqa: PLC0415

    _with_forge_merge_read(tracker_status)
    payload, code = tracker_status.run(
        get_flow_dir(),
        spec_id=getattr(args, "spec_id", None),
        to=getattr(args, "to", None),
        reason=getattr(args, "reason", None),
        event=getattr(args, "event", None),
        branch=getattr(args, "branch", None),
    )
    print(payload)
    sys.exit(code)


def cmd_tracker_relate(args: argparse.Namespace) -> None:
    if not ensure_flow_exists():
        error_exit(".flow/ does not exist.")
    from flowctl_tracker import relate as tracker_relate  # noqa: PLC0415

    payload, code = tracker_relate.run(
        get_flow_dir(),
        spec_id=getattr(args, "spec_id", None),
        blocked_by=getattr(args, "blocked_by", None),
        event=getattr(args, "event", None),
    )
    print(payload)
    sys.exit(code)


def _repo_path(arg: Optional[str]) -> Path:
    return Path(arg).resolve() if arg else get_repo_root()


def cmd_forge_origin(args: argparse.Namespace) -> None:
    import forge  # noqa: PLC0415

    origin = forge.repo_forge(str(_repo_path(args.repo)))
    print(json.dumps({"forge": origin.forge, "host": origin.host, "project": origin.project}))


def cmd_forge_prs(args: argparse.Namespace) -> None:
    import forge  # noqa: PLC0415

    rows = forge.forge_list_prs(
        _repo_path(args.repo), args.head, state=args.state, limit=args.limit
    )
    if rows is None:
        error_exit("forge PR listing failed")
    print(json.dumps(rows))


def cmd_forge_readiness(args: argparse.Namespace) -> None:
    import forge  # noqa: PLC0415

    out = forge.forge_readiness(_repo_path(args.repo), args.number)
    if out is None:
        error_exit("forge readiness is unsupported on this origin")
    print(json.dumps(out))


def cmd_forge_approvals(args: argparse.Namespace) -> None:
    import forge  # noqa: PLC0415

    rows, failure = forge.forge_approval_rows(args.head, _repo_path(args.repo))
    if rows is None:
        error_exit(failure or "forge approvals read failed")
    print(json.dumps([forge._pr_approval(row) for row in rows]))


def cmd_forge_wait(args: argparse.Namespace) -> None:
    import forge  # noqa: PLC0415

    if args.timeout < 1 or args.interval < 1:
        error_exit("--timeout and --interval must be >= 1 second")
    out = forge.forge_wait(
        _repo_path(args.repo), args.number, timeout_s=args.timeout, interval_s=args.interval
    )
    print(json.dumps(out))
    sys.exit(1 if out["state"] == "error" else 0)


def cmd_forge_merge(args: argparse.Namespace) -> None:
    import forge  # noqa: PLC0415

    out = forge.forge_merge(_repo_path(args.repo), args.number, args.head)
    print(json.dumps(out))
    sys.exit(0 if out["merged"] else 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edge",
        description="Flow edge CLI for tracker and forge operations",
    )
    sub = parser.add_subparsers(dest="group", required=True)

    # --- tracker ---
    p_tracker = sub.add_parser("tracker", help="Tracker operations")
    tracker_sub = p_tracker.add_subparsers(dest="tracker_cmd", required=True)

    p_res = tracker_sub.add_parser(
        "resolve",
        help="Backfill/refresh tracker.resolved (destination, ids scope, capabilities)",
    )
    p_res.add_argument("--scope", default=None)
    p_res.add_argument("--refresh", action="store_true")
    p_res.add_argument("--select", default=None, metavar="NORMALIZED=ID")
    p_res.add_argument("--json", action="store_true")
    p_res.set_defaults(func=cmd_tracker_resolve)

    p_wire = tracker_sub.add_parser("wire", help="Locator-addressed wire verbs")
    wire_sub = p_wire.add_subparsers(dest="wire_verb", required=True)

    def _wire_locator(p: argparse.ArgumentParser) -> None:
        p.add_argument("--locator", required=True,
                       help='JSON locator {"durable":"<id>","display":"<#N|project#iid|KEY-N>"}')

    def _wire_json(p: argparse.ArgumentParser) -> None:
        p.add_argument("--json", action="store_true")

    p_w = wire_sub.add_parser("read", help="Fetch one issue by locator")
    _wire_locator(p_w); _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("update", help="Update title/body by locator")
    _wire_locator(p_w); p_w.add_argument("--title", default=None); p_w.add_argument("--body-file", default=None)
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("comment-add", help="Add a comment")
    _wire_locator(p_w); p_w.add_argument("--body-file", required=True)
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("comment-list", help="List comments")
    _wire_locator(p_w); _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("comment-update", help="Update a comment")
    _wire_locator(p_w); p_w.add_argument("comment_id"); p_w.add_argument("--body-file", required=True)
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("comment-delete", help="Delete a comment")
    _wire_locator(p_w); p_w.add_argument("comment_id")
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("label", help="Add/remove labels")
    _wire_locator(p_w); p_w.add_argument("--add", action="append", default=[]); p_w.add_argument("--remove", action="append", default=[])
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("assign", help="Add/remove assignees")
    _wire_locator(p_w); p_w.add_argument("--add", action="append", default=[]); p_w.add_argument("--remove", action="append", default=[])
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("list-open", help="List open issues (compact rows)")
    p_w.add_argument("--any-lane", action="store_true")
    p_w.add_argument("--unlinked", action="store_true")
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("unready", help="Move an issue out of tracker.readyState")
    _wire_locator(p_w); _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("list-states", help="List tracker workflow states")
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("relation-list", help="List normalized dependency relations")
    _wire_locator(p_w); _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("question", help="Idempotently post a question comment")
    _wire_locator(p_w)
    p_w.add_argument("--subject-id", required=True)
    p_w.add_argument("--blocked-stage", required=True)
    p_w.add_argument("--reason-code", required=True)
    p_w.add_argument("--question-slug", required=True)
    p_w.add_argument("--reply-settles", action="store_true")
    p_w.add_argument("--body-file", required=True)
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("attach", help="Upload an attachment")
    _wire_locator(p_w); p_w.add_argument("--file", required=True)
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("attach-get", help="Download an attachment by id")
    p_w.add_argument("attachment_id"); p_w.add_argument("--out", required=True)
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_w = wire_sub.add_parser("link-pr", help="Link a PR URL to an issue")
    _wire_locator(p_w); p_w.add_argument("--url", required=True)
    _wire_json(p_w); p_w.set_defaults(func=cmd_tracker_wire)

    p_cr = tracker_sub.add_parser("create", help="Create a tracker issue and link an existing spec")
    p_cr.add_argument("spec_id")
    p_cr.add_argument("--title", required=True)
    p_cr.add_argument("--body-file", required=True)
    p_cr.add_argument("--parent", default=None)
    p_cr.add_argument("--project-id", dest="project_id", default=None)
    p_cr.add_argument("--project-milestone-id", dest="project_milestone_id", default=None)
    p_cr.add_argument("--event", default=None)
    p_cr.add_argument("--json", action="store_true")
    p_cr.set_defaults(func=cmd_tracker_lifecycle, lifecycle_verb="create")

    p_cf = tracker_sub.add_parser("create-first", help="Create a tracker issue before any local spec")
    p_cf.add_argument("--title", required=True)
    p_cf.add_argument("--body-file", required=True)
    p_cf.add_argument("--retry-key", required=True)
    p_cf.add_argument("--parent", default=None)
    p_cf.add_argument("--project-id", dest="project_id", default=None)
    p_cf.add_argument("--project-milestone-id", dest="project_milestone_id", default=None)
    p_cf.add_argument("--json", action="store_true")
    p_cf.set_defaults(func=cmd_tracker_lifecycle, lifecycle_verb="create-first")

    p_cfk = tracker_sub.add_parser("create-first-key", help="Compute the create-first retry lookup key")
    p_cfk.add_argument("--type", required=True)
    p_cfk.add_argument("--title", required=True)
    p_cfk.add_argument("--body-file", dest="body_file", default=None)
    p_cfk.add_argument("--parent", default=None)
    p_cfk.add_argument("--json", action="store_true")
    p_cfk.set_defaults(func=cmd_tracker_create_first_key)

    p_pe = tracker_sub.add_parser("persist-external", help="Record an MCP-performed Linear create")
    p_pe.add_argument("spec_id")
    p_pe.add_argument("--identifier", required=True)
    p_pe.add_argument("--id", dest="durable_id", default=None)
    p_pe.add_argument("--url", default=None)
    p_pe.add_argument("--source", required=True, choices=["mcp"])
    p_pe.add_argument("--event", default=None)
    p_pe.add_argument("--json", action="store_true")
    p_pe.set_defaults(func=cmd_tracker_lifecycle, lifecycle_verb="persist-external")

    p_idea = tracker_sub.add_parser("idea", help="Jira Product Discovery idea intake")
    idea_sub = p_idea.add_subparsers(dest="idea_verb", required=True)
    p_ir = idea_sub.add_parser("read", help="Read idea text, comments, and delivery links")
    p_ir.add_argument("idea")
    p_ip = idea_sub.add_parser("parent", help="Reuse or create the idea's delivery parent")
    p_ip.add_argument("idea")
    p_ip.add_argument("--body-file", required=True)
    p_ip.add_argument("--use", default=None)
    p_il = idea_sub.add_parser("link", help="Link a delivery issue to an idea")
    p_il.add_argument("idea")
    p_il.add_argument("parent_key")
    for p in (p_ir, p_ip, p_il):
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=cmd_tracker_idea)

    p_st = tracker_sub.add_parser("status", help="Reconcile tracker status for a linked spec")
    p_st.add_argument("spec_id")
    p_st.add_argument("--to", required=True,
                      choices=["backlog", "todo", "in_progress", "in_review", "done", "cancelled"])
    p_st.add_argument("--branch", default=None, help="Branch to probe for PR merge evidence")
    p_st.add_argument("--reason", default=None)
    p_st.add_argument("--event", default=None)
    p_st.add_argument("--json", action="store_true")
    p_st.set_defaults(func=cmd_tracker_status)

    p_rel = tracker_sub.add_parser("relate", help="Project a blocked-by relation between two linked specs")
    p_rel.add_argument("spec_id")
    p_rel.add_argument("--blocked-by", required=True, dest="blocked_by")
    p_rel.add_argument("--event", default=None)
    p_rel.add_argument("--json", action="store_true")
    p_rel.set_defaults(func=cmd_tracker_relate)

    # --- forge ---
    p_forge = sub.add_parser("forge", help="Forge operations (GitHub, GitLab, Bitbucket)")
    forge_sub = p_forge.add_subparsers(dest="forge_cmd", required=True)

    p_fo = forge_sub.add_parser("origin", help="Identify origin forge, host, and project")
    p_fo.add_argument("--repo", default=None)
    p_fo.set_defaults(func=cmd_forge_origin)

    p_fp = forge_sub.add_parser("prs", help="List PRs/MRs on the origin forge")
    p_fp.add_argument("--head", default=None)
    p_fp.add_argument("--state", default="open", choices=["open", "all"])
    p_fp.add_argument("--limit", type=int, default=50)
    p_fp.add_argument("--repo", default=None)
    p_fp.set_defaults(func=cmd_forge_prs)

    p_fr = forge_sub.add_parser("readiness", help="Check PR/MR merge readiness")
    p_fr.add_argument("number", type=int)
    p_fr.add_argument("--repo", default=None)
    p_fr.set_defaults(func=cmd_forge_readiness)

    p_fa = forge_sub.add_parser("approvals", help="Read PR approvals for a head branch")
    p_fa.add_argument("--head", required=True)
    p_fa.add_argument("--repo", default=None)
    p_fa.set_defaults(func=cmd_forge_approvals)

    p_fw = forge_sub.add_parser("wait", help="Wait for PR/MR checks and review to settle or deadline")
    p_fw.add_argument("number", type=int)
    p_fw.add_argument("--timeout", type=int, default=480, help="Deadline in seconds (default: 480)")
    p_fw.add_argument("--interval", type=int, default=15, help="Poll interval in seconds (default: 15)")
    p_fw.add_argument("--repo", default=None)
    p_fw.set_defaults(func=cmd_forge_wait)

    p_fm = forge_sub.add_parser("merge", help="Squash-merge a PR/MR bound to a specific head SHA")
    p_fm.add_argument("number", type=int)
    p_fm.add_argument("--head", required=True, help="Expected full 40-hex head commit SHA")
    p_fm.add_argument("--repo", default=None)
    p_fm.set_defaults(func=cmd_forge_merge)

    return parser


def main() -> None:
    _reconfigure_stdio_utf8()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
