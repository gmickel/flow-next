#!/usr/bin/env python3
"""Reached-path production-path harness (fn-130.1).

Pure-stdlib. Extends the optimization methodology rather than inventing a new
scoring framework. See README.md.

Modes:
  --self-test                 offline deterministic proofs (no model)
  --freeze-b0                 bootstrap-only: write sanitized B0 when output dir is
                              empty/absent; every counted prompt byte comes from
                              git show BASELINE_COMMIT:<path> (never the live
                              worktree); usable from any HEAD; refuses nonempty
                              targets
  --validate-b0               load + validate every frozen B0 manifest
  --production-path-smoke     authenticated Claude proof → ignored candidate under
                              runs/candidates/ (never touches tracked B0 proof)
  --freeze-b0-smoke           one-time: exclusive-create tracked
                              runs/b0-production-path-smoke.json on pass only;
                              failures stay as candidate evidence
  --fixture <id>              validate one frozen fixture
  --all                       validate-b0 + (optional) production-path smoke when --backend claude

Never mutates canonical skill prompts. No live tracker calls.
B0 manifests are immutable after their initial freeze — never re-run --freeze-b0
against an existing (nonempty) fixtures/b0/. Tracked production-path smoke proof
is write-once via --freeze-b0-smoke; ordinary smoke always writes candidates.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
FIXTURES_B0 = HERE / "fixtures" / "b0"
SYNTHETIC = HERE / "fixtures" / "synthetic"
RUNS = HERE / "runs"
RESULTS = HERE / "results"

# Local imports (same directory — keep import path explicit for unittest loader).
sys.path.insert(0, str(HERE))
import character as character  # noqa: E402
import inventory as inventory  # noqa: E402
import isolation as isolation  # noqa: E402
import privacy as privacy  # noqa: E402
import ratchet as ratchet  # noqa: E402
import trace as trace  # noqa: E402

BASELINE_COMMIT = inventory.BASELINE_COMMIT


# ── freeze / validate ─────────────────────────────────────────────────────────


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _hash_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


FIXTURE_HASH_KEYS = (
    "fixture_id",
    "cluster",
    "baseline",
    "baseline_commit",
    "host",
    "activation",
    "branch_inputs",
    "required_reads",
    "forbidden_reads",
    "prompt_files",
    "oracles",
    "prompt_hashes",
    "metrics",
)


def fixture_hash_body(fx: dict[str, Any]) -> dict[str, Any]:
    """Frozen hash-body contract — freeze and validate use the same keys."""
    return {k: fx[k] for k in FIXTURE_HASH_KEYS if k in fx}


def recompute_fixture_hash(fx: dict[str, Any]) -> str:
    return _hash_obj(fixture_hash_body(fx))


def _read_live_repo_text(repo_rel_path: str) -> Optional[str]:
    """Read UTF-8 text from the live worktree; None if missing."""
    path = REPO_ROOT / repo_rel_path
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _fill_hashes(
    fx: dict[str, Any],
    *,
    sources: Optional[Mapping[str, str]] = None,
    source_reader: Optional[Callable[[str], Optional[str]]] = None,
) -> dict[str, Any]:
    """Hash prompt paths and compute reached-path metrics.

    Default (validation / current-tree): read live ``REPO_ROOT`` files.
    Freeze passes a preflighted ``sources`` map (or ``source_reader``) so
    ``freeze_b0`` never hashes live worktree content.
    """
    if sources is not None and source_reader is not None:
        raise ValueError("pass sources or source_reader, not both")

    def _get(path: str) -> Optional[str]:
        if sources is not None:
            return sources.get(path)
        if source_reader is not None:
            return source_reader(path)
        return _read_live_repo_text(path)

    prompt_hashes: dict[str, str] = {}
    root_text = None
    root_path = None
    # Every prompt_files + required_reads path is hashed (required ⊆ counted).
    paths_to_hash = list(
        dict.fromkeys([*(fx.get("prompt_files") or []), *(fx.get("required_reads") or [])])
    )
    texts: dict[str, str] = {}
    for p in paths_to_hash:
        text = _get(p)
        if text is None:
            prompt_hashes[p] = f"MISSING:{p}"
            continue
        texts[p] = text
        prompt_hashes[p] = character.content_hash(text)
        if p.endswith("/SKILL.md") and root_text is None:
            root_text = text
            root_path = p

    if root_text is None and fx.get("required_reads"):
        rp = fx["required_reads"][0]
        root_path = rp
        if rp not in texts:
            root_text = _get(rp)
            if root_text is None:
                prompt_hashes[rp] = f"MISSING:{rp}"
                root_text = ""
            else:
                prompt_hashes[rp] = character.content_hash(root_text)
                texts[rp] = root_text
        else:
            root_text = texts[rp]

    activated: list[tuple[str, str]] = []
    for p in fx.get("required_reads") or []:
        if p == root_path:
            continue
        if p in texts:
            activated.append((p, texts[p]))
        else:
            text = _get(p)
            if text is not None:
                activated.append((p, text))

    metrics = character.compute_reached_path(
        root_skill_text=root_text or "",
        root_skill_path=root_path
        or (fx["required_reads"][0] if fx.get("required_reads") else "MISSING"),
        activated=activated,
    )
    fx = dict(fx)
    fx["prompt_hashes"] = prompt_hashes
    fx["metrics"] = {
        "reached_path_chars": metrics["reached_path_chars"],
        "reached_path_chars_div_4": metrics["reached_path_chars_div_4"],
        "reached_path_files": metrics["files"],
        "backend_telemetry": None,
        "algorithm": metrics["algorithm"],
    }
    fx["fixture_hash"] = recompute_fixture_hash(fx)
    prov = dict(fx.get("provenance") or {})
    if prov.get("capture_kind") != "backend_run":
        for k, v in inventory.PROVENANCE_DETERMINISTIC_FREEZE.items():
            prov[k] = v
        prov["model"] = None
        prov["cli_version"] = None
    prov["host"] = fx.get("host") or prov.get("host")
    prov["fixture_hash"] = fx["fixture_hash"]
    prov["date_utc"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    fx["provenance"] = prov
    return privacy.scrub_obj(fx)


def git_show_text(
    commit: str, repo_rel_path: str, repo_root: Path = REPO_ROOT
) -> str:
    """Return UTF-8 text of ``repo_rel_path`` at ``commit`` via ``git show``.

    Fail closed on missing git, bad commit, missing path, decode error, or
    nonzero exit — never falls back to the live worktree.
    """
    rel = str(repo_rel_path).replace("\\", "/").lstrip("./")
    if not rel or rel.startswith("/") or ".." in rel.split("/"):
        raise RuntimeError(f"refusing unsafe repo-relative path for git show: {repo_rel_path!r}")
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{commit}:{rel}"],
            capture_output=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "git executable unavailable — cannot read baseline sources for B0 freeze"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git show {commit}:{rel} timed out") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"git show {commit}:{rel} failed ({err or f'exit {proc.returncode}'})"
        )
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"git show {commit}:{rel} is not valid UTF-8") from exc


def inventory_prompt_paths(items: list[dict[str, Any]]) -> list[str]:
    """Deduped ``prompt_files`` + ``required_reads`` across inventory fixtures."""
    paths: list[str] = []
    for fx in items:
        paths.extend(fx.get("prompt_files") or [])
        paths.extend(fx.get("required_reads") or [])
    return list(dict.fromkeys(paths))


def materialize_baseline_sources(
    paths: list[str],
    commit: str = BASELINE_COMMIT,
    repo_root: Path = REPO_ROOT,
) -> dict[str, str]:
    """Preflight: load every path from ``commit`` into memory (no worktree reads)."""
    sources: dict[str, str] = {}
    for p in paths:
        sources[p] = git_show_text(commit, p, repo_root=repo_root)
    return sources


def _output_dir_nonempty(out: Path) -> bool:
    """True if ``out`` exists and is not an empty directory (or is a non-dir)."""
    if not out.exists():
        return False
    if not out.is_dir():
        return True
    try:
        next(out.iterdir())
    except StopIteration:
        return False
    return True


def freeze_b0(output_dir: Optional[Path] = None) -> int:
    """Bootstrap-only B0 freeze.

    Writes sanitized manifests only when:
      1. ``output_dir`` is absent or an empty directory (never rewrite / never
         overwrite leftover manifests after INDEX.json removal), and
      2. every inventory ``prompt_files`` / ``required_reads`` path resolves via
         ``git show BASELINE_COMMIT:<path>`` and is fully materialized in memory
         before any output write (live worktree is never hashed for counted
         prompt bytes). Usable from any HEAD — the baseline commit predates this
         harness, so an exact-HEAD checkout is not required.

    Both guards and full source materialization run before any directory or file
    write. ``output_dir`` defaults to canonical ``fixtures/b0``; tests may pass a
    temp path.
    """
    out = Path(output_dir) if output_dir is not None else FIXTURES_B0
    index_path = out / "INDEX.json"

    # Guard 1 — refuse nonempty targets before any git/source work (immutable B0).
    if _output_dir_nonempty(out):
        try:
            shown = out.relative_to(REPO_ROOT)
        except ValueError:
            shown = out
        detail = (
            f"{index_path.name} present"
            if index_path.is_file()
            else "directory nonempty (INDEX.json may be absent)"
        )
        print(
            f"FAIL: B0 output {shown} is not empty ({detail}) — --freeze-b0 is "
            "bootstrap-only and refuses to overwrite an existing freeze or leftover "
            "manifests. Validate with --validate-b0; do not re-freeze. Use an absent "
            "or empty output directory only for a fresh bootstrap seam.",
            file=sys.stderr,
        )
        return 1

    # Guard 2 — materialize baseline sources in memory before any write.
    items = inventory.inventory()
    paths = inventory_prompt_paths(items)
    try:
        sources = materialize_baseline_sources(paths, commit=BASELINE_COMMIT)
    except RuntimeError as exc:
        print(f"FAIL: baseline source preflight: {exc}", file=sys.stderr)
        return 1

    index = {
        "baseline": "B0",
        "baseline_commit": BASELINE_COMMIT,
        "algorithm": "lf-full-file-on-activation-once-per-path-hash",
        "frozen_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixture_count": len(items),
        "clusters": {},
        "subjective_policy": ratchet.subjective_policy(),
        "privacy": {
            "scrubbed": True,
            "no_live_tracker": True,
            "answer_key_separated": True,
        },
        "lineage": {
            "B0": BASELINE_COMMIT,
            "V1_B1": None,
            "rule": "task 130.2 derives V1/B1; later structural tasks compare only to B1",
        },
        "fixtures": [],
    }
    out.mkdir(parents=True, exist_ok=True)
    for fx in items:
        filled = _fill_hashes(fx, sources=sources)
        cluster_dir = out / filled["cluster"]
        cluster_dir.mkdir(parents=True, exist_ok=True)
        # Filename from fixture_id without cluster prefix if present.
        name = filled["fixture_id"].split(".", 1)[-1] + ".json"
        path = cluster_dir / name
        path.write_text(_stable_json(filled), encoding="utf-8")
        try:
            rel = str(path.relative_to(HERE)).replace("\\", "/")
        except ValueError:
            # Non-canonical temp output (tests): store path relative to out parent.
            rel = str(path).replace("\\", "/")
        index["fixtures"].append(
            {
                "fixture_id": filled["fixture_id"],
                "cluster": filled["cluster"],
                "path": rel,
                "fixture_hash": filled["fixture_hash"],
                "reached_path_chars": filled["metrics"]["reached_path_chars"],
            }
        )
        index["clusters"].setdefault(filled["cluster"], 0)
        index["clusters"][filled["cluster"]] += 1
    index_path.write_text(_stable_json(index), encoding="utf-8")
    try:
        shown_out = out.relative_to(REPO_ROOT)
    except ValueError:
        shown_out = out
    print(f"froze {len(items)} B0 fixtures → {shown_out}")
    print(f"clusters: {index['clusters']}")
    return 0


def _load_all_manifests() -> list[dict[str, Any]]:
    out = []
    for p in sorted(FIXTURES_B0.glob("*/*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def validate_manifest(fx: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for key in (
        "fixture_id",
        "cluster",
        "baseline",
        "baseline_commit",
        "required_reads",
        "forbidden_reads",
        "prompt_hashes",
        "oracles",
        "metrics",
        "provenance",
        "ratchet",
        "privacy",
        "resume",
        "lineage",
        "fixture_hash",
    ):
        if key not in fx:
            errs.append(f"missing field {key}")
    if fx.get("baseline_commit") != BASELINE_COMMIT:
        errs.append(f"baseline_commit mismatch: {fx.get('baseline_commit')}")
    if fx.get("baseline") != "B0":
        errs.append("baseline must be B0 for this freeze")
    # Required/forbidden disjoint.
    overlap = set(fx.get("required_reads") or []) & set(fx.get("forbidden_reads") or [])
    if overlap:
        errs.append(f"required∩forbidden nonempty: {sorted(overlap)}")
    # B0 is immutable original-main evidence. Validate its prompt hashes against
    # the frozen Git source, never the mutable live worktree (which legitimately
    # diverges as soon as task 130.2 creates B1).
    for path, h in (fx.get("prompt_hashes") or {}).items():
        if str(h).startswith("MISSING:"):
            continue
        try:
            source = git_show_text(BASELINE_COMMIT, path)
        except RuntimeError as exc:
            errs.append(f"frozen source unavailable: {path}: {exc}")
            continue
        got = character.content_hash(source)
        if got != h:
            errs.append(f"prompt hash drift: {path}")
    # Every required read must be hashed and counted in reached-path files.
    reached_paths = {
        f.get("path") for f in ((fx.get("metrics") or {}).get("reached_path_files") or [])
    }
    for req in fx.get("required_reads") or []:
        if req not in (fx.get("prompt_hashes") or {}):
            errs.append(f"required_read missing from prompt_hashes: {req}")
        elif str((fx.get("prompt_hashes") or {}).get(req, "")).startswith("MISSING:"):
            errs.append(f"required_read missing from frozen source: {req}")
        if req not in reached_paths:
            errs.append(f"required_read missing from reached_path_files: {req}")
    # Recompute fixture_hash from the frozen hash-body contract; fail closed.
    stored = fx.get("fixture_hash")
    recomputed = recompute_fixture_hash(fx)
    if stored != recomputed:
        errs.append(
            f"fixture_hash mismatch: stored={stored} recomputed={recomputed}"
        )
    # Metrics separation.
    m = fx.get("metrics") or {}
    if "reached_path_chars" not in m or "reached_path_chars_div_4" not in m:
        errs.append("metrics missing reached_path_chars / chars_div_4")
    if m.get("backend_telemetry") not in (None, {}) and not isinstance(
        m.get("backend_telemetry"), (dict, type(None))
    ):
        errs.append("backend_telemetry must be dict or null (separate from chars)")
    # Honest provenance: freeze manifests are not backend runs.
    prov = fx.get("provenance") or {}
    kind = prov.get("capture_kind")
    if kind not in ("deterministic_freeze", "backend_run"):
        errs.append(
            "provenance.capture_kind must be deterministic_freeze or backend_run "
            f"(got {kind!r}; null model/cli alone is not honest provenance)"
        )
    elif kind == "deterministic_freeze":
        if not prov.get("capture_reason"):
            errs.append("deterministic_freeze provenance requires capture_reason")
        if prov.get("model") is not None or prov.get("cli_version") is not None:
            errs.append(
                "deterministic_freeze must keep model/cli_version null "
                "(not a captured backend run)"
            )
    elif kind == "backend_run":
        if not prov.get("model") or not prov.get("cli_version"):
            errs.append("backend_run provenance requires real model and cli_version")
    # Privacy + no live tracker.
    if not (fx.get("privacy") or {}).get("no_live_tracker", False):
        errs.append("privacy.no_live_tracker must be true")
    if (fx.get("branch_inputs") or {}).get("live_tracker") is True:
        errs.append("live_tracker must not be true")
    # Ratchet policy encoded.
    r = fx.get("ratchet") or {}
    if r.get("flat_or_noisy") != "discard":
        errs.append("ratchet.flat_or_noisy must be discard")
    # Version B0 answer keys must freeze current-main behavior, not 130.2 Plan-only.
    if fx.get("cluster") == "version":
        future_as_baseline = {
            "no runtime snippet/version ceremony in Plan",
            "warn once; continue planning; no acknowledgement write",
            "tolerate on read; do not write/use",
            "exact Refresh question/options; stop; instruct /flow-next:setup",
        }
        for o in (fx.get("oracles") or {}).get("output") or []:
            if isinstance(o, dict) and o.get("detail") in future_as_baseline:
                errs.append(
                    "version baseline oracle encodes 130.2/future Plan-only text; "
                    f"move to mutation_targets: {o.get('detail')!r}"
                )
    return errs


def validate_index(
    index: dict[str, Any],
    manifests: list[dict[str, Any]],
    root: Path,
) -> list[str]:
    """Pure INDEX ↔ manifest cross-check (no I/O beyond ``root`` path probes).

    ``root`` is the harness root that INDEX ``path`` values are relative to
    (normally ``optimization/reached-path``). Pass a copied tree for tamper
    tests — never mutate committed B0.
    """
    errs: list[str] = []
    if not manifests:
        errs.append("no B0 manifests")
        return errs
    if index.get("fixture_count") != len(manifests):
        errs.append(
            f"INDEX count {index.get('fixture_count')} != manifests {len(manifests)}"
        )
    expected_clusters = {
        "version",
        "setup",
        "tracker",
        "prime",
        "plan-review",
        "plan",
        "work",
        "strategy",
        "make-pr",
        "pilot",
        "cross-host",
    }
    have = {m["cluster"] for m in manifests}
    missing_clusters = expected_clusters - have
    if missing_clusters:
        errs.append(f"missing clusters {sorted(missing_clusters)}")

    by_id = {m["fixture_id"]: m for m in manifests}
    index_rows = index.get("fixtures") or []
    index_ids = [r.get("fixture_id") for r in index_rows]
    if len(index_ids) != len(set(index_ids)):
        errs.append("INDEX contains duplicate fixture_id rows")
    index_id_set = set(index_ids)
    manifest_id_set = set(by_id)
    if index_id_set != manifest_id_set:
        errs.append(
            "INDEX/manifest id mismatch "
            f"missing={sorted(manifest_id_set - index_id_set)} "
            f"extra={sorted(index_id_set - manifest_id_set)}"
        )
    for row in index_rows:
        fid = row.get("fixture_id")
        if fid not in by_id:
            errs.append(f"{fid}: INDEX fixture_id not in manifests")
            continue
        m = by_id[fid]
        recomputed = recompute_fixture_hash(m)
        if m.get("fixture_hash") != recomputed:
            errs.append(
                f"{fid}: stored fixture_hash != recomputed "
                f"({m.get('fixture_hash')} vs {recomputed})"
            )
        if row.get("fixture_hash") != m.get("fixture_hash"):
            errs.append(f"{fid}: INDEX fixture_hash != manifest")
        if row.get("cluster") != m.get("cluster"):
            errs.append(f"{fid}: INDEX cluster != manifest")
        expected_path = f"fixtures/b0/{m['cluster']}/{fid.split('.', 1)[-1]}.json"
        row_path = row.get("path") or ""
        if row_path != expected_path:
            disk = root / row_path
            path_ok = False
            if disk.is_file():
                try:
                    path_ok = (
                        json.loads(disk.read_text(encoding="utf-8")).get("fixture_id")
                        == fid
                    )
                except (OSError, json.JSONDecodeError):
                    path_ok = False
            if not path_ok:
                errs.append(f"{fid}: INDEX path invalid ({row_path})")
        if row.get("reached_path_chars") != (m.get("metrics") or {}).get(
            "reached_path_chars"
        ):
            errs.append(f"{fid}: INDEX reached_path_chars != manifest metrics")
    return errs


def validate_b0() -> int:
    index_path = FIXTURES_B0 / "INDEX.json"
    if not index_path.is_file():
        print("FAIL: B0 INDEX.json missing — run --freeze-b0", file=sys.stderr)
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))
    manifests = _load_all_manifests()
    index_errs = validate_index(index, manifests, HERE)
    if index_errs:
        for e in index_errs:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    bad = 0
    for m in manifests:
        errs = validate_manifest(m)
        if errs:
            bad += 1
            print(f"FAIL {m.get('fixture_id')}: {errs}", file=sys.stderr)
    if bad:
        print(f"FAIL: {bad}/{len(manifests)} manifests invalid", file=sys.stderr)
        return 1
    have = {m["cluster"] for m in manifests}
    print(f"OK: {len(manifests)} B0 manifests valid across {sorted(have)}")
    return 0


# ── self-test (offline) ───────────────────────────────────────────────────────


def self_test() -> int:
    print("reached-path harness self-test (offline, no model)\n")
    ok = True

    # (1) LF normalization + full-file-on-activation + path/hash dedupe.
    root = "line1\r\nline2\r\n"
    ref_a = "AAA\r\n"
    ref_a2 = "AAA\n"  # same after LF norm
    ref_b = "BBB\n"
    m = character.compute_reached_path(
        root_skill_text=root,
        root_skill_path="skill/SKILL.md",
        activated=[
            ("skill/references/a.md", ref_a),
            ("skill/references/a.md", ref_a2),  # dedupe
            ("skill/references/b.md", ref_b),
            ("skill/references/b.md", ref_b),  # repeated
        ],
    )
    expect = len(character.normalize_lf(root)) + len("AAA\n") + len("BBB\n")
    c1 = m["reached_path_chars"] == expect and len(m["files"]) == 3
    ok &= c1
    print(f"[{'PASS' if c1 else 'FAIL'}] LF + once-per-path/hash character algorithm ({m['reached_path_chars']})")

    # (2) Failed reads excluded — caller simply omits them from activated.
    m2 = character.compute_reached_path(
        root_skill_text="R\n",
        root_skill_path="s/SKILL.md",
        activated=[],  # failed read of cold.md omitted
    )
    c2 = m2["reached_path_chars"] == 2 and len(m2["files"]) == 1
    ok &= c2
    print(f"[{'PASS' if c2 else 'FAIL'}] failed/absent refs excluded from count")

    # (3) Ratchet: flat = discard; improvement + no accuracy loss = keep.
    base_acc = {"e1": True, "e2": True}
    cand_acc = {"e1": True, "e2": True}
    base_m = {"reached_path_chars": 1000, "__lower_better__": ["reached_path_chars"]}
    flat = ratchet.decide_ratchet(
        baseline_accuracy=base_acc,
        candidate_accuracy=cand_acc,
        baseline_metrics=base_m,
        candidate_metrics={"reached_path_chars": 1000, "__lower_better__": ["reached_path_chars"]},
    )
    keep = ratchet.decide_ratchet(
        baseline_accuracy=base_acc,
        candidate_accuracy=cand_acc,
        baseline_metrics=base_m,
        candidate_metrics={"reached_path_chars": 800, "__lower_better__": ["reached_path_chars"]},
    )
    noisy = ratchet.decide_ratchet(
        baseline_accuracy=base_acc,
        candidate_accuracy=cand_acc,
        baseline_metrics=base_m,
        candidate_metrics={"reached_path_chars": 800, "__lower_better__": ["reached_path_chars"]},
        noisy=True,
    )
    c3 = flat["verdict"] == "discard" and keep["verdict"] == "keep" and noisy["verdict"] == "discard"
    ok &= c3
    print(f"[{'PASS' if c3 else 'FAIL'}] ratchet flat/noisy=discard; improvement=keep")

    # (4) Borderline N>=2 + subjective majority.
    bord = ratchet.decide_ratchet(
        baseline_accuracy=base_acc,
        candidate_accuracy=cand_acc,
        baseline_metrics=base_m,
        candidate_metrics={"reached_path_chars": 800, "__lower_better__": ["reached_path_chars"]},
        borderline=True,
        paired_runs=1,
    )
    subj_fail = ratchet.decide_ratchet(
        baseline_accuracy=base_acc,
        candidate_accuracy=cand_acc,
        baseline_metrics=base_m,
        candidate_metrics={"reached_path_chars": 800, "__lower_better__": ["reached_path_chars"]},
        subjective=True,
        majority_votes=[True, False],
    )
    subj_ok = ratchet.decide_ratchet(
        baseline_accuracy=base_acc,
        candidate_accuracy=cand_acc,
        baseline_metrics=base_m,
        candidate_metrics={"reached_path_chars": 800, "__lower_better__": ["reached_path_chars"]},
        subjective=True,
        majority_votes=[True, True, False],
    )
    c4 = (
        bord["verdict"] == "discard"
        and subj_fail["verdict"] == "discard"
        and subj_ok["verdict"] == "keep"
    )
    ok &= c4
    print(f"[{'PASS' if c4 else 'FAIL'}] borderline N>=2 + subjective majority N=3–5")

    # (5) Privacy scrub.
    scrubbed = privacy.scrub_text("mail me at gordon@mickel.tech path=/Users/gordon/x token=sk-abcdefghijklmnop")
    c5 = (
        "gordon@mickel.tech" not in scrubbed
        and "/Users/gordon" not in scrubbed
        and "sk-abcdefghijklmnop" not in scrubbed
    )
    ok &= c5
    print(f"[{'PASS' if c5 else 'FAIL'}] privacy scrub")

    # (6) Isolation tripwire: arena-only write breaches; sentinel/leak still trip.
    with tempfile.TemporaryDirectory(prefix="rp-self-") as td:
        base = Path(td)
        arena = base / "arena"
        arena.mkdir()
        (arena / "keep.txt").write_text("x\n", encoding="utf-8")
        pre = isolation.fs_snapshot(arena)
        sentinel, token, sig = isolation.plant_sentinel(base)
        # Arena-only write — no sentinel touch, no leak.
        (arena / "escaped.txt").write_text("y\n", encoding="utf-8")
        iso_arena = isolation.isolation_report(
            arena, pre, sentinel, token, sig, stdout="clean", stderr=""
        )
        c6a = (
            "escaped.txt" in iso_arena["arena_diff"]["created"]
            and iso_arena["arena_changed"]
            and not iso_arena["clean"]
            and isolation.isolation_breached(iso_arena)
            and not iso_arena["sentinel_modified"]
            and not iso_arena["sentinel_token_leaked"]
        )
        # Sentinel + leak still breach.
        sentinel.write_text("PWNED\n", encoding="utf-8")
        iso = isolation.isolation_report(
            arena, pre, sentinel, token, sig, stdout=token, stderr=""
        )
        c6b = (
            iso["sentinel_modified"]
            and iso["sentinel_token_leaked"]
            and isolation.isolation_breached(iso)
            and not iso["clean"]
        )
        c6 = c6a and c6b
    ok &= c6
    print(f"[{'PASS' if c6 else 'FAIL'}] arena fs-diff + out-of-arena sentinel tripwire")

    # (7) Trace parser: active read present, cold absent; failed excluded.
    # Successful Read requires a matching non-error tool_result (not bare tool_use).
    stream = "\n".join(
        [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "1",
                                "name": "Read",
                                "input": {"file_path": "/arena/skill/references/active.md"},
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "1",
                                "content": "active body",
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "2",
                                "name": "Read",
                                "input": {"file_path": "/arena/skill/references/missing.md"},
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "2",
                                "is_error": True,
                                "content": "ENOENT",
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "3",
                                "name": "Read",
                                "input": {
                                    "file_path": "/arena/skill/references/unpaired.md",
                                    "offset": 1,
                                    "limit": 5,
                                },
                            }
                        ]
                    },
                }
            ),
            json.dumps({"type": "result", "usage": {"input_tokens": 1, "output_tokens": 2}}),
        ]
    )
    reads = trace.parse_stream_json_reads(stream)
    failed = trace.parse_stream_json_failed_reads(stream)
    acts = trace.successful_activations(reads, failed)
    c7 = (
        any(a.endswith("active.md") for a in acts)
        and not any(a.endswith("cold.md") for a in acts)
        and not any(a.endswith("unpaired.md") for a in acts)
        and not any(r["path"].endswith("unpaired.md") for r in reads)
        and any(f["path"].endswith("missing.md") for f in failed)
        and "missing.md" not in "".join(acts)
        and any(
            r.get("offset") is None and r.get("limit") is None
            for r in reads
            if r["path"].endswith("active.md")
        )
    )
    ok &= c7
    print(f"[{'PASS' if c7 else 'FAIL'}] trace: active read + failed excluded + cold non-read")

    # (8) Synthetic skill tree present for production-path smoke.
    c8 = (SYNTHETIC / "SKILL.md").is_file() and (SYNTHETIC / "references" / "active.md").is_file()
    ok &= c8
    print(f"[{'PASS' if c8 else 'FAIL'}] synthetic production-path skill fixture present")

    # (9) Lineage fail-closed.
    lin = ratchet.validate_lineage(
        stage="B1",
        expected_input_hashes={"a": "aaa"},
        observed_input_hashes={"a": "bbb"},
    )
    c9 = lin["ok"] is False
    ok &= c9
    print(f"[{'PASS' if c9 else 'FAIL'}] lineage hash mismatch fail-closed")

    # (10) Claude isolation flags never use --bare / fresh config dir.
    flags = " ".join(isolation.CLAUDE_ISOLATION_FLAGS)
    c10 = (
        "--setting-sources" in flags
        and "project,local" in flags
        and "--no-session-persistence" in flags
        and "--bare" not in flags
    )
    ok &= c10
    print(f"[{'PASS' if c10 else 'FAIL'}] OAuth-preserving isolation flags (no --bare)")

    # (11) Auth envelope: positive usage ⇒ ok; zero usage ⇒ zero_token_auth_failure.
    pos_env = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "OK",
        "usage": {
            "input_tokens": 12,
            "output_tokens": 3,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 100,
        },
        "modelUsage": {
            "claude-haiku-4-5": {
                "inputTokens": 12,
                "outputTokens": 3,
                "cacheCreationInputTokens": 0,
                "cacheReadInputTokens": 100,
            }
        },
    }
    pos = isolation.evaluate_auth_envelope(pos_env, rc=0)
    zero_env = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "OK",
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "modelUsage": {
            "claude-haiku-4-5": {
                "inputTokens": 0,
                "outputTokens": 0,
                "cacheCreationInputTokens": 0,
                "cacheReadInputTokens": 0,
            }
        },
    }
    zero = isolation.evaluate_auth_envelope(zero_env, rc=0)
    parsed = isolation.parse_claude_json_envelope(json.dumps(pos_env))
    c11 = (
        pos.get("ok") is True
        and pos.get("invalid") is False
        and pos.get("reason") == "ok"
        and (pos.get("usage_totals") or {}).get("backend_total", 0) > 0
        and zero.get("ok") is False
        and zero.get("invalid") is True
        and zero.get("reason") == "zero_token_auth_failure"
        and isinstance(parsed, dict)
        and parsed.get("result") == "OK"
    )
    ok &= c11
    print(f"[{'PASS' if c11 else 'FAIL'}] auth JSON envelope: positive vs zero-token")

    # (12) Leak scorer: userEmail residual passes; planted guidance signature fails.
    leak_marker = "REACHED-PATH-LEAK-MARKER-selftest"
    leak_pass = isolation.evaluate_instruction_leak(
        f"UNIQUE_MARKER={leak_marker}; userEmail=gordon@mickel.tech",
        marker=leak_marker,
        rc=0,
    )
    leak_fail = isolation.evaluate_instruction_leak(
        f"UNIQUE_MARKER={leak_marker}\nOwner block from global CLAUDE.md",
        marker=leak_marker,
        rc=0,
    )
    c12 = (
        leak_pass.get("ok") is True
        and leak_pass.get("global_leaks") == []
        and "userEmail" in (leak_pass.get("identity_residual") or [])
        and "gordon@mickel.tech" not in (leak_pass.get("stdout_scrubbed") or "")
        and leak_marker not in (leak_pass.get("stdout_scrubbed") or "")
        and leak_fail.get("ok") is False
        and "Owner block" in (leak_fail.get("global_leaks") or [])
        and "gordon@mickel.tech" not in isolation.GLOBAL_GUIDANCE_NEEDLES
    )
    ok &= c12
    print(
        f"[{'PASS' if c12 else 'FAIL'}] "
        "leak probe: identity residual scrubbed; guidance needles still trip"
    )

    print("\n" + ("SELF-TEST PASSED" if ok else "SELF-TEST FAILED"))
    return 0 if ok else 1


# ── production-path Claude smoke ──────────────────────────────────────────────

B0_SMOKE_FILENAME = "b0-production-path-smoke.json"
CANDIDATES_DIRNAME = "candidates"


def tracked_b0_smoke_path(runs_dir: Path) -> Path:
    """Immutable tracked B0 production-path proof path."""
    return Path(runs_dir) / B0_SMOKE_FILENAME


def candidates_dir(runs_dir: Path) -> Path:
    return Path(runs_dir) / CANDIDATES_DIRNAME


def _safe_status_slug(status: str) -> str:
    raw = (status or "unknown").strip() or "unknown"
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in raw)


def smoke_candidate_basename(
    status: str, *, when: Optional[_dt.datetime] = None
) -> str:
    """UTC microsecond stamp + status — exclusive-create friendly."""
    ts = when or _dt.datetime.now(_dt.timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_dt.timezone.utc)
    else:
        ts = ts.astimezone(_dt.timezone.utc)
    stamp = ts.strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-production-path-smoke-{_safe_status_slug(status)}.json"


def _utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _exclusive_write_text(path: Path, text: str) -> Path:
    """Create ``path`` exclusively (O_EXCL / mode ``x``); never overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as fh:
        fh.write(text)
    return path


