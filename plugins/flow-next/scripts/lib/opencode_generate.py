#!/usr/bin/env python3
"""Generate OpenCode agent files and slash-command stubs at install time (fn-201.2).

Invoked by scripts/install-opencode.sh. Stdlib only (Python 3.11+). No committed
OpenCode tree — callers pass a dest and a paths-file; every dest-relative path
written is appended to the paths-file (one per line) so the installer manifest
picks it up.

CLI (exactly one mode per invocation):

  python3 opencode_generate.py --agents <canonical-agents-dir> <dest> <paths-file>
  python3 opencode_generate.py --commands <canonical-commands-dir> <canonical-skills-dir> <dest> <paths-file>

Pinned OpenCode agent frontmatter (2026-08-20, opencode 1.18.19,
https://opencode.ai/config.json $defs.AgentConfig / $defs.PermissionConfig,
recorded in /tmp/opencode-pins.md):

  description, mode (primary|subagent|all), permission (allow|ask|deny).
  tools: is a DEPRECATED boolean map — never emit it.

permission keys: enumerated read, edit, glob, grep, list, bash, task,
external_directory, todowrite, question, webfetch, websearch, lsp, doom_loop,
skill; additionalProperties accepts any tool name, so write: deny is
schema-valid. The ONLY licensed disallowedTools -> permission mapping:

  Edit  -> edit: deny
  Write -> write: deny   (additionalProperties; not an enumerated key)
  Task  -> task: deny
  Bash  -> bash: deny

Fail closed (named error on stderr, non-zero exit, no file written) on:
  UNMAPPED_DISALLOWED_TOOL              — token outside {Edit, Write, Task, Bash}
  UNREPRESENTABLE_DENIAL                — mapped key not in the pinned output set
  READONLY_DISALLOWEDTOOLS_DISAGREEMENT — readonly: true without Edit AND Write denied

Dropped (not fatal): name, model, color, user-invocable.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# Canonical Claude/Droid disallowedTools token -> OpenCode permission key.
# Anything else is UNMAPPED_DISALLOWED_TOOL.
DISALLOWED_TO_PERMISSION: dict[str, str] = {
    "Edit": "edit",
    "Write": "write",
    "Task": "task",
    "Bash": "bash",
}

# Output-side allowlist. Enumerated PermissionConfig keys plus `write`
# (licensed additionalProperties target). Emitting a key outside this set is
# UNREPRESENTABLE_DENIAL — OpenCode ignoring it would be broader access than
# canonical intent.
PINNED_PERMISSION_KEYS: frozenset[str] = frozenset(
    {
        "read",
        "edit",
        "glob",
        "grep",
        "list",
        "bash",
        "task",
        "external_directory",
        "todowrite",
        "question",
        "webfetch",
        "websearch",
        "lsp",
        "doom_loop",
        "skill",
        "write",
    }
)

PERMISSION_ACTIONS: frozenset[str] = frozenset({"allow", "ask", "deny"})

# Canonical frontmatter keys that carry no permission meaning and are dropped.
# Together with the handled keys below this is a closed allowlist: an unknown
# canonical key fails generation, because a silently dropped permission-shaped
# key (an `allowedTools:` allowlist is an implicit denial) is the failure mode
# the spec calls unacceptable.
DROPPED_KEYS: frozenset[str] = frozenset(
    {"name", "model", "color", "user-invocable"}
)
HANDLED_KEYS: frozenset[str] = frozenset(
    {"description", "disallowedTools", "readonly"}
)

EXCLUDED_COMMANDS: frozenset[str] = frozenset({"setup"})
VERBATIM_COMMANDS: frozenset[str] = frozenset({"uninstall"})

SETUP_EXCLUSION_NOTE = (
    "excluding commands/setup.md (setup is not supported on OpenCode)"
)


class GenerateError(Exception):
    """Named generation failure. `name` is the stable identifier tests pin."""

    def __init__(self, name: str, detail: str) -> None:
        self.name = name
        self.detail = detail
        super().__init__(f"{name}: {detail}")


def _unquote_scalar(raw: str) -> str:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        inner = text[1:-1]
        return inner.replace("\\\\", "\0").replace('\\"', '"').replace("\0", "\\")
    if len(text) >= 2 and text[0] == text[-1] == "'":
        return text[1:-1]
    return text


def _yaml_scalar(text: str) -> str:
    """Emit a YAML plain or double-quoted scalar. Deterministic; no block form."""
    reserved = {
        "true",
        "false",
        "null",
        "yes",
        "no",
        "on",
        "off",
        "~",
        "TRUE",
        "FALSE",
        "NULL",
        "Yes",
        "No",
    }
    needs = (
        not text
        or text in reserved
        or text != text.strip()
        or text[0] in "-?:#&*!|>%@`'\""
        or ": " in text
        or text.endswith(":")
        or " #" in text
        or "\t#" in text
        or any(c in text for c in ",[]{}\n\r\t")
        or any(ord(c) < 0x20 or ord(c) == 0x7F for c in text)
    )
    if not needs:
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    escaped = (
        escaped.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    )
    escaped = "".join(
        ch if ord(ch) >= 0x20 and ord(ch) != 0x7F else f"\\x{ord(ch):02x}"
        for ch in escaped
    )
    return f'"{escaped}"'


def split_frontmatter(text: str, source: Path) -> tuple[dict[str, str], str]:
    """Return (scalar-map, body-after-closing-fence). Body is byte-identical."""
    if text.startswith("---\n"):
        start = 4
        fence = "\n---"
    elif text.startswith("---\r\n"):
        start = 5
        fence = "\r\n---"
    else:
        raise GenerateError(
            "MISSING_FRONTMATTER",
            f"{source} has no opening --- fence",
        )
    idx = text.find(fence, start)
    if idx < 0:
        raise GenerateError(
            "MISSING_FRONTMATTER",
            f"{source} has no closing --- fence",
        )
    inner = text[start:idx]
    body = text[idx + len(fence) :]
    fields: dict[str, str] = {}
    for line in inner.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, raw = stripped.split(":", 1)
        key = key.strip()
        if not key:
            continue
        fields[key] = _unquote_scalar(raw)
    return fields, body


def parse_disallowed_tools(raw: str) -> list[str]:
    """Preserve first-seen order; drop empties. Caller sorts for output."""
    seen: list[str] = []
    for token in raw.split(","):
        item = token.strip()
        if item and item not in seen:
            seen.append(item)
    return seen


def permission_map(tokens: list[str], source: Path) -> dict[str, str]:
    """Translate canonical denials. Fails closed on (a) and (b)."""
    out: dict[str, str] = {}
    for token in tokens:
        key = DISALLOWED_TO_PERMISSION.get(token)
        if key is None:
            raise GenerateError(
                "UNMAPPED_DISALLOWED_TOOL",
                f"token {token!r} in {source} is outside "
                f"{{{', '.join(DISALLOWED_TO_PERMISSION)}}}",
            )
        if key not in PINNED_PERMISSION_KEYS:
            raise GenerateError(
                "UNREPRESENTABLE_DENIAL",
                f"token {token!r} in {source} maps to {key!r}, which is not "
                f"in the pinned PermissionConfig key set",
            )
        out[key] = "deny"
    for key, action in out.items():
        if key not in PINNED_PERMISSION_KEYS:
            raise GenerateError(
                "UNREPRESENTABLE_DENIAL",
                f"emitted permission key {key!r} from {source} is not in the "
                f"pinned PermissionConfig key set",
            )
        if action not in PERMISSION_ACTIONS:
            raise GenerateError(
                "UNREPRESENTABLE_DENIAL",
                f"emitted permission action {action!r} for {key!r} from "
                f"{source} is not allow|ask|deny",
            )
    return out


def check_readonly(fields: dict[str, str], tokens: list[str], source: Path) -> None:
    """readonly: true requires Edit AND Write in disallowedTools. Never drop it."""
    if "readonly" not in fields:
        return
    raw = fields["readonly"].strip().lower()
    if raw != "true":
        return
    denied = set(tokens)
    if "Edit" not in denied or "Write" not in denied:
        raise GenerateError(
            "READONLY_DISALLOWEDTOOLS_DISAGREEMENT",
            f"{source} has readonly: true but disallowedTools does not deny "
            f"both Edit and Write (disallowedTools={tokens})",
        )


def flow_next_prefix(stem: str) -> str:
    """Add the flow-next- prefix exactly once."""
    if stem.startswith("flow-next-"):
        return stem
    return f"flow-next-{stem}"


def render_agent(fields: dict[str, str], body: str, source: Path) -> str:
    unknown = sorted(set(fields) - DROPPED_KEYS - HANDLED_KEYS)
    if unknown:
        raise GenerateError(
            "UNKNOWN_FRONTMATTER_KEY",
            f"{source} carries frontmatter key(s) {unknown} outside the closed "
            "allowlist; refusing to guess whether they carry permission meaning",
        )
    description = fields.get("description", "").strip()
    if not description:
        raise GenerateError(
            "MISSING_DESCRIPTION",
            f"{source} has no description",
        )
    tokens = parse_disallowed_tools(fields.get("disallowedTools", ""))
    check_readonly(fields, tokens, source)
    perms = permission_map(tokens, source)
    lines = [
        "---",
        f"description: {_yaml_scalar(description)}",
        "mode: subagent",
    ]
    if perms:
        lines.append("permission:")
        for key in sorted(perms):
            lines.append(f"  {key}: {perms[key]}")
    lines.append("---")
    return "\n".join(lines) + body


def render_command_stub(description: str, skill_path: Path) -> str:
    lines = [
        "---",
        f"description: {_yaml_scalar(description)}",
        "---",
        "",
        "Read and follow this installed skill exactly:",
        "",
        f"`{skill_path}`",
        "",
        "Forward the command arguments to that skill:",
        "",
        "$ARGUMENTS",
        "",
    ]
    return "\n".join(lines)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def _require_dir(path: Path, label: str) -> Path:
    if not path.is_dir():
        raise GenerateError("MISSING_DIRECTORY", f"{label} not found: {path}")
    return path


def _append_paths(paths_file: Path, rels: list[str]) -> None:
    if not rels:
        return
    paths_file.parent.mkdir(parents=True, exist_ok=True)
    with paths_file.open("a", encoding="utf-8", newline="\n") as fh:
        for rel in rels:
            fh.write(f"{rel}\n")


def generate_agents(agents_dir: Path, dest: Path, paths_file: Path) -> list[str]:
    """Translate every canonical agents/*.md. Writes nothing on failure."""
    agents_dir = _require_dir(agents_dir, "canonical agents dir")
    dest = dest.expanduser().resolve()
    sources = sorted(
        p for p in agents_dir.glob("*.md") if p.is_file() and not p.name.startswith(".")
    )
    if not sources:
        raise GenerateError(
            "MISSING_AGENTS",
            f"no agent markdown files in {agents_dir}",
        )
    planned: list[tuple[Path, bytes, str]] = []
    for src in sources:
        text = src.read_text(encoding="utf-8")
        fields, body = split_frontmatter(text, src)
        rendered = render_agent(fields, body, src)
        stem = flow_next_prefix(src.stem)
        rel = f"agents/{stem}.md"
        planned.append((dest / rel, rendered.encode("utf-8"), rel))
    out_dir = dest / "agents"
    if out_dir.exists() and not out_dir.is_dir():
        raise GenerateError(
            "DEST_NOT_DIRECTORY",
            f"{out_dir} exists and is not a directory",
        )
    rels: list[str] = []
    for path, data, rel in planned:
        _atomic_write_bytes(path, data)
        rels.append(rel)
    _append_paths(paths_file, rels)
    return rels


def _skill_description(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    fields, _body = split_frontmatter(text, skill_md)
    description = fields.get("description", "").strip()
    if not description:
        raise GenerateError(
            "MISSING_DESCRIPTION",
            f"{skill_md} has no description",
        )
    return description


def generate_commands(
    commands_dir: Path,
    skills_dir: Path,
    dest: Path,
    paths_file: Path,
) -> list[str]:
    """Roster: commands/<name>.md whose skills/flow-next-<name>/SKILL.md exists.

    uninstall.md is copied verbatim (whole file). setup.md is excluded by name.
    Writes nothing on failure (the setup note may already have been printed).
    """
    commands_dir = _require_dir(commands_dir, "canonical commands dir")
    skills_dir = _require_dir(skills_dir, "canonical skills dir")
    dest = dest.expanduser().resolve()
    sources = sorted(
        p
        for p in commands_dir.glob("*.md")
        if p.is_file() and not p.name.startswith(".")
    )
    planned: list[tuple[Path, bytes, str]] = []
    for src in sources:
        stem = src.stem
        if stem in EXCLUDED_COMMANDS:
            print(SETUP_EXCLUSION_NOTE)
            continue
        dest_name = f"{flow_next_prefix(stem)}.md"
        rel = f"commands/{dest_name}"
        dest_path = dest / rel
        if stem in VERBATIM_COMMANDS:
            planned.append((dest_path, src.read_bytes(), rel))
            continue
        skill_md = skills_dir / f"flow-next-{stem}" / "SKILL.md"
        if not skill_md.is_file():
            # Phrase-triggered skills have no command file; a command without
            # a skill dir is not in the roster (uninstall is the named exception).
            continue
        description = _skill_description(skill_md)
        installed_skill = dest / "skills" / f"flow-next-{stem}" / "SKILL.md"
        rendered = render_command_stub(description, installed_skill)
        planned.append((dest_path, rendered.encode("utf-8"), rel))
    out_dir = dest / "commands"
    if out_dir.exists() and not out_dir.is_dir():
        raise GenerateError(
            "DEST_NOT_DIRECTORY",
            f"{out_dir} exists and is not a directory",
        )
    rels: list[str] = []
    for path, data, rel in planned:
        _atomic_write_bytes(path, data)
        rels.append(rel)
    _append_paths(paths_file, rels)
    return rels


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate OpenCode agents and slash-command stubs from canonical files.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--agents",
        nargs=3,
        metavar=("CANONICAL_AGENTS_DIR", "DEST", "PATHS_FILE"),
        help="translate agents/*.md into DEST/agents/flow-next-<name>.md",
    )
    group.add_argument(
        "--commands",
        nargs=4,
        metavar=(
            "CANONICAL_COMMANDS_DIR",
            "CANONICAL_SKILLS_DIR",
            "DEST",
            "PATHS_FILE",
        ),
        help="generate DEST/commands/flow-next-<name>.md stubs (uninstall verbatim; setup excluded)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(sys.argv[1:] if argv is None else argv)
        if args.agents is not None:
            agents_dir, dest, paths_file = args.agents
            generate_agents(Path(agents_dir), Path(dest), Path(paths_file))
            return 0
        commands_dir, skills_dir, dest, paths_file = args.commands
        generate_commands(
            Path(commands_dir),
            Path(skills_dir),
            Path(dest),
            Path(paths_file),
        )
        return 0
    except GenerateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
