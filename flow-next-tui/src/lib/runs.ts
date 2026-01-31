import { readdir, stat } from 'node:fs/promises';
import { join, basename, dirname } from 'node:path';

import type { Run } from './types';

/**
 * Extended run details beyond basic Run interface
 */
export interface RunDetails {
  id: string;
  path: string;
  epics: string[];
  active: boolean;
  iteration: number;
  startedAt?: string;
  hasProgress: boolean;
  hasAttempts: boolean;
  hasBranches: boolean;
}

/**
 * Receipt status for a task
 */
export interface ReceiptStatus {
  plan?: boolean;
  impl?: boolean;
}

/**
 * Default runs directory relative to repo root
 */
const DEFAULT_RUNS_DIR = 'scripts/ralph/runs';

/**
 * Cached repo roots by starting directory
 */
const repoRootCache = new Map<string, string>();

/**
 * Find repo root by walking up from startDir looking for .git or .flow directory
 */
export async function findRepoRoot(startDir?: string): Promise<string> {
  const start = startDir ?? process.cwd();

  // Check cache for this startDir
  const cached = repoRootCache.get(start);
  if (cached) return cached;

  let dir = start;
  while (dir !== dirname(dir)) {
    // Check for .git directory or file (worktrees use .git file)
    const gitPath = join(dir, '.git');
    try {
      const s = await stat(gitPath);
      // .git can be directory (regular) or file (worktrees)
      if (s.isDirectory() || s.isFile()) {
        repoRootCache.set(start, dir);
        return dir;
      }
    } catch {
      // Continue searching
    }

    // Check for .flow directory
    const flowPath = join(dir, '.flow');
    try {
      const s = await stat(flowPath);
      if (s.isDirectory()) {
        repoRootCache.set(start, dir);
        return dir;
      }
    } catch {
      // Continue searching
    }

    dir = dirname(dir);
  }

  // Fall back to start if no markers found
  repoRootCache.set(start, start);
  return start;
}

/**
 * Clear cached repo root (for testing)
 */
export function clearRepoRootCache(): void {
  repoRootCache.clear();
}

/**
 * Regex for valid task IDs:
 * - fn-N (epic only)
 * - fn-N-xxx (legacy 3-char suffix)
 * - fn-N-slug (new slug suffix, e.g., fn-1-add-oauth)
 * - fn-N.M, fn-N-xxx.M, fn-N-slug.M (task variants)
 */
const TASK_ID_PATTERN = /^fn-\d+(?:(?:-[a-z0-9][a-z0-9-]*[a-z0-9])|(?:-[a-z0-9]{1,3}))?(?:\.\d+)?$/;

/**
 * Regex for valid run IDs (alphanumeric, hyphens, underscores only - no path traversal)
 * Matches: YYYYMMDDTHHMMSSZ-hostname-user-pid-rand (real) or YYYY-MM-DD-NNN (test)
 */
const RUN_ID_PATTERN = /^[\w-]+$/;

/**
 * Validate task ID to prevent path traversal
 * @throws Error if taskId is invalid
 */
function validateTaskId(taskId: string): void {
  if (!TASK_ID_PATTERN.test(taskId)) {
    throw new Error(
      `Invalid task ID: ${taskId}. Expected format: fn-N, fn-N-slug, fn-N.M, or fn-N-slug.M (e.g., fn-1, fn-1-add-auth, fn-1.2, fn-1-add-auth.2)`
    );
  }
}

/**
 * Validate run ID to prevent path traversal
 * @throws Error if runId is invalid
 */
function validateRunId(runId: string): void {
  if (!RUN_ID_PATTERN.test(runId) || runId.includes('..')) {
    throw new Error(
      `Invalid run ID: ${runId}. Must be alphanumeric with hyphens/underscores only.`
    );
  }
}

/**
 * Check if a directory exists
 */
async function dirExists(path: string): Promise<boolean> {
  try {
    const s = await stat(path);
    return s.isDirectory();
  } catch {
    return false;
  }
}

/**
 * Check if a file exists
 */
async function fileExists(path: string): Promise<boolean> {
  const file = Bun.file(path);
  return file.exists();
}

/**
 * Compare run IDs for sorting (newest first).
 * Uses lexicographic comparison which works correctly for:
 * - YYYYMMDDTHHMMSSZ-hostname-user-pid-rand format (real Ralph runs)
 * - YYYY-MM-DD-NNN format (test fixtures)
 * ISO-like timestamps ensure correct ordering.
 */
function compareRunIds(a: string, b: string): number {
  // Lexicographic descending (b > a = newest first)
  return b.localeCompare(a);
}

/**
 * Check if run is active (not completed)
 * Parses progress.txt, looks for line containing `promise=COMPLETE` or `<promise>COMPLETE</promise>`
 */