def persist_production_path_smoke(
    record: Mapping[str, Any],
    *,
    runs_dir: Path,
    mode: str = "candidate",
    when: Optional[_dt.datetime] = None,
    max_candidate_attempts: int = 16,
) -> tuple[Path, str]:
    """Persist sanitized smoke evidence.

    ``mode="candidate"`` (default / ordinary smoke): always writes under
    ``runs_dir/candidates/`` via exclusive create. Never touches tracked B0.

    ``mode="freeze_b0"``: on ``status==pass`` exclusive-creates the tracked
    ``b0-production-path-smoke.json``; on non-pass (or tracked create race)
    writes candidate evidence only and raises if a pass could not be promoted.

    Returns ``(path, kind)`` where ``kind`` is ``"b0_proof"`` or ``"candidate"``.
    """
    if mode not in ("candidate", "freeze_b0"):
        raise ValueError(f"unknown smoke persist mode: {mode!r}")

    stamp = when or _utc_now()
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=_dt.timezone.utc)
    else:
        stamp = stamp.astimezone(_dt.timezone.utc)

    body = privacy.scrub_obj(dict(record))
    body.setdefault(
        "timestamp_utc",
        stamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    )
    text = _stable_json(body)
    status = str(body.get("status") or "unknown")

    if mode == "freeze_b0" and status == "pass":
        tracked = tracked_b0_smoke_path(runs_dir)
        try:
            return _exclusive_write_text(tracked, text), "b0_proof"
        except FileExistsError as exc:
            # Refuse overwrite; still park the pass as candidate evidence.
            cand = _persist_candidate_smoke(
                text,
                status=status,
                runs_dir=runs_dir,
                when=stamp,
                max_attempts=max_candidate_attempts,
            )
            raise RuntimeError(
                f"tracked B0 smoke already exists at {tracked} — refuse overwrite; "
                f"pass evidence saved as candidate {cand}"
            ) from exc

    cand = _persist_candidate_smoke(
        text,
        status=status,
        runs_dir=runs_dir,
        when=stamp,
        max_attempts=max_candidate_attempts,
    )
    return cand, "candidate"


