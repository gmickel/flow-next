import { join, dirname } from 'node:path';
import { readdir } from 'node:fs/promises';

import { discoverRuns } from './runs';

/**
 * Error thrown when ralph.sh cannot be found
 */
export class RalphNotFoundError extends Error {
  searchedPaths: string[];

  constructor(searchedPaths: string[]) {
    const paths = searchedPaths.join(', ');
    const msg = `ralph.sh not found. Run \`/flow-next:ralph-init\` to scaffold scripts/ralph/. Searched: ${paths}`;
    super(msg);
    this.name = 'RalphNotFoundError';
    this.searchedPaths = searchedPaths;
  }
}

/**
 * Spawn result with run info
 */
export interface SpawnResult {
  runId: string;
  pid: number;
}

/**
 * Cached repo root (single-repo usage per process)
 */
let repoRootCache: string | null = null;

/**
 * Find repo root by looking for .git directory
 */
async function findRepoRoot(startDir: string): Promise<string | null> {
  if (repoRootCache) return repoRootCache;

  let dir = startDir;
  while (dir !== dirname(dir)) {
    // Check for .git directory or file (worktrees)
    const gitPath = join(dir, '.git');
    const gitFile = Bun.file(gitPath);
    if (await gitFile.exists()) {
      repoRootCache = dir;
      return dir;
    }
    // Also check .git/HEAD for regular repos
    const gitHead = Bun.file(join(dir, '.git', 'HEAD'));
    if (await gitHead.exists()) {
      repoRootCache = dir;
      return dir;
    }
    dir = dirname(dir);
  }
  return null;
}

/**
 * Check if file exists and is executable
 */
async function isExecutable(path: string): Promise<boolean> {
  const file = Bun.file(path);
  if (!(await file.exists())) return false;

  try {
    // Test execution with --help (any exit code ok, spawn fail = not executable)
    const proc = Bun.spawn(['bash', path, '--help'], {
      stdout: 'pipe',
      stderr: 'pipe',
    });
    await proc.exited;
    return true;
  } catch {
    return false;
  }
}

/**
 * Find ralph.sh location
 *
 * Search order:
 * 1. scripts/ralph/ralph.sh (repo-local after /flow-next:ralph-init)
 * 2. plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh
 * 3. null (caller should show helpful error)
 *
 * @param startDir Starting directory (defaults to cwd)
 * @returns Path to ralph.sh or null if not found
 */
export async function findRalphScript(startDir?: string): Promise<string | null> {
  const cwd = startDir ?? process.cwd();
  const repoRoot = await findRepoRoot(cwd);
  const searchedPaths: string[] = [];

  // 1. Repo-local: scripts/ralph/ralph.sh
  if (repoRoot) {
    const localPath = join(repoRoot, 'scripts', 'ralph', 'ralph.sh');
    searchedPaths.push(localPath);
    if (await isExecutable(localPath)) {
      return localPath;
    }
  }

  // 2. Plugin template (for dev/testing in plugin repo)
  if (repoRoot) {
    const templatePath = join(
      repoRoot,
      'plugins',
      'flow-next',
      'skills',
      'flow-next-ralph-init',
      'templates',
      'ralph.sh'
    );
    searchedPaths.push(templatePath);
    if (await isExecutable(templatePath)) {
      return templatePath;
    }
  }

  return null;
}

/**
 * Spawn ralph as detached process
 *
 * - Spawns ralph.sh with epic ID via EPICS env var
 * - Process runs detached (TUI exit won't kill ralph)
 * - Polls for new run directory to get run ID
 *
 * @param epicId Epic ID to work on (e.g., "fn-9")
 * @returns Spawn result with runId and pid
 * @throws RalphNotFoundError if ralph.sh not found
 */
export async function spawnRalph(epicId: string): Promise<SpawnResult> {
  const cwd = process.cwd();
  const repoRoot = (await findRepoRoot(cwd)) ?? cwd;

  // Find ralph script
  const ralphPath = await findRalphScript(cwd);
  if (!ralphPath) {
    const searchedPaths = [
      join(repoRoot, 'scripts', 'ralph', 'ralph.sh'),
      join(repoRoot, 'plugins', 'flow-next', 'skills', 'flow-next-ralph-init', 'templates', 'ralph.sh'),
    ];
    throw new RalphNotFoundError(searchedPaths);
  }

  // Get existing runs before spawn (to detect new run)
  const existingRuns = await discoverRuns();
  const existingIds = new Set(existingRuns.map((r) => r.id));

  // ralph.sh expects to run from its directory for relative paths
  const ralphDir = dirname(ralphPath);

  // Spawn detached
  const proc = Bun.spawn(['bash', ralphPath], {
    cwd: ralphDir,
    env: {
      ...process.env,
      EPICS: epicId,
      YOLO: '1', // Required for unattended mode
    },
    stdout: 'ignore',
    stderr: 'ignore',
    // Note: Bun doesn't have detached option like Node
    // But stdio: 'ignore' + not awaiting allows parent to exit
  });

  const pid = proc.pid;

  // Poll for new run directory (ralph creates it immediately)
  const runsDir = join(repoRoot, 'scripts', 'ralph', 'runs');
  let runId: string | null = null;
  const maxAttempts = 20;
  const pollInterval = 100; // ms

  for (let i = 0; i < maxAttempts; i++) {
    await Bun.sleep(pollInterval);

    try {
      const entries = await readdir(runsDir);
      for (const entry of entries) {
        if (!existingIds.has(entry)) {
          // Found new run
          runId = entry;
          break;
        }
      }
      if (runId) break;
    } catch {
      // runsDir may not exist yet on first run
      continue;
    }
  }

  if (!runId) {
    // Fallback: generate a placeholder ID (shouldn't happen normally)
    runId = `unknown-${Date.now()}`;
  }

  return { runId, pid };
}

/**
 * Check if ralph is running for a given run
 *
 * Checks progress.txt for COMPLETE marker.
 * No marker = still running.
 *
 * @param runId Run ID to check
 * @returns true if ralph is still running (not complete)
 */
export async function isRalphRunning(runId: string): Promise<boolean> {
  const cwd = process.cwd();
  const repoRoot = (await findRepoRoot(cwd)) ?? cwd;
  const progressPath = join(repoRoot, 'scripts', 'ralph', 'runs', runId, 'progress.txt');

  const file = Bun.file(progressPath);
  if (!(await file.exists())) {
    // No progress file = assume running (just started or crashed early)
    return true;
  }

  try {
    const content = await file.text();
    // Check for COMPLETE marker
    if (
      content.includes('promise=COMPLETE') ||
      content.includes('<promise>COMPLETE</promise>')
    ) {
      return false;
    }
    return true;
  } catch {
    // Unreadable = assume running
    return true;
  }
}

/**
 * Clear cached repo root (for testing)
 */
export function clearRepoRootCache(): void {
  repoRootCache = null;
}
