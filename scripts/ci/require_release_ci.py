#!/usr/bin/env python3
"""Require successful main push CI and its aggregate job for the checked-out revision."""
import json
import os
import subprocess
import sys


def gh_pages(endpoint):
    result = subprocess.run(['gh', 'api', '--paginate', '--slurp', endpoint],
                            check=True, capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


def require_ci(repository, sha):
    pages = gh_pages(f'repos/{repository}/actions/workflows/test-flow-next.yml/runs'
                     f'?head_sha={sha}&event=push&branch=main&per_page=100')
    runs = [run for page in pages for run in page['workflow_runs']
            if run['head_sha'] == sha and run['event'] == 'push' and run['head_branch'] == 'main']
    if not runs:
        raise ValueError('No main push CI for this revision')
    run = max(runs, key=lambda item: item['id'])
    if run['status'] != 'completed' or run['conclusion'] != 'success':
        raise ValueError('Latest main push CI is not successful')
    pages = gh_pages(f'repos/{repository}/actions/runs/{run["id"]}/jobs?per_page=100')
    aggregate = [job for page in pages for job in page['jobs'] if job['name'] == 'CI']
    if len(aggregate) != 1 or aggregate[0]['status'] != 'completed' or aggregate[0]['conclusion'] != 'success':
        raise ValueError('Successful CI aggregate job is missing')
    return run['id']


if __name__ == '__main__':
    try:
        sha = subprocess.run(['git', 'rev-parse', 'HEAD'], check=True,
                             capture_output=True, text=True).stdout.strip()
        run_id = require_ci(os.environ['GITHUB_REPOSITORY'], sha)
        print(f'Release CI verified: {sha}, run {run_id}')
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        print(f'Release blocked: {exc}', file=sys.stderr)
        sys.exit(1)
