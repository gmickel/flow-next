#!/usr/bin/env python3
"""Merge Flow-Next role registrations without trusting disposable comment markers.

Requires Python 3.11+. Validate before replacing, preserve unrelated tables and
role overrides, and keep a private backup of every changed existing config.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import tomllib

from normalize_codex_hooks import normalize

BEGIN = '# --- flow-next multi-agent roles (auto-generated) ---'
END = '# --- end flow-next roles ---'
HEADER = re.compile(r'^\s*(\[.*\])\s*(?:#.*)?$')
OWN_COMMENT = re.compile(r'^# (?:--- (?:flow-next multi-agent roles.*|end flow-next roles ---)|Re-run install-codex.sh to regenerate)$')


def sections(text: str) -> list[tuple[tuple[str, ...], str]]:
    """Keep table bodies verbatim; TOML parsing rejects ambiguous/unsupported shapes."""
    result = []
    name: tuple[str, ...] = ()
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        match = HEADER.match(line.rstrip('\n'))
        if match:
            if lines:
                result.append((name, ''.join(lines)))
            obj = tomllib.loads(match[1])
            keys = []
            while isinstance(obj, dict) and len(obj) == 1:
                key, obj = next(iter(obj.items()))
                keys.append(key)
            name = tuple(keys)
            lines = []
        lines.append(line)
    if lines:
        result.append((name, ''.join(lines)))
    return result


def role_data(text: str, key: str) -> dict:
    return tomllib.loads(text)['agents'][key]


def merge(text: str, source: Path, max_threads: int) -> str:
    if max_threads < 1:
        raise ValueError('CODEX_MAX_THREADS must be a positive integer')
    roles = {}
    for path in sorted(source.glob('*.toml')):
        roles[path.stem.replace('-', '_')] = (path.stem, tomllib.loads(path.read_text())['description'])
    if not roles:
        raise ValueError('No generated Codex roles found')

    original_sections = sections(text)

    # Remove only generator comments and the historically misplaced cap between
    # the opening marker and first table. Never delete an entire marked region.
    cleaned = []
    preamble = False
    for line in text.splitlines(keepends=True):
        if line.strip() == BEGIN:
            preamble = True
        if HEADER.match(line.rstrip('\n')):
            preamble = False
        if preamble and re.match(r'^max_threads\s*=', line):
            continue
        if OWN_COMMENT.match(line.rstrip('\n')):
            continue
        cleaned.append(line)
    # Older installers emitted a second, explicitly owned [features] block.
    # Migrate only the known switch-only shape; never discard user settings.
    text = ''.join(cleaned)
    legacy = re.compile(r'^# --- flow-next features[^\n]*\n(.*?)^# --- end flow-next features ---\n?', re.M | re.S)
    def retire_features(match: re.Match) -> str:
        data = tomllib.loads(match[1])
        if set(data) != {'features'} or set(data['features']) - {'hooks', 'codex_hooks', 'multi_agent'}:
            raise ValueError('Customized legacy feature block requires manual reconciliation')
        return ''
    text = normalize(legacy.sub(retire_features, text))
    kept = []
    extras: dict[str, str] = {}
    have_agents = False
    for name, block in sections(text):
        if len(name) == 2 and name[0] == 'agents' and name[1] in roles:
            key = name[1]
            data = role_data(block, key)
            expected = f'agents/{roles[key][0]}.toml'
            if data.get('config_file') != expected:
                raise ValueError(f'Role agents.{key} is not owned by Flow-Next; config left unchanged')
            # Preserve custom model/other fields on owned roles. Conflicting
            # duplicate customizations require a human decision, not last-wins.
            extra = ''.join(line for line in block.splitlines(keepends=True)[1:]
                            if not re.match(r'^\s*(description|config_file)\s*=', line)).strip()
            if key in extras and extras[key] != extra and extra and extras[key]:
                raise ValueError(f'Conflicting duplicate overrides for agents.{key}')
            extras[key] = extra or extras.get(key, '')
            continue
        if name == ('agents',):
            if have_agents:
                raise ValueError('Duplicate [agents] table; config left unchanged')
            have_agents = True
            lines = block.splitlines(keepends=True)
            block = lines[0] + f'max_threads = {max_threads}\n' + ''.join(
                line for line in lines[1:] if not re.match(r'^\s*(max_threads|max_concurrent_threads_per_session)\s*=', line))
        kept.append(block)
    base = ''.join(kept).rstrip() + '\n'
    if not have_agents:
        base += f'\n[agents]\nmax_threads = {max_threads}\n'
    # Retain the installer's existing root feature switch without moving it
    # into the last table. Other feature normalization is delegated above.
    if 'multi_agent' not in tomllib.loads(base):
        base = 'multi_agent = true\n' + base
    result = base + '\n' + BEGIN + '\n# Re-run install-codex.sh to regenerate\n'
    for key, (stem, description) in roles.items():
        result += f'\n[agents.{key}]\ndescription = {json.dumps(description)}\nconfig_file = {json.dumps("agents/" + stem + ".toml")}\n'
        if extras.get(key):
            result += extras[key] + '\n'
    result += '\n' + END + '\n'
    parsed = tomllib.loads(result)
    # A marker-looking line inside a user TOML string is data, not ownership.
    # Refuse any unexpected semantic change outside generated role fields.
    for name, block in original_sections:
        if len(name) == 2 and name[0] == 'agents' and name[1] in roles:
            continue
        before = tomllib.loads(normalize(block) if name == ('features',) else block)
        after = parsed
        for key in name:
            before = before[key]
            after = after[key]
        if isinstance(before, list):
            if not isinstance(after, list) or any(item not in after for item in before):
                raise ValueError('Unrelated array table would change; original preserved')
            continue
        allowed = {'max_threads', 'max_concurrent_threads_per_session'} if name == ('agents',) else set()
        if name == ('features',):
            allowed = {'hooks', 'codex_hooks', 'multi_agent'}
        for key, value in before.items():
            if key not in allowed and after.get(key) != value:
                raise ValueError('Unrelated configuration would change; original preserved')
    return result


def update(path: Path, source: Path, max_threads: int, check: bool = False) -> None:
    path = path.resolve()
    original = path.read_text() if path.exists() else ''
    result = merge(original, source, max_threads)
    if check or result == original:
        return
    fd, temp = tempfile.mkstemp(prefix='.flow-next-config-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(result)
        if path.exists():
            os.chmod(temp, path.stat().st_mode & 0o777)
            backup_fd, backup = tempfile.mkstemp(prefix='config.toml.pre-flow-next-', dir=path.parent)
            os.close(backup_fd)
            shutil.copyfile(path, backup)
        if (path.read_text() if path.exists() else '') != original:
            raise ValueError('Config changed concurrently; retry without overwriting it')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('--max-threads', type=int, default=12)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        update(args.config, args.source, args.max_threads, args.check)
    except (ValueError, OSError) as exc:
        # Do not echo configuration content (it can contain credentials).
        parser.exit(1, f'Codex config merge refused: {type(exc).__name__}. Original config preserved; inspect conflicting TOML or role ownership.\n')


if __name__ == '__main__':
    main()
