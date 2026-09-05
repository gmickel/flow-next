#!/usr/bin/env python3
"""Conservative CI matrix selection for PR and main push ranges."""
import json
import os
import subprocess

FULL = [{'os': os_name, 'python-version': '3.11'} for os_name in
        ('ubuntu-latest', 'macos-latest', 'windows-latest')]
DOCS = FULL[:1]
WEEKLY = [{'os': 'ubuntu-latest', 'python-version': '3.x'}]


def classify(event, paths):
    units, smokes, run_smokes, stub = FULL, FULL, True, True
    if event == 'schedule':
        units = smokes = WEEKLY
    elif event in ('pull_request', 'push') and paths:
        docs_only = all(
            'tests' not in p.split('/') and
            (p.endswith('.md') or p.startswith(('.flow/specs/', '.flow/tasks/')))
            for p in paths
        )
        stub = any(p.startswith(('scripts/', 'plugins/flow-next/scripts/',
                                 'plugins/flow-next/codex/scripts/', '.github/workflows/'))
                   or p == '.gitattributes' for p in paths)
        if docs_only:
            units, run_smokes = DOCS, False
    return {'units_matrix': units, 'smokes_matrix': smokes,
            'run_smokes': run_smokes, 'run_windows_stub': stub}


def changed_paths(event, base, head):
    if event not in ('pull_request', 'push') or not base or set(base) == {'0'} or not head:
        return None
    separator = '...' if event == 'pull_request' else '..'
    try:
        result = subprocess.run(['git', 'diff', '--name-only', '-z', f'{base}{separator}{head}'],
                                check=True, capture_output=True, timeout=60)
        return result.stdout.decode('utf-8').rstrip('\0').split('\0') if result.stdout else None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None


if __name__ == '__main__':
    event = os.environ['GITHUB_EVENT_NAME']
    paths = changed_paths(event, os.environ.get('BASE_SHA'), os.environ.get('HEAD_SHA'))
    outputs = classify(event, paths)
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
        for key, value in outputs.items():
            stream.write(f'{key}={json.dumps(value, separators=(",", ":"))}\n')
