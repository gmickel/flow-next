import { dirname } from 'node:path';

import type {
  Epic,
  EpicListItem,
  EpicShowResponse,
  EpicsResponse,
  ReadyResponse,
  Task,
  TaskListItem,
  TaskShowResponse,
  TasksResponse,
} from './types';

/**
 * Error thrown when flowctl command fails
 */
export class FlowctlError extends Error {
  /** Full command executed (including python3, path) */
  fullCommand: string[];
  /** Just the flowctl args (for easier inspection) */
  args: string[];
  exitCode: number;
  /** Error output/context (may be stderr, stdout, or descriptive message) */
  output: string;
  /** Error kind: "exec" for process failure, "parse" for JSON parse failure, "api" for success:false */
  kind: 'exec' | 'parse' | 'api';

  constructor(
    fullCommand: string[],
    args: string[],
    exitCode: number,
    output: string,
    kind: 'exec' | 'parse' | 'api' = 'exec'
  ) {
    const msg = `flowctl ${args.join(' ')} failed (exit ${exitCode}): ${output}`;
    super(msg);
    this.name = 'FlowctlError';
    this.fullCommand = fullCommand;
    this.args = args;
    this.exitCode = exitCode;
    this.output = output;
    this.kind = kind;
  }
}

/**
 * Atomic cache for flowctl path and invocation method.
 * Note: This assumes single-repo usage per process. The first successful
 * path resolution is cached for all subsequent calls, even if different
 * startDir values are passed. This is intentional for TUI usage.
 */
interface FlowctlCache {
  path: string;
  usePython: boolean;
}

let cache: FlowctlCache | null = null;

/**
 * Check if a file exists and is executable
 * Uses `flowctl --help` as test command (repo-independent)
 * Spawn success = executable (any exit code ok; ENOENT/EACCES throws)
 */
