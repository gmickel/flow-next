#!/usr/bin/env python3
"""Regenerate the committed sanitized fixture projections for the prime
judgment-layer agentic eval (fn-92.11).

Each projection is the `flowctl prime classify --json` emitter output for one of
the six classification fixture families (the same families the CI oracle in
`plugins/flow-next/tests/test_prime_eval.py` builds), captured once and committed
so the agentic eval NEVER depends on a live repo or a live CI path. The family
builders here are a self-contained stdlib copy of the CI builders; if the CI
builders change, re-run this to refresh the snapshots.

A projection is a SANITIZED metadata snapshot: it carries the emitter payload
plus a bounded file listing, and NOTHING from any live checkout. The emitter's
redaction contract (key-names-only, no secret values) already holds; this script
additionally rewrites any home/absolute path in the payload to a stable
placeholder so a committed snapshot never leaks a maintainer-local path.

Usage:
    python3 optimization/prime/gen_fixtures.py            # all six families
    python3 optimization/prime/gen_fixtures.py --real-repo # + this repo's snapshot

Pure stdlib. Never writes outside optimization/prime/fixtures/.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES_DIR = HERE / "fixtures"
REPO_ROOT = HERE.parent.parent
FLOWCTL_PY = REPO_ROOT / "plugins" / "flow-next" / "scripts" / "flowctl.py"


def _pinned_env() -> dict:
    """Deterministic git env (no user config bleed), matching the CI builders."""
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "HOME": tempfile.gettempdir(),
        }
    )
    return env


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=_pinned_env(),
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")


def _write(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _commit_all(repo: Path, msg: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)


# -- family builders (self-contained copy of the CI oracle builders) -----------


def _mk_workspace_parent(tmp: Path) -> Path:
    parent = tmp / "workspace"
    parent.mkdir()
    for i in range(25):  # >20 -> workspace-parent dampener fires
        _init_repo(parent / f"proj-{i}")
    for name in ("acme-api", "acme-web"):  # a prefix family among them
        _init_repo(parent / name)
    target = parent / "acme-api"
    _write(target, "src/main.ts", "export const a = 1\n")
    _commit_all(target, "seed")
    return target


def _mk_tier_a_siblings(tmp: Path) -> Path:
    parent = tmp / "org"
    parent.mkdir()
    for name in ("svc-a", "svc-b"):
        _init_repo(parent / name)
    target = parent / "svc-a"
    _write(target, "main.py", "x = 1\n")
    _commit_all(target, "seed")
    return target


def _mk_tier_b_home_base(tmp: Path) -> Path:
    home = tmp / "home"
    home.mkdir()
    (home / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (home / "CLAUDE.md").write_text("# constellation home base\n", encoding="utf-8")
    for name in ("app", "worker"):
        _init_repo(home / name)
    return home  # non-git parent -> assessed as the home base itself


def _mk_greenfield(tmp: Path) -> Path:
    repo = tmp / "fresh"
    _init_repo(repo)
    _write(repo, "index.js", "console.log(1)\n")
    _commit_all(repo, "init")
    return repo


def _mk_greenfield_x_constellation(tmp: Path) -> Path:
    parent = tmp / "cluster"
    parent.mkdir()
    _init_repo(parent / "sibling")
    repo = parent / "newthing"
    _init_repo(repo)
    _write(repo, "index.ts", "export const x = 1\n")
    _commit_all(repo, "init")
    return repo


def _mk_worktree_sibling(tmp: Path) -> Path:
    parent = tmp / "wt"
    parent.mkdir()
    main = parent / "mainrepo"
    _init_repo(main)
    _write(main, "app.py", "x = 1\n")
    _commit_all(main, "seed")
    _git(main, "worktree", "add", "-q", str(parent / "mainrepo-wt"), "-b", "wt")
    return main


FAMILIES = {
    "workspace-parent": _mk_workspace_parent,
    "tier-a-siblings": _mk_tier_a_siblings,
    "tier-b-home-base": _mk_tier_b_home_base,
    "greenfield": _mk_greenfield,
    "greenfield-x-constellation": _mk_greenfield_x_constellation,
    "worktree-sibling": _mk_worktree_sibling,
}


# -- sanitization + snapshot ---------------------------------------------------

_HOME_RE = re.compile(r"(/Users/[^/\s\"']+|/home/[^/\s\"']+|~)(?:/[^\s\"']*)?")
_TMP_RE = re.compile(r"(/private)?/(?:var/folders|tmp)/[^\s\"']*")


def _sanitize(value):
    """Rewrite any home/absolute/temp path to a stable placeholder so a committed
    projection never carries a maintainer-local path. Structure is preserved."""
    if isinstance(value, str):
        v = _TMP_RE.sub("<fixture-root>", value)
        v = _HOME_RE.sub("<redacted-path>", v)
        return v
    if isinstance(value, list):
        return [_sanitize(x) for x in value]
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    return value


def _classify(root: Path) -> dict:
    out = subprocess.run(
        [sys.executable, str(FLOWCTL_PY), "prime", "classify", "--json", str(root)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def _file_listing(root: Path, limit: int = 40) -> list:
    """A bounded, sorted, relative file listing for the fixture (part of the
    prompt). Bounded to `limit` entries; tool-managed dirs excluded."""
    skip = {".git", ".flow", ".claude", "node_modules"}
    rels = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), root)
            rels.append(rel)
    rels.sort()
    return rels[:limit]


def _snapshot(family: str, emitter: dict, listing: list) -> dict:
    return {
        "family": family,
        "note": (
            "Sanitized metadata projection for the prime judgment-layer agentic "
            "eval. Emitter payload + bounded file listing only; no live checkout, "
            "no CI path, no secret values (key-names-only redaction)."
        ),
        "emitter": _sanitize(emitter),
        "file_listing": _sanitize(listing),
    }


def gen_family(family: str) -> Path:
    builder = FAMILIES[family]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td).resolve()
        target = builder(tmp)
        emitter = _classify(target)
        listing = _file_listing(target)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    out = FIXTURES_DIR / f"{family}.json"
    out.write_text(
        json.dumps(_snapshot(family, emitter, listing), indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def gen_real_repo() -> Path:
    """One real-repo baseline generated from THIS repo via the emitter. Safe:
    the emitter redacts (key-names-only) and this script additionally rewrites
    home/absolute paths to placeholders."""
    emitter = _classify(REPO_ROOT)
    listing = _file_listing(REPO_ROOT, limit=40)
    snap = _snapshot("real-repo-flow-next", emitter, listing)
    snap["note"] = (
        "Example real-repo baseline generated from the flow-next repo itself via "
        "`flowctl prime classify`. SAFE to commit: emitter redaction is "
        "key-names-only and gen_fixtures.py rewrites every home/absolute path to a "
        "placeholder. Demonstrates the committed-projection format for real-repo "
        "baselines - never a live path or CI dependency."
    )
    out = FIXTURES_DIR / "real-repo-flow-next.json"
    out.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate prime eval fixture projections.")
    ap.add_argument("--real-repo", action="store_true", help="also snapshot this repo")
    ap.add_argument("family", nargs="?", choices=sorted(FAMILIES), help="one family only")
    args = ap.parse_args()
    if args.family:
        print("wrote", gen_family(args.family))
        return 0
    for fam in FAMILIES:
        print("wrote", gen_family(fam))
    if args.real_repo:
        print("wrote", gen_real_repo())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
