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
  stderr: string;
  /** Error kind: "exec" for process failure, "parse" for JSON parse failure */
  kind: 'exec' | 'parse';

  constructor(
    fullCommand: string[],
    args: string[],
    exitCode: number,
    stderr: string,
    kind: 'exec' | 'parse' = 'exec'
  ) {
    const msg = `flowctl ${args.join(' ')} failed (exit ${exitCode}): ${stderr}`;
    super(msg);
    this.name = 'FlowctlError';
    this.fullCommand = fullCommand;
    this.args = args;
    this.exitCode = exitCode;
    this.stderr = stderr;
    this.kind = kind;
  }
}

/** Atomic cache for flowctl path and invocation method */
interface FlowctlCache {
  path: string;
  usePython: boolean;
}

let cache: FlowctlCache | null = null;

/**
 * Check if a file exists and is executable
 * Uses `flowctl --help` as test command (repo-independent, always exits 0)
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
    return proc.exitCode === 0;
  } catch {
    return false;
  }
}

/**
 * Check if flowctl works via python3
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
    return proc.exitCode === 0;
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
    const msg = `flowctl not found. Run \`/flow-next:setup\` or ensure flow-next plugin is installed. Searched: ${searchedPaths.slice(0, 4).join(', ')}`;
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
async function spawnFlowctl(
  args: string[]
): Promise<{
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

  const proc = Bun.spawn(cmd, {
    stdout: 'pipe',
    stderr: 'pipe',
    cwd: process.cwd(),
  });

  const [stdout, stderr] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
  ]);

  await proc.exited;

  return { cmd, stdout, stderr, exitCode: proc.exitCode ?? 1 };
}

/**
 * Run flowctl command and parse JSON output
 */
export async function flowctl<T>(args: string[]): Promise<T> {
  const { cmd, stdout, stderr, exitCode } = await spawnFlowctl(args);

  if (exitCode !== 0) {
    throw new FlowctlError(cmd, args, exitCode, stderr.trim(), 'exec');
  }

  try {
    return JSON.parse(stdout) as T;
  } catch {
    // Include both stdout and stderr for debugging parse failures
    // Use real exitCode (could be non-zero with junk stdout)
    const context = stderr.trim()
      ? `stderr: ${stderr.trim()}, stdout: ${stdout.slice(0, 150)}`
      : `stdout: ${stdout.slice(0, 200)}`;
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
 * Get all epics (list items with counts)
 */
export async function getEpics(): Promise<EpicListItem[]> {
  const response = await flowctl<EpicsResponse>(['epics', '--json']);
  return response.epics;
}

/**
 * Get tasks for an epic
 */
export async function getTasks(epicId: string): Promise<TaskListItem[]> {
  const response = await flowctl<TasksResponse>([
    'tasks',
    '--epic',
    epicId,
    '--json',
  ]);
  return response.tasks;
}

/**
 * Get task spec (markdown content)
 */
export async function getTaskSpec(taskId: string): Promise<string> {
  const args = ['cat', taskId];
  const { cmd, stdout, stderr, exitCode } = await spawnFlowctl(args);

  if (exitCode !== 0) {
    throw new FlowctlError(cmd, args, exitCode, stderr.trim(), 'exec');
  }

  return stdout;
}

/**
 * Get ready/in_progress/blocked tasks for an epic
 */
export async function getReadyTasks(epicId: string): Promise<ReadyResponse> {
  return flowctl<ReadyResponse>(['ready', '--epic', epicId, '--json']);
}

/**
 * Get epic details
 */
export async function getEpic(epicId: string): Promise<Epic> {
  const response = await flowctl<EpicShowResponse>(['show', epicId, '--json']);
  const { success: _, ...epic } = response;
  return epic as Epic;
}

/**
 * Get task details
 */
export async function getTask(taskId: string): Promise<Task> {
  const response = await flowctl<TaskShowResponse>(['show', taskId, '--json']);
  const { success: _, ...task } = response;
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