export async function isRunActive(runPath: string): Promise<boolean> {
  const progressPath = join(runPath, 'progress.txt');
  const file = Bun.file(progressPath);

  if (!(await file.exists())) {
    // No progress file = assume active (just started or crashed early)
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
    // Unreadable/corrupt file = assume active (safer default)
    return true;
  }
}

/**
 * Get current iteration number by counting iter-*.log files
 */
async function getIterationCount(runPath: string): Promise<number> {
  try {
    const entries = await readdir(runPath);
    const iterLogs = entries.filter(
      (e) => e.startsWith('iter-') && e.endsWith('.log')
    );
    return iterLogs.length;
  } catch {
    return 0;
  }
}

/**
 * Get epics from run - checks run.json first (all epics), then progress.txt (current epic)
 * Returns array of epic IDs. Empty array if none found.
 */
async function getRunEpics(runPath: string): Promise<string[]> {
  // Primary: check run.json for epics array (the authoritative source when EPICS is set)
  const runJsonPath = join(runPath, 'run.json');
  const runJsonFile = Bun.file(runJsonPath);

  if (await runJsonFile.exists()) {
    try {
      const runJson = await runJsonFile.json();
      if (Array.isArray(runJson?.epics) && runJson.epics.length > 0) {
        return runJson.epics.filter((e: unknown) => typeof e === 'string');
      }
    } catch {
      // Ignore parse errors, try other sources
    }
  }

  // Fallback: parse progress.txt for epic= patterns (collect unique epics)
  const progressPath = join(runPath, 'progress.txt');
  const progressFile = Bun.file(progressPath);

  if (await progressFile.exists()) {
    try {
      const content = await progressFile.text();
      const matches = content.match(/epic=(fn-\d+(?:(?:-[a-z0-9][a-z0-9-]*[a-z0-9])|(?:-[a-z0-9]{1,3}))?)/g);
      if (matches && matches.length > 0) {
        const epics = matches.map((m) => m.replace('epic=', ''));
        // Return unique epics in order of appearance
        return [...new Set(epics)];
      }
    } catch {
      // Ignore read errors
    }
  }

  // Fallback: check branches.json for epic field (legacy single-epic)
  const branchesPath = join(runPath, 'branches.json');
  const branchesFile = Bun.file(branchesPath);

  if (await branchesFile.exists()) {
    try {
      const branches = await branchesFile.json();
      if (branches?.epic && typeof branches.epic === 'string') {
        return [branches.epic];
      }
    } catch {
      // Ignore parse errors
    }
  }

  return [];
}

/**
 * Get run start time from directory mtime or log files
 */
async function getRunStartTime(runPath: string): Promise<string | undefined> {
  try {
    const s = await stat(runPath);
    return s.birthtime?.toISOString() ?? s.mtime.toISOString();
  } catch {
    return undefined;
  }
}

/**
 * Discover all runs in the runs directory
 * @param runsDir Path to runs directory (defaults to scripts/ralph/runs relative to repo root)
 * @returns Array of Run objects sorted by date (newest first)
 */
export async function discoverRuns(runsDir?: string): Promise<Run[]> {
  const repoRoot = await findRepoRoot();
  const dir = runsDir ?? join(repoRoot, DEFAULT_RUNS_DIR);

  if (!(await dirExists(dir))) {
    return [];
  }

  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }

  // Filter to directories only (runs are directories) - parallel stat
  const entryChecks = await Promise.all(
    entries.map(async (entry) => {
      const entryPath = join(dir, entry);
      const isDir = await dirExists(entryPath);
      return { entry, isDir };
    })
  );
  const runDirs = entryChecks.filter((e) => e.isDir).map((e) => e.entry);

  // Build Run objects in parallel
  const runs = await Promise.all(
    runDirs.map(async (runId) => {
      const runPath = join(dir, runId);
      const [active, iteration, epics, startedAt] = await Promise.all([
        isRunActive(runPath),
        getIterationCount(runPath),
        getRunEpics(runPath),
        getRunStartTime(runPath),
      ]);
      return {
        id: runId,
        path: runPath,
        epics,
        active,
        iteration,
        startedAt,
      };
    })
  );

  // Sort by run ID (lexicographic descending = newest first)
  runs.sort((a, b) => compareRunIds(a.id, b.id));

  return runs;
}

/**
 * Get the latest (most recent) run by ID.
 * Computes the latest run regardless of input array order.
 * Uses lexicographic comparison (higher = newer for ISO-like run IDs).
 */
export function getLatestRun(runs: Run[]): Run | undefined {
  if (runs.length === 0) return undefined;
  return runs.reduce((latest, run) => (run.id > latest.id ? run : latest));
}

