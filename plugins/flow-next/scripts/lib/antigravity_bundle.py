#!/usr/bin/env python3
"""Build the Antigravity CLI plugin bundle at install time (fn-341).

Invoked by scripts/install-antigravity.sh. Stdlib only (Python 3.11+). No
committed Antigravity tree: the bundle is a copy of the canonical plugin with
these bundle-only changes, installed by `agy plugin install` and then
discarded.

  python3 antigravity_bundle.py <canonical-plugin-dir> <dest>

Pinned Antigravity CLI behaviour (1.5.12/1.5.13, verified live 2026-11-19):

  - A root `plugin.json` makes the directory a native plugin, so
    `agy plugin validate` reads it before install and `agy plugin install`
    copies it without the Claude converter (which would add a
    `flow-next-cmd-<name>` skill per command, doubling the skill catalog).
  - Agent `model` must be an Antigravity tier (`inherit`, `flash_lite`,
    `flash`, `pro`); `sonnet` or `opus` makes the loader skip the agent.
  - `disallowedTools` is ignored and an agent with no `tools` list gets no
    shell. Tool access is a `tools:` YAML list of Antigravity tool names.
  - Commands become hidden stub skills (`disable-model-invocation: true`),
    typed as `/flow-next:<name>`.
  - Plugin rules load from `rules/AGENTS.md` (plain markdown, always on).

Fail closed (named error on stderr, non-zero exit) on:
  UNMAPPED_MODEL            — agent model outside MODEL_TO_TIER, or none
  UNMAPPED_DISALLOWED_TOOL  — token outside DENIED_TOOLS
  UNSUPPORTED_TOOLS_KEY     — a canonical agent declares a `tools:` allowlist
  UNSUPPORTED_FIELD_FORM    — `model`, `tools` or `disallowedTools` written in any
                              form but a plain `key: value` line (quoted key,
                              space before the colon, block list, empty value)
  STUB_NAME_COLLISION       — a command name matches an existing skill
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path


# Canonical agent model alias -> Antigravity tier.
MODEL_TO_TIER: dict[str, str] = {
    "sonnet": "flash",
    "opus": "pro",
    "inherit": "inherit",
}

# Every agent gets these; read-only agents keep the shell, as on Claude Code.
BASE_TOOLS = ("run_command", "read_file", "search_web")

# Canonical disallowedTools token -> the Antigravity tools it withholds.
DENIED_TOOLS: dict[str, tuple[str, ...]] = {
    "Edit": ("edit_file",),
    "Write": ("write_file",),
    "Task": ("invoke_subagent", "ask_question"),
}

# Host manifests, the Codex mirror, the test suite, the commands (replaced by
# stub skills) and the Cursor rule (replaced by rules/AGENTS.md) stay out.
EXCLUDED = shutil.ignore_patterns(
    "codex", ".codex-plugin", ".cursor-plugin", "tests", "commands", "rules",
    "__pycache__", "*.pyc",
)

# setup's host detection keys on this file at the plugin root.
MARKER = ".flow-next-antigravity-bundle"

_FIELD_RE = r"^{}:[ \t]*(.*)$"
_TRANSLATED_KEYS = ("model", "tools", "disallowedTools")
_LOOSE_KEY_RE = re.compile(
    r"^[ \t]*[\"']?(" + "|".join(_TRANSLATED_KEYS) + r")[\"']?[ \t]*:", re.M)


class BundleError(Exception):
    """Named bundle failure. `name` is the stable identifier tests pin."""

    def __init__(self, name: str, detail: str) -> None:
        self.name = name
        super().__init__(f"{name}: {detail}")


def _split_frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.index("\n---", 4)
    return text[:end], text[end:]


def _field(front: str, key: str) -> re.Match[str] | None:
    return re.search(_FIELD_RE.format(re.escape(key)), front, re.M)


def translate_agent(text: str, source: str) -> str:
    """Rewrite one agent's model and tool restriction for Antigravity."""
    parts = _split_frontmatter(text)
    if parts is None:
        raise BundleError("UNMAPPED_MODEL", f"{source}: no frontmatter")
    front, body = parts
    for loose in _LOOSE_KEY_RE.finditer(front):
        line = front[loose.start():].split("\n", 1)[0]
        if not re.match(rf"{loose.group(1)}:[ \t]*\S", line):
            raise BundleError("UNSUPPORTED_FIELD_FORM", f"{source}: {line.strip()}")
    if _field(front, "tools"):
        raise BundleError("UNSUPPORTED_TOOLS_KEY", source)

    model = _field(front, "model")
    alias = model.group(1).strip() if model else ""
    if alias not in MODEL_TO_TIER:
        raise BundleError("UNMAPPED_MODEL", f"{source}: {alias or '(none)'}")
    front = front[: model.start()] + f"model: {MODEL_TO_TIER[alias]}" + front[model.end():]

    withheld: set[str] = set()
    denied = _field(front, "disallowedTools")
    if denied is not None:
        for token in (t.strip() for t in denied.group(1).split(",")):
            if not token:
                continue
            if token not in DENIED_TOOLS:
                raise BundleError("UNMAPPED_DISALLOWED_TOOL", f"{source}: {token}")
            withheld.update(DENIED_TOOLS[token])
    tools = [*BASE_TOOLS] + [t for names in DENIED_TOOLS.values() for t in names
                             if t not in withheld]
    line = "tools: [" + ", ".join(tools) + "]"
    if denied is not None:
        front = front[: denied.start()] + line + front[denied.end():]
    else:
        front = front.rstrip("\n") + "\n" + line
    return front + body


