"""Frozen reached-path character algorithm (fn-130 R1).

Deterministic source-size measure — NOT interchangeable with backend token,
cache, or wall-time telemetry.

Algorithm (immutable for B0 → V1/B1 → candidate lineage):
  1. Normalize every counted prompt file to LF before counting Unicode chars.
  2. Count the complete root SKILL.md exactly once.
  3. Count the complete content of each successfully reached direct reference
     exactly once, deduplicated by normalized repo-relative path + content hash.
     A host range/subset read activates the COMPLETE referenced file once
     (reference activation, not tool span size, is the contract).
  4. Exclude failed reads, repeated reads, catalog metadata, tool output, and
     host-injected text.
  5. Codex fixtures count actual regenerated mirror files, not canonical proxies.
  6. Raw trace spans remain separate evidence from this calculation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Optional

CHARS_PER_TOKEN_EQUIV = 4


def normalize_lf(text: str) -> str:
    """Normalize newlines to LF without altering other Unicode characters."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def content_hash(text: str) -> str:
    """SHA-256 of LF-normalized UTF-8 bytes."""
    return hashlib.sha256(normalize_lf(text).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return content_hash(path.read_text(encoding="utf-8"))


def char_count(text: str) -> int:
    return len(normalize_lf(text))


def chars_div_4(chars: int) -> float:
    return chars / CHARS_PER_TOKEN_EQUIV


def normalize_repo_rel(path: str | Path, repo_root: Optional[Path] = None) -> str:
    """Normalize to a forward-slash repo-relative path (no leading ./)."""
    p = Path(path)
    if repo_root is not None:
        try:
            p = p.resolve().relative_to(repo_root.resolve())
        except ValueError:
            p = Path(path)
    s = p.as_posix().lstrip("./")
    return s


def compute_reached_path(
    *,
    root_skill_text: str,
    root_skill_path: str,
    activated: Iterable[tuple[str, str]],
) -> dict[str, Any]:
    """Compute deterministic reached-path size from already-loaded texts.

    ``activated`` is an iterable of ``(repo_relative_path, file_text)`` for each
    successfully reached direct reference (NOT including the root skill — the
    root is always counted separately and exactly once). Failed reads must not
    appear here. Repeated path+hash pairs collapse to one.
    """
    files: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    total = 0

    root_path = normalize_repo_rel(root_skill_path)
    root_norm = normalize_lf(root_skill_text)
    root_h = content_hash(root_norm)
    root_chars = len(root_norm)
    files.append(
        {
            "path": root_path,
            "role": "root_skill",
            "content_hash": root_h,
            "chars_lf": root_chars,
        }
    )
    total += root_chars
    seen.add((root_path, root_h))

    for raw_path, text in activated:
        path = normalize_repo_rel(raw_path)
        norm = normalize_lf(text)
        h = content_hash(norm)
        key = (path, h)
        if key in seen:
            continue
        seen.add(key)
        n = len(norm)
        files.append(
            {
                "path": path,
                "role": "direct_reference",
                "content_hash": h,
                "chars_lf": n,
            }
        )
        total += n

    return {
        "algorithm": "lf-full-file-on-activation-once-per-path-hash",
        "files": files,
        "reached_path_chars": total,
        "reached_path_chars_div_4": chars_div_4(total),
        # Raw trace spans are intentionally absent here — callers attach them
        # under a separate `raw_trace_spans` field.
    }


def compute_reached_path_from_paths(
    repo_root: Path,
    root_skill: Path,
    activated_paths: Iterable[Path],
    *,
    mirror_root: Optional[Path] = None,
) -> dict[str, Any]:
    """Load texts from disk and compute reached-path.

    When ``mirror_root`` is set (Codex fixtures), resolve activated paths under
    the regenerated mirror tree rather than the canonical plugin tree.
    """
    root = root_skill if mirror_root is None else _mirror_map(root_skill, repo_root, mirror_root)
    root_text = root.read_text(encoding="utf-8")
    activated: list[tuple[str, str]] = []
    for p in activated_paths:
        src = p if mirror_root is None else _mirror_map(p, repo_root, mirror_root)
        # Successful read only — missing files are excluded (failed reads).
        if not src.is_file():
            continue
        rel = normalize_repo_rel(src, repo_root if mirror_root is None else mirror_root.parent.parent)
        # Prefer canonical-relative labels when counting mirror content so
        # manifests stay addressable; content still comes from the mirror file.
        if mirror_root is not None:
            try:
                rel = normalize_repo_rel(p, repo_root)
            except Exception:
                pass
        activated.append((rel, src.read_text(encoding="utf-8")))
    return compute_reached_path(
        root_skill_text=root_text,
        root_skill_path=normalize_repo_rel(root_skill, repo_root),
        activated=activated,
    )


def _mirror_map(canonical: Path, repo_root: Path, mirror_root: Path) -> Path:
    """Map a canonical plugin path to its Codex-mirror twin when present."""
    try:
        rel = canonical.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return canonical
    # Canonical: plugins/flow-next/skills/... → mirror: plugins/flow-next/codex/skills/...
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "plugins" and parts[1] == "flow-next":
        rest = parts[2:]
        if rest and rest[0] != "codex":
            candidate = mirror_root.joinpath(*rest)
            if candidate.is_file():
                return candidate
    return canonical
