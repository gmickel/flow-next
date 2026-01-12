import { readdir, stat } from 'node:fs/promises';
import { join, basename } from 'node:path';

import type { Run } from './types';

/**
 * Extended run details beyond basic Run interface
 */
export interface RunDetails {
  id: string;
  path: string;
  epic?: string;
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
 * - YYYY-MM-DD-NNN format (e.g., 2024-01-15-001 < 2024-01-15-002)
 * - YYYY-MM-DD-HH-MM-SS-NNN format
 * Zero-padded segments ensure correct ordering.
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

  const content = await file.text();
  // Check for COMPLETE marker
  if (content.includes('promise=COMPLETE') || content.includes('<promise>COMPLETE</promise>')) {
    return false;
  }

  return true;
}

/**
 * Get current iteration number by counting iter-*.log files
 */
async function getIterationCount(runPath: string): Promise<number> {
  try {
    const entries = await readdir(runPath);
    const iterLogs = entries.filter((e) => e.startsWith('iter-') && e.endsWith('.log'));
    return iterLogs.length;
  } catch {
    return 0;
  }
}

/**
 * Get epic ID from run if recorded
 */
async function getRunEpic(runPath: string): Promise<string | undefined> {
  // Check attempts.json for epic info
  const attemptsPath = join(runPath, 'attempts.json');
  const attemptsFile = Bun.file(attemptsPath);

  if (await attemptsFile.exists()) {
    try {
      const attempts = await attemptsFile.json();
      if (Array.isArray(attempts) && attempts.length > 0) {
        // Get epic from most recent attempt
        const lastAttempt = attempts[attempts.length - 1];
        if (lastAttempt?.epic) {
          return lastAttempt.epic;
        }
      }
    } catch {
      // Ignore parse errors
    }
  }

  // Check branches.json for epic info
  const branchesPath = join(runPath, 'branches.json');
  const branchesFile = Bun.file(branchesPath);

  if (await branchesFile.exists()) {
    try {
      const branches = await branchesFile.json();
      if (branches?.epic) {
        return branches.epic;
      }
    } catch {
      // Ignore parse errors
    }
  }

  return undefined;
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
 * @param runsDir Path to runs directory (defaults to scripts/ralph/runs relative to cwd)
 * @returns Array of Run objects sorted by date (newest first)
 */
export async function discoverRuns(runsDir?: string): Promise<Run[]> {
  const dir = runsDir ?? join(process.cwd(), DEFAULT_RUNS_DIR);

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

  // Build Run objects
  const runs: Run[] = [];
  for (const runId of runDirs) {
    const runPath = join(dir, runId);
    const [active, iteration, epic, startedAt] = await Promise.all([
      isRunActive(runPath),
      getIterationCount(runPath),
      getRunEpic(runPath),
      getRunStartTime(runPath),
    ]);

    runs.push({
      id: runId,
      path: runPath,
      epic,
      active,
      iteration,
      startedAt,
    });
  }

  // Sort by run ID (lexicographic descending = newest first)
  runs.sort((a, b) => compareRunIds(a.id, b.id));

  return runs;
}

/**
 * Get the latest (most recent) run by ID.
 * Computes the latest run regardless of input array order.
 */
export function getLatestRun(runs: Run[]): Run | undefined {
  if (runs.length === 0) return undefined;
  return runs.reduce((latest, run) =>
    compareRunIds(run.id, latest.id) < 0 ? run : latest
  );
}

/**
 * Get detailed information about a run
 */
export async function getRunDetails(runPath: string): Promise<RunDetails> {
  const id = basename(runPath);
  const [active, iteration, epic, startedAt] = await Promise.all([
    isRunActive(runPath),
    getIterationCount(runPath),
    getRunEpic(runPath),
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
    epic,
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
 */
export async function getReceiptStatus(
  runPath: string,
  taskId: string
): Promise<ReceiptStatus> {
  const receiptsDir = join(runPath, 'receipts');

  // Normalize task ID for filename (fn-1.2 -> fn-1.2)
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
 */
export async function getBlockReason(
  taskId: string,
  runPath?: string
): Promise<string | null> {
  // Check .flow/blocks first
  const flowBlockPath = join(process.cwd(), '.flow', 'blocks', `block-${taskId}.md`);
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
 * Validate a run ID and return the run if found
 * @throws Error with helpful message if run not found
 * @returns Run with any warnings (e.g., corrupt run)
 */
export async function validateRun(
  runId: string,
  runsDir?: string
): Promise<ValidateRunResult> {
  const runs = await discoverRuns(runsDir);
  const run = runs.find((r) => r.id === runId);

  if (!run) {
    const available = runs.map((r) => r.id).join(', ') || 'none';
    throw new Error(`Run '${runId}' not found. Available: ${available}`);
  }

  const warnings: string[] = [];

  // Check if corrupt (missing progress.txt)
  const progressPath = join(run.path, 'progress.txt');
  if (!(await fileExists(progressPath))) {
    warnings.push(`Run '${runId}' may be corrupt (missing progress.txt)`);
  }

  return { run, warnings };
}