def command_stub(text: str, source: str) -> str:
    """A command file as a hidden skill: same name, description and body."""
    parts = _split_frontmatter(text)
    if parts is None:
        raise BundleError("STUB_NAME_COLLISION", f"{source}: no frontmatter")
    front, body = parts
    keep = [line for line in front[4:].splitlines()
            if line.split(":", 1)[0] in ("name", "description")]
    return "---\n" + "\n".join(keep) + "\ndisable-model-invocation: true" + body


def rules_agents_md(text: str) -> str:
    """The Cursor rule as an always-on plugin rule, scoped by its first sentence."""
    parts = _split_frontmatter(text)
    if parts is None:
        return text
    front, body = parts
    description = _field(front, "description")
    body = body[len("\n---"):].lstrip("\n")
    if description is None:
        return body
    scope = description.group(1).strip().split(". ", 1)[0].rstrip(".")
    return f"{scope}; otherwise ignore this rule.\n\n{body}"


def manifest(claude_manifest: dict) -> dict:
    """Root plugin.json: the fields Antigravity reads from the Claude manifest."""
    author = claude_manifest.get("author")
    if isinstance(author, dict):
        author = {k: author[k] for k in ("name", "url") if k in author}
    out = {key: claude_manifest[key] for key in
           ("name", "version", "description", "homepage", "repository")
           if key in claude_manifest}
    if author:
        out["author"] = author
    return out


def build(plugin: Path, dest: Path) -> None:
    shutil.copytree(plugin, dest, ignore=EXCLUDED)
    for agent in sorted((dest / "agents").glob("*.md")):
        agent.write_text(
            translate_agent(agent.read_text(encoding="utf-8"), agent.name),
            encoding="utf-8",
        )
    skills = dest / "skills"
    for command in sorted((plugin / "commands").glob("*.md")):
        stub = skills / command.stem
        if stub.exists():
            raise BundleError("STUB_NAME_COLLISION", command.stem)
        stub.mkdir()
        (stub / "SKILL.md").write_text(
            command_stub(command.read_text(encoding="utf-8"), command.name),
            encoding="utf-8",
        )
    rule = plugin / "rules" / "flow-next.mdc"
    if rule.is_file():
        (dest / "rules").mkdir()
        (dest / "rules" / "AGENTS.md").write_text(
            rules_agents_md(rule.read_text(encoding="utf-8")), encoding="utf-8"
        )
    claude = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    (dest / "plugin.json").write_text(json.dumps(manifest(claude), indent=2) + "\n",
                                      encoding="utf-8")
    (dest / MARKER).write_text("flow-next Antigravity CLI bundle\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: antigravity_bundle.py <canonical-plugin-dir> <dest>", file=sys.stderr)
        return 2
    try:
        build(Path(argv[0]), Path(argv[1]))
    except BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
