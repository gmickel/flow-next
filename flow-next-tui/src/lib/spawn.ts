import { stat } from 'node:fs/promises';
import { join, dirname } from 'node:path';

import {
  discoverRuns,
  findRepoRoot,
  clearRepoRootCache as clearRunsRepoRootCache,
} from './runs';

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
 * Default runs directory relative to repo root
 */
const DEFAULT_RUNS_DIR = 'scripts/ralph/runs';

/**
 * Check if path is a readable file (not directory)
 * Since we run via `bash ralph.sh`, we only need it to exist and be a file.
 */
async function isReadableFile(path: string): Promise<boolean> {
  try {
    const s = await stat(path);
    return s.isFile();
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
 * @returns Object with path and searched paths, or null if not found
 */
export async function findRalphScript(
  startDir?: string
): Promise<{ path: string; searchedPaths: string[] } | null> {
  const cwd = startDir ?? process.cwd();
  const repoRoot = await findRepoRoot(cwd);
  const searchedPaths: string[] = [];

  // 1. Repo-local: scripts/ralph/ralph.sh
  const localPath = join(repoRoot, 'scripts', 'ralph', 'ralph.sh');
  searchedPaths.push(localPath);
  if (await isReadableFile(localPath)) {
    return { path: localPath, searchedPaths };
  }

  // 2. Plugin template (for dev/testing in plugin repo)
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
  if (await isReadableFile(templatePath)) {
    return { path: templatePath, searchedPaths };
  }

  return null;
}

/**
 * Spawn ralph as detached process
 *
 * - Spawns ralph.sh with epic ID via EPICS env var
 * - Process runs in new session via setsid (TUI exit won't kill ralph)
 * - Polls for new run directory to get run ID
 *
 * @param epicId Epic ID to work on (e.g., "fn-9")
 * @returns Spawn result with runId and pid
 * @throws RalphNotFoundError if ralph.sh not found
 */
export async function spawnRalph(epicId: string): Promise<SpawnResult> {
  const cwd = process.cwd();
  const repoRoot = await findRepoRoot(cwd);
  const runsDir = join(repoRoot, DEFAULT_RUNS_DIR);

  // Find ralph script
  const result = await findRalphScript(cwd);
  if (!result) {
    const searchedPaths = [
      join(repoRoot, 'scripts', 'ralph', 'ralph.sh'),
      join(
        repoRoot,
        'plugins',
        'flow-next',
        'skills',
        'flow-next-ralph-init',
        'templates',
        'ralph.sh'
      ),
    ];
    throw new RalphNotFoundError(searchedPaths);
  }
  const { path: ralphPath } = result;

  // Get existing runs before spawn (use same runsDir for consistency)
  const existingRuns = await discoverRuns(runsDir);
  const existingIds = new Set(existingRuns.map((r) => r.id));

  // ralph.sh expects to run from its directory for relative paths
  const ralphDir = dirname(ralphPath);

  // Spawn detached using setsid for true process group separation
  // This ensures TUI Ctrl+C won't kill ralph
  // Note: setsid required (macOS/Linux only; Windows not supported for ralph)
  const proc = Bun.spawn(['setsid', 'bash', ralphPath], {
    cwd: ralphDir,
    env: {
      ...process.env,
      EPICS: epicId,
      YOLO: '1', // Required for unattended mode
    },
    stdin: 'ignore',
    stdout: 'ignore',
    stderr: 'ignore',
  });

  const pid = proc.pid;

  // Poll for new run directory (ralph creates it immediately)
  let runId: string | null = null;
  const maxAttempts = 20;
  const pollInterval = 100; // ms

  for (let i = 0; i < maxAttempts; i++) {
    await Bun.sleep(pollInterval);

    try {
      // Re-discover runs and find newest new one
      const currentRuns = await discoverRuns(runsDir);
      const newRuns = currentRuns.filter((r) => !existingIds.has(r.id));

      if (newRuns.length > 0) {
        // Pick the newest (discoverRuns sorts newest first, but be explicit)
        runId = newRuns.reduce((newest, r) =>
          r.id > newest.id ? r : newest
        ).id;
        break;
      }
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
 * @param runsDir Optional runs directory (defaults to scripts/ralph/runs)
 * @returns true if ralph is still running (not complete)
 */
export async function isRalphRunning(
  runId: string,
  runsDir?: string
): Promise<boolean> {
  const cwd = process.cwd();
  const repoRoot = await findRepoRoot(cwd);
  const dir = runsDir ?? join(repoRoot, DEFAULT_RUNS_DIR);
  const progressPath = join(dir, runId, 'progress.txt');

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
 * Delegates to runs.ts cache clearing
 */
export function clearRepoRootCache(): void {
  clearRunsRepoRootCache();
}