async function canExecute(path: string): Promise<boolean> {
  const file = Bun.file(path);
  if (!(await file.exists())) return false;

  try {
    const proc = Bun.spawn([path, '--help'], {
      stdout: 'pipe',
      stderr: 'pipe',
    });
    await proc.exited;
    // Any exit code is fine - spawn success means executable
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if flowctl works via python3
 * Spawn success = executable (any exit code ok; ENOENT/EACCES throws)
 */
async function canExecuteViaPython(path: string): Promise<boolean> {
  const file = Bun.file(path);
  if (!(await file.exists())) return false;

  try {
    const proc = Bun.spawn(['python3', path, '--help'], {
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
 * Try flowctl at a given path, returning cache entry if it works
 */
async function tryFlowctl(path: string): Promise<FlowctlCache | null> {
  if (await canExecute(path)) {
    return { path, usePython: false };
  }
  if (await canExecuteViaPython(path)) {
    return { path, usePython: true };
  }
  return null;
}

/**
 * Find repo root by looking for .git directory
 * Note: Bun.file().exists() doesn't work for directories, so we check .git/HEAD
 */
async function findRepoRoot(startDir: string): Promise<string | null> {
  let dir = startDir;
  while (dir !== dirname(dir)) {
    const gitHeadPath = `${dir}/.git/HEAD`;
    const gitHeadFile = Bun.file(gitHeadPath);
    if (await gitHeadFile.exists()) {
      return dir;
    }
    // Also check for .git file (for worktrees)
    const gitFilePath = `${dir}/.git`;
    const gitFile = Bun.file(gitFilePath);
    if (await gitFile.exists()) {
      const content = await gitFile.text();
      if (content.startsWith('gitdir:')) {
        return dir;
      }
    }
    dir = dirname(dir);
  }
  return null;
}

/**
 * Error thrown when flowctl path cannot be found
 */
export class FlowctlNotFoundError extends Error {
  /** Paths that were searched */
  searchedPaths: string[];
  /** Starting directory for search */
  startDir: string;

  constructor(startDir: string, searchedPaths: string[]) {
    const pathList = searchedPaths.join(', ');
    const msg = `flowctl not found. Run \`/flow-next:setup\` or ensure flow-next plugin is installed. Searched: ${pathList}`;
    super(msg);
    this.name = 'FlowctlNotFoundError';
    this.startDir = startDir;
    this.searchedPaths = searchedPaths;
  }
}

/**
 * Find flowctl path
 * Search order:
 * 1. .flow/bin/flowctl (installed via /flow-next:setup)
 * 2. ./plugins/flow-next/scripts/flowctl (repo-local plugin checkout)
 * 3. Search up to repo root for plugins/flow-next/scripts/flowctl
 * 4. flowctl or flowctl.py on PATH (via Bun.which)
 * 5. Error with helpful message
 *
 * @param startDir Optional starting directory (defaults to process.cwd(), for testing)
 */
export async function getFlowctlPath(startDir?: string): Promise<string> {
  if (cache) return cache.path;

  const cwd = startDir ?? process.cwd();
  const searchedPaths: string[] = [];

  // 1. .flow/bin/flowctl
  const flowBinPath = `${cwd}/.flow/bin/flowctl`;
  searchedPaths.push(flowBinPath);
  let result = await tryFlowctl(flowBinPath);
  if (result) {
    cache = result;
    return result.path;
  }

  // 2. ./plugins/flow-next/scripts/flowctl (from cwd)
  const pluginPath = `${cwd}/plugins/flow-next/scripts/flowctl`;
  searchedPaths.push(pluginPath);
  result = await tryFlowctl(pluginPath);
  if (result) {
    cache = result;
    return result.path;
  }

  // 3. Search up to repo root
  const repoRoot = await findRepoRoot(cwd);
  if (repoRoot && repoRoot !== cwd) {
    const repoFlowBin = `${repoRoot}/.flow/bin/flowctl`;
    searchedPaths.push(repoFlowBin);
    result = await tryFlowctl(repoFlowBin);
    if (result) {
      cache = result;
      return result.path;
    }

    const repoPluginPath = `${repoRoot}/plugins/flow-next/scripts/flowctl`;
    searchedPaths.push(repoPluginPath);
    result = await tryFlowctl(repoPluginPath);
    if (result) {
      cache = result;
      return result.path;
    }
  }

  // 4. flowctl on PATH (use Bun.which instead of shelling out)
  const flowctlOnPath = Bun.which('flowctl');
  if (flowctlOnPath) {
    searchedPaths.push(flowctlOnPath);
    result = await tryFlowctl(flowctlOnPath);
    if (result) {
      cache = result;
      return result.path;
    }
  }

  // 4b. flowctl.py on PATH
  const flowctlPyOnPath = Bun.which('flowctl.py');
  if (flowctlPyOnPath) {
    searchedPaths.push(flowctlPyOnPath);
    result = await tryFlowctl(flowctlPyOnPath);
    if (result) {
      cache = result;
      return result.path;
    }
  }

  // 5. Error with context
  throw new FlowctlNotFoundError(cwd, searchedPaths);
}

/**
 * Spawn flowctl and return stdout/stderr
 * Shared helper for flowctl() and getTaskSpec()
 */
async function spawnFlowctl(args: string[]): Promise<{
  cmd: string[];
  stdout: string;
  stderr: string;
  exitCode: number;
}> {
  const flowctlPath = await getFlowctlPath();
  // cache is guaranteed to be set after getFlowctlPath succeeds
  const usePython = cache?.usePython ?? false;

  const cmd = usePython
    ? ['python3', flowctlPath, ...args]
    : [flowctlPath, ...args];

  try {
    const proc = Bun.spawn(cmd, {
      stdout: 'pipe',
      stderr: 'pipe',
    });

    const [stdout, stderr] = await Promise.all([
      new Response(proc.stdout).text(),
      new Response(proc.stderr).text(),
    ]);

    await proc.exited;

    return { cmd, stdout, stderr, exitCode: proc.exitCode ?? 1 };
  } catch (err) {
    // Wrap spawn failures (ENOENT, EACCES, etc) in FlowctlError
    throw new FlowctlError(cmd, args, -1, String(err), 'exec');
  }
}

/**
 * Run flowctl command and parse JSON output
 */
export async function flowctl<T>(args: string[]): Promise<T> {
  const { result } = await flowctlWithCmd<T>(args);
  return result;
}

/**
 * Run flowctl command and parse JSON output, returning cmd for error context
 */
async function flowctlWithCmd<T>(
  args: string[]
): Promise<{ result: T; cmd: string[] }> {
  const { cmd, stdout, stderr, exitCode } = await spawnFlowctl(args);

  if (exitCode !== 0) {
    // Include stdout when stderr empty (some failures emit useful info on stdout)
    const errorContext = stderr.trim()
      ? stderr.trim()
      : stdout.trim().slice(0, 200) || 'no output';
    throw new FlowctlError(cmd, args, exitCode, errorContext, 'exec');
  }

  try {
    return { result: JSON.parse(stdout) as T, cmd };
  } catch {
    // Include both streams labeled consistently for debugging
    const stdoutSnip = stdout.trim().slice(0, 150);
    const stderrSnip = stderr.trim().slice(0, 150);
    const context = `stdout=${stdoutSnip || '(empty)'}, stderr=${stderrSnip || '(empty)'}`;
    throw new FlowctlError(
      cmd,
      args,
      exitCode,
      `Failed to parse JSON: ${context}`,
      'parse'
    );
  }
}

/**
 * Validate response has success:true, throw FlowctlError if not
 * Includes error field from response if present
 */
function assertSuccess<T extends { success: boolean; error?: string }>(
  response: T,
  cmd: string[],
  args: string[]
): asserts response is T & { success: true } {
  if (response.success !== true) {
    const errorMsg = response.error
      ? `flowctl returned success:false: ${response.error}`
      : 'flowctl returned success:false';
    throw new FlowctlError(cmd, args, 0, errorMsg, 'api');
  }
}

/**
 * Get all epics (list items with counts)
 */
export async function getEpics(): Promise<EpicListItem[]> {
  const args = ['epics', '--json'];
  const { result, cmd } = await flowctlWithCmd<EpicsResponse>(args);
  assertSuccess(result, cmd, args);
  return result.epics;
}

/**
 * Get tasks for an epic
 */
export async function getTasks(epicId: string): Promise<TaskListItem[]> {
  const args = ['tasks', '--epic', epicId, '--json'];
  const { result, cmd } = await flowctlWithCmd<TasksResponse>(args);
  assertSuccess(result, cmd, args);
  return result.tasks;
}

/**
 * Get task spec (markdown content)
 */
export async function getTaskSpec(taskId: string): Promise<string> {
  const args = ['cat', taskId];
  const { cmd, stdout, stderr, exitCode } = await spawnFlowctl(args);

  if (exitCode !== 0) {
    const errorContext = stderr.trim()
      ? stderr.trim()
      : stdout.trim().slice(0, 200) || 'no output';
    throw new FlowctlError(cmd, args, exitCode, errorContext, 'exec');
  }

  return stdout;
}

/**
 * Get ready/in_progress/blocked tasks for an epic
 */
export async function getReadyTasks(epicId: string): Promise<ReadyResponse> {
  const args = ['ready', '--epic', epicId, '--json'];
  const { result, cmd } = await flowctlWithCmd<ReadyResponse>(args);
  assertSuccess(result, cmd, args);
  return result;
}

/**
 * Get epic details
 */
export async function getEpic(epicId: string): Promise<Epic> {
  const args = ['show', epicId, '--json'];
  const { result, cmd } = await flowctlWithCmd<EpicShowResponse>(args);
  assertSuccess(result, cmd, args);
  const { success: _, ...epic } = result;
  return epic as Epic;
}

/**
 * Get task details
 */
export async function getTask(taskId: string): Promise<Task> {
  const args = ['show', taskId, '--json'];
  const { result, cmd } = await flowctlWithCmd<TaskShowResponse>(args);
  assertSuccess(result, cmd, args);
  const { success: _, ...task } = result;
  return task as Task;
}

/**
 * Clear cached flowctl path (useful for testing)
 */
export function clearFlowctlCache(): void {
  cache = null;
}

/**
 * Check if flowctl is available (for test gating)
 */
export async function isFlowctlAvailable(): Promise<boolean> {
  try {
    await getFlowctlPath();
    return true;
  } catch {
    return false;
  }
}