def _persist_candidate_smoke(
    text: str,
    *,
    status: str,
    runs_dir: Path,
    when: _dt.datetime,
    max_attempts: int,
) -> Path:
    last_err: Optional[BaseException] = None
    for attempt in range(max_attempts):
        ts = when + _dt.timedelta(microseconds=attempt)
        path = candidates_dir(runs_dir) / smoke_candidate_basename(status, when=ts)
        try:
            return _exclusive_write_text(path, text)
        except FileExistsError as exc:
            last_err = exc
            continue
    raise RuntimeError(
        f"could not exclusive-create candidate smoke evidence under "
        f"{candidates_dir(runs_dir)} after {max_attempts} attempts"
    ) from last_err


def tracked_b0_smoke_present(runs_dir: Path) -> bool:
    """True when the immutable tracked proof file already exists (any size)."""
    return tracked_b0_smoke_path(runs_dir).exists()


def production_path_smoke(
    *,
    model: str = "haiku",
    timeout: int = 120,
    freeze_b0: bool = False,
    runs_dir: Optional[Path] = None,
    when: Optional[_dt.datetime] = None,
) -> int:
    """Prove one active direct-reference read and one cold forbidden non-read.

    Ordinary runs (``freeze_b0=False``) always persist sanitized candidate
    evidence under ``runs/candidates/`` and never write the tracked B0 proof.

    ``freeze_b0=True`` (``--freeze-b0-smoke``) refuses if tracked proof already
    exists (before any backend work); on pass exclusive-creates the tracked
    proof; on failure writes candidate evidence only.
    """
    runs = Path(runs_dir) if runs_dir is not None else RUNS
    results = RESULTS if runs_dir is None else (runs.parent / "results")
    runs.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    persist_mode = "freeze_b0" if freeze_b0 else "candidate"
    clock = when  # fixed stamp seam for tests; None → wall clock at persist

    if freeze_b0 and tracked_b0_smoke_present(runs):
        tracked = tracked_b0_smoke_path(runs)
        try:
            shown = tracked.relative_to(REPO_ROOT)
        except ValueError:
            shown = tracked
        print(
            f"FAIL: tracked B0 smoke proof already exists at {shown} — "
            "--freeze-b0-smoke is write-once; use --production-path-smoke for "
            "ordinary candidate evidence.",
            file=sys.stderr,
        )
        return 1

    def _persist(record: Mapping[str, Any]) -> Path:
        path, kind = persist_production_path_smoke(
            record, runs_dir=runs, mode=persist_mode, when=clock
        )
        try:
            shown = path.relative_to(REPO_ROOT)
        except ValueError:
            shown = path
        print(f"wrote {kind} evidence → {shown}")
        return path

    if not shutil.which("claude"):
        # Missing CLI is an invalid/non-run outcome — never soft-SKIP as success
        # (that would let --freeze-b0-smoke falsely succeed without a tracked proof).
        print(
            "INVALID RUN: claude CLI unavailable — cannot run production-path smoke",
            file=sys.stderr,
        )
        _persist(
            {
                "status": "claude_cli_missing",
                "reason": "claude CLI not found on PATH",
                "baseline": "B0",
                "baseline_commit": BASELINE_COMMIT,
                "fixture": "synthetic.production-path-smoke",
            }
        )
        return 1

    auth = isolation.auth_probe(model=model, timeout=min(60, timeout))
    if auth.get("invalid") or not auth.get("ok"):
        print(
            f"INVALID RUN: auth probe failed ({auth.get('reason')}) — "
            "zero-token/auth failure is not a model judgment miss.",
            file=sys.stderr,
        )
        _persist(
            {
                "status": "invalid_auth",
                "auth_probe": privacy.scrub_obj(auth),
                "baseline_commit": BASELINE_COMMIT,
            }
        )
        return 1

    leak = isolation.instruction_leak_probe(model=model, timeout=min(90, timeout))
    if not leak.get("ok"):
        print(f"INVALID RUN: instruction-leak probe failed: {leak}", file=sys.stderr)
        _persist(
            {
                "status": "invalid_leak_probe",
                "auth_probe": privacy.scrub_obj(auth),
                "leak_probe": privacy.scrub_obj(leak),
                "baseline_commit": BASELINE_COMMIT,
            }
        )
        return 1

    with tempfile.TemporaryDirectory(prefix="rp-prod-") as td:
        base = Path(td).resolve()
        arena = isolation.prepare_skill_arena(base, SYNTHETIC)
        skill = arena / "skill"
        sentinel, token, sig = isolation.plant_sentinel(base)
        pre = isolation.fs_snapshot(arena)

        # Ask the model to follow the synthetic skill on route=alpha.
        # Scorer required/forbidden oracles live only here — not in SKILL.md.
        prompt = (
            f"Read {skill / 'SKILL.md'}. That file is your complete operating "
            "instructions — follow it exactly. Input: route=alpha"
        )
        cmd = isolation.claude_base_cmd(model=model, output_format="stream-json") + [
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            "Read",
            "--disallowedTools",
            "Bash,Edit,Write,WebFetch,WebSearch,Agent,Task",
        ]
        rc, out, err, timed_out = isolation.run_cmd(
            cmd,
            cwd=skill,
            prompt=prompt,
            timeout=timeout,
            env=isolation.claude_env(),
        )
        iso = isolation.isolation_report(arena, pre, sentinel, token, sig, out, err)
        iso["breached"] = isolation.isolation_breached(iso)

        reads = trace.parse_stream_json_reads(out)
        failed = trace.parse_stream_json_failed_reads(out)
        acts = trace.successful_activations(reads, failed)
        rels = []
        for a in acts:
            rel = trace.rel_under(skill, a)
            if rel:
                rels.append(rel)

        # External scorer oracles for route=alpha (not disclosed in subject skill text).
        scorer_required = "references/active.md"
        scorer_forbidden = "references/cold.md"
        active_ok = scorer_required in rels or any(
            r.endswith(scorer_required) for r in rels
        )
        cold_read = scorer_forbidden in rels or any(
            r.endswith(scorer_forbidden) for r in rels
        )
        result_obj = trace.parse_result_envelope(out)
        telemetry = trace.backend_telemetry(result_obj)

        # Deterministic reached-path from successful activations under the skill.
        root_text = (skill / "SKILL.md").read_text(encoding="utf-8")
        activated_texts: list[tuple[str, str]] = []
        for rel in rels:
            if rel == "SKILL.md":
                continue
            p = skill / rel
            if p.is_file():
                activated_texts.append((f"fixtures/synthetic/{rel}", p.read_text(encoding="utf-8")))
        metrics = character.compute_reached_path(
            root_skill_text=root_text,
            root_skill_path="fixtures/synthetic/SKILL.md",
            activated=activated_texts,
        )

        loader_trace_precise = True  # Claude stream-json exposed Read tool_use.
        status = "pass"
        if timed_out:
            status = "timeout"
        elif iso["breached"]:
            status = "isolation_breach"
        elif rc != 0:
            status = "backend_error"
        elif not active_ok or cold_read:
            status = "fail"

        # Sanitize absolute arena paths in retained raw spans → skill-relative.
        raw_spans = []
        for r in reads:
            item = dict(r)
            rel = trace.rel_under(skill, r.get("path", ""))
            if rel:
                item["path"] = rel
                item["path_was_absolute"] = True
            raw_spans.append(item)

        record = privacy.scrub_obj(
            {
                "status": status,
                "baseline": "B0",
                "baseline_commit": BASELINE_COMMIT,
                "fixture": "synthetic.production-path-smoke",
                "route": "alpha",
                "scorer_oracles": {
                    "required_reads": [scorer_required],
                    "forbidden_reads": [scorer_forbidden],
                    "note": "oracles are scorer-side only; not present in subject SKILL.md",
                },
                "auth_probe": auth,
                "leak_probe": leak,
                "isolation": {
                    k: iso[k]
                    for k in iso
                    if k != "arena_diff" or True
                },
                "required_read_ok": active_ok,
                "forbidden_read_absent": not cold_read,
                "successful_reads_rel": rels,
                "raw_trace_spans": raw_spans,
                "failed_reads": failed,
                "metrics": {
                    "reached_path_chars": metrics["reached_path_chars"],
                    "reached_path_chars_div_4": metrics["reached_path_chars_div_4"],
                    "reached_path_files": metrics["files"],
                    "backend_telemetry": telemetry,
                },
                "provenance": {
                    "capture_kind": "backend_run",
                    "capture_reason": "authenticated claude production-path smoke",
                    "host": "claude",
                    "model": model,
                    "cli_version": _claude_version(),
                    "date_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d"),
                    "flags": list(isolation.CLAUDE_ISOLATION_FLAGS),
                    "used_bare": False,
                    "used_fresh_config_dir": False,
                    "loader_trace_precise": loader_trace_precise,
                    "rc": rc,
                    "timed_out": timed_out,
                    "smoke_persist_mode": persist_mode,
                },
                "result_text_scrubbed": privacy.scrub_text(
                    (result_obj or {}).get("result", "")[:500]
                ),
                "stderr_tail_scrubbed": isolation.redact_token(err or "", token)[-400:],
                "no_live_tracker": True,
            }
        )
        # Never persist the sentinel token.
        record = json.loads(isolation.redact_token(json.dumps(record), token))

        try:
            _persist(record)
        except RuntimeError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        print(
            f"status={status} active_read={active_ok} cold_absent={not cold_read} "
            f"chars={metrics['reached_path_chars']}"
        )
        if status != "pass":
            return 1
        return 0