/**
 * Get detailed information about a run
 */
export async function getRunDetails(runPath: string): Promise<RunDetails> {
  const id = basename(runPath);
  const [active, iteration, epics, startedAt] = await Promise.all([
    isRunActive(runPath),
    getIterationCount(runPath),
    getRunEpics(runPath),
    getRunStartTime(runPath),
  ]);

  const [hasProgress, hasAttempts, hasBranches] = await Promise.all([
    fileExists(join(runPath, 'progress.txt')),
    fileExists(join(runPath, 'attempts.json')),
    fileExists(join(runPath, 'branches.json')),
  ]);

  return {
    id,
    path: runPath,
    epics,
    active,
    iteration,
    startedAt,
    hasProgress,
    hasAttempts,
    hasBranches,
  };
}

/**
 * Get receipt status for a task
 * Receipts are in runs/<id>/receipts/ as plan-<task-id>.json and impl-<task-id>.json
 * @throws Error if taskId is invalid (path traversal protection)
 */
export async function getReceiptStatus(
  runPath: string,
  taskId: string
): Promise<ReceiptStatus> {
  validateTaskId(taskId);

  const receiptsDir = join(runPath, 'receipts');
  const planPath = join(receiptsDir, `plan-${taskId}.json`);
  const implPath = join(receiptsDir, `impl-${taskId}.json`);

  const [hasPlan, hasImpl] = await Promise.all([
    fileExists(planPath),
    fileExists(implPath),
  ]);

  return {
    plan: hasPlan ? true : undefined,
    impl: hasImpl ? true : undefined,
  };
}

/**
 * Get block reason if task is blocked
 * Block files: .flow/blocks/block-<task-id>.md or runs/<id>/block-<task-id>.md
 * @throws Error if taskId is invalid (path traversal protection)
 */
export async function getBlockReason(
  taskId: string,
  runPath?: string
): Promise<string | null> {
  validateTaskId(taskId);

  // Check .flow/blocks first (relative to repo root)
  const repoRoot = await findRepoRoot();
  const flowBlockPath = join(repoRoot, '.flow', 'blocks', `block-${taskId}.md`);
  const flowBlockFile = Bun.file(flowBlockPath);

  if (await flowBlockFile.exists()) {
    return flowBlockFile.text();
  }

  // Check run-specific block file if runPath provided
  if (runPath) {
    const runBlockPath = join(runPath, `block-${taskId}.md`);
    const runBlockFile = Bun.file(runBlockPath);

    if (await runBlockFile.exists()) {
      return runBlockFile.text();
    }
  }

  return null;
}

/**
 * Result from validateRun with optional warnings
 */
export interface ValidateRunResult {
  run: Run;
  warnings: string[];
}

/**
 * Validate a run ID and return the run if found.
 * Fast-paths by checking if run directory exists before scanning all runs.
 * @throws Error with helpful message if run not found or invalid
 * @returns Run with any warnings (e.g., corrupt run)
 */
export async function validateRun(
  runId: string,
  runsDir?: string
): Promise<ValidateRunResult> {
  // Validate runId to prevent path traversal
  validateRunId(runId);

  const repoRoot = await findRepoRoot();
  const dir = runsDir ?? join(repoRoot, DEFAULT_RUNS_DIR);
  const runPath = join(dir, runId);

  // Fast path: check if run directory exists
  if (await dirExists(runPath)) {
    const warnings: string[] = [];
    const progressPath = join(runPath, 'progress.txt');

    if (!(await fileExists(progressPath))) {
      warnings.push(`Run '${runId}' may be corrupt (missing progress.txt)`);
    }

    // Get run details for this specific run
    const [active, iteration, epics, startedAt] = await Promise.all([
      isRunActive(runPath),
      getIterationCount(runPath),
      getRunEpics(runPath),
      getRunStartTime(runPath),
    ]);

    return {
      run: { id: runId, path: runPath, epics, active, iteration, startedAt },
      warnings,
    };
  }

  // Run not found - enumerate available runs (cheap readdir only)
  let available = 'none';
  try {
    const entries = await readdir(dir);
    const runDirs = await Promise.all(
      entries.map(async (entry) => {
        const entryPath = join(dir, entry);
        return (await dirExists(entryPath)) ? entry : null;
      })
    );
    const validRuns = runDirs.filter((e): e is string => e !== null);
    if (validRuns.length > 0) {
      // Sort for consistent output
      validRuns.sort((a, b) => b.localeCompare(a));
      available = validRuns.join(', ');
    }
  } catch {
    // Directory doesn't exist or unreadable
  }

  throw new Error(`Run '${runId}' not found. Available: ${available}`);
}