def _claude_version() -> str:
    try:
        p = __import__("subprocess").run(
            ["claude", "--version"], capture_output=True, text=True, timeout=15
        )
        return (p.stdout or p.stderr or "").strip() or "unknown"
    except Exception:
        return "unknown"


# ── main ──────────────────────────────────────────────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--freeze-b0", action="store_true")
    ap.add_argument("--validate-b0", action="store_true")
    ap.add_argument("--production-path-smoke", action="store_true")
    ap.add_argument(
        "--freeze-b0-smoke",
        action="store_true",
        help="one-time exclusive-create of tracked b0-production-path-smoke.json on pass",
    )
    ap.add_argument("--fixture", help="validate one fixture_id")
    ap.add_argument("--all", action="store_true", help="validate-b0 (+ smoke if --backend claude)")
    ap.add_argument("--backend", default="none", choices=["none", "claude", "auto"])
    ap.add_argument("--model", default=os.environ.get("REACHED_PATH_MODEL", "haiku"))
    ap.add_argument(
        "--timeout", type=int, default=int(os.environ.get("REACHED_PATH_TIMEOUT", "120"))
    )
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.freeze_b0:
        return freeze_b0()
    if args.validate_b0:
        return validate_b0()
    if args.freeze_b0_smoke:
        return production_path_smoke(
            model=args.model, timeout=args.timeout, freeze_b0=True
        )
    if args.production_path_smoke:
        return production_path_smoke(
            model=args.model, timeout=args.timeout, freeze_b0=False
        )
    if args.fixture:
        manifests = {m["fixture_id"]: m for m in _load_all_manifests()}
        if args.fixture not in manifests:
            print(f"FAIL: unknown fixture {args.fixture}", file=sys.stderr)
            return 1
        errs = validate_manifest(manifests[args.fixture])
        if errs:
            print(f"FAIL: {errs}", file=sys.stderr)
            return 1
        print(f"OK: {args.fixture}")
        return 0
    if args.all:
        rc = validate_b0()
        if rc != 0:
            return rc
        backend = args.backend
        if backend == "auto":
            backend = "claude" if shutil.which("claude") else "none"
        if backend == "claude":
            # Ordinary candidate evidence only — never re-freeze tracked B0.
            return production_path_smoke(
                model=args.model, timeout=args.timeout, freeze_b0=False
            )
        print("validated B0; skipped production-path smoke (no --backend claude)")
        return 0

    ap.error(
        "choose --self-test, --freeze-b0, --validate-b0, --production-path-smoke, "
        "--freeze-b0-smoke, --fixture, or --all"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
