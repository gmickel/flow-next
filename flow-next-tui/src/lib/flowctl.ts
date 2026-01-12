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
} from "./types";

/**
 * Error thrown when flowctl command fails
 */
export class FlowctlError extends Error {
	command: string[];
	exitCode: number;
	stderr: string;

	constructor(command: string[], exitCode: number, stderr: string) {
		const msg = `flowctl ${command.join(" ")} failed (exit ${exitCode}): ${stderr}`;
		super(msg);
		this.name = "FlowctlError";
		this.command = command;
		this.exitCode = exitCode;
		this.stderr = stderr;
	}
}

// Cached flowctl path and invocation method
let cachedFlowctlPath: string | null = null;
let usePython: boolean | null = null;

/**
 * Check if a file exists and is executable
 * Uses `flowctl --help` as test command (repo-independent, always exits 0)
 */
async function canExecute(path: string): Promise<boolean> {
	const file = Bun.file(path);
	if (!(await file.exists())) return false;

	// Try direct execution with --help (repo-independent)
	try {
		const proc = Bun.spawn([path, "--help"], {
			stdout: "pipe",
			stderr: "pipe",
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
		const proc = Bun.spawn(["python3", path, "--help"], {
			stdout: "pipe",
			stderr: "pipe",
		});
		await proc.exited;
		return proc.exitCode === 0;
	} catch {
		return false;
	}
}

/**
 * Check if a command exists on PATH
 */
async function commandExists(cmd: string): Promise<string | null> {
	try {
		const proc = Bun.spawn(["which", cmd], {
			stdout: "pipe",
			stderr: "pipe",
		});
		const stdout = await new Response(proc.stdout).text();
		await proc.exited;
		if (proc.exitCode === 0) {
			return stdout.trim();
		}
	} catch {
		// ignore
	}
	return null;
}

/**
 * Try flowctl at a given path, returning true if it works
 * Sets usePython based on which invocation method works
 */
async function tryFlowctl(path: string): Promise<boolean> {
	if (await canExecute(path)) {
		usePython = false;
		return true;
	}
	if (await canExecuteViaPython(path)) {
		usePython = true;
		return true;
	}
	return false;
}

/**
 * Find repo root by looking for .git directory
 * Note: Bun.file().exists() doesn't work for directories, so we check .git/HEAD
 */
async function findRepoRoot(startDir: string): Promise<string | null> {
	let dir = startDir;
	const root = "/";
	while (dir !== root) {
		// Check for .git/HEAD file (works for both regular repos and worktrees)
		const gitHeadPath = `${dir}/.git/HEAD`;
		const gitHeadFile = Bun.file(gitHeadPath);
		if (await gitHeadFile.exists()) {
			return dir;
		}
		// Also check for .git file (for worktrees, it's a file containing path)
		const gitFilePath = `${dir}/.git`;
		const gitFile = Bun.file(gitFilePath);
		if (await gitFile.exists()) {
			const content = await gitFile.text();
			// If it's a worktree, the file contains "gitdir: /path/to/git"
			if (content.startsWith("gitdir:")) {
				return dir;
			}
		}
		dir = dir.substring(0, dir.lastIndexOf("/")) || root;
	}
	return null;
}

/**
 * Find flowctl path
 * Search order:
 * 1. .flow/bin/flowctl (installed via /flow-next:setup)
 * 2. ./plugins/flow-next/scripts/flowctl (repo-local plugin checkout)
 * 3. Search up to repo root for plugins/flow-next/scripts/flowctl
 * 4. flowctl or flowctl.py on PATH
 * 5. Error with helpful message
 */
export async function getFlowctlPath(): Promise<string> {
	if (cachedFlowctlPath) return cachedFlowctlPath;

	const cwd = process.cwd();

	// 1. .flow/bin/flowctl
	const flowBinPath = `${cwd}/.flow/bin/flowctl`;
	if (await tryFlowctl(flowBinPath)) {
		cachedFlowctlPath = flowBinPath;
		return flowBinPath;
	}

	// 2. ./plugins/flow-next/scripts/flowctl (from cwd)
	const pluginPath = `${cwd}/plugins/flow-next/scripts/flowctl`;
	if (await tryFlowctl(pluginPath)) {
		cachedFlowctlPath = pluginPath;
		return pluginPath;
	}

	// 3. Search up to repo root
	const repoRoot = await findRepoRoot(cwd);
	if (repoRoot && repoRoot !== cwd) {
		// Try .flow/bin at repo root
		const repoFlowBin = `${repoRoot}/.flow/bin/flowctl`;
		if (await tryFlowctl(repoFlowBin)) {
			cachedFlowctlPath = repoFlowBin;
			return repoFlowBin;
		}

		// Try plugins dir at repo root
		const repoPluginPath = `${repoRoot}/plugins/flow-next/scripts/flowctl`;
		if (await tryFlowctl(repoPluginPath)) {
			cachedFlowctlPath = repoPluginPath;
			return repoPluginPath;
		}
	}

	// 4. flowctl on PATH
	const flowctlOnPath = await commandExists("flowctl");
	if (flowctlOnPath && (await tryFlowctl(flowctlOnPath))) {
		cachedFlowctlPath = flowctlOnPath;
		return flowctlOnPath;
	}

	// 4b. flowctl.py on PATH
	const flowctlPyOnPath = await commandExists("flowctl.py");
	if (flowctlPyOnPath && (await tryFlowctl(flowctlPyOnPath))) {
		cachedFlowctlPath = flowctlPyOnPath;
		return flowctlPyOnPath;
	}

	// 5. Error
	throw new Error(
		"flowctl not found. Run `/flow-next:setup` or ensure flow-next plugin is installed.",
	);
}

/**
 * Run flowctl command and parse JSON output
 */
export async function flowctl<T>(args: string[]): Promise<T> {
	const flowctlPath = await getFlowctlPath();

	const cmd = usePython
		? ["python3", flowctlPath, ...args]
		: [flowctlPath, ...args];

	const proc = Bun.spawn(cmd, {
		stdout: "pipe",
		stderr: "pipe",
		cwd: process.cwd(),
	});

	const [stdout, stderr] = await Promise.all([
		new Response(proc.stdout).text(),
		new Response(proc.stderr).text(),
	]);

	await proc.exited;

	if (proc.exitCode !== 0) {
		throw new FlowctlError(args, proc.exitCode ?? 1, stderr.trim());
	}

	try {
		return JSON.parse(stdout) as T;
	} catch {
		// Include both stdout and stderr for debugging parse failures
		const context = stderr.trim()
			? `stderr: ${stderr.trim()}, stdout: ${stdout.slice(0, 150)}`
			: `stdout: ${stdout.slice(0, 200)}`;
		throw new FlowctlError(args, 0, `Failed to parse JSON: ${context}`);
	}
}

/**
 * Get all epics (list items with counts)
 */
export async function getEpics(): Promise<EpicListItem[]> {
	const response = await flowctl<EpicsResponse>(["epics", "--json"]);
	return response.epics;
}

/**
 * Get tasks for an epic
 */
export async function getTasks(epicId: string): Promise<TaskListItem[]> {
	const response = await flowctl<TasksResponse>([
		"tasks",
		"--epic",
		epicId,
		"--json",
	]);
	return response.tasks;
}

/**
 * Get task spec (markdown content)
 */
export async function getTaskSpec(taskId: string): Promise<string> {
	const flowctlPath = await getFlowctlPath();

	const cmd = usePython
		? ["python3", flowctlPath, "cat", taskId]
		: [flowctlPath, "cat", taskId];

	const proc = Bun.spawn(cmd, {
		stdout: "pipe",
		stderr: "pipe",
		cwd: process.cwd(),
	});

	const [stdout, stderr] = await Promise.all([
		new Response(proc.stdout).text(),
		new Response(proc.stderr).text(),
	]);

	await proc.exited;

	if (proc.exitCode !== 0) {
		throw new FlowctlError(["cat", taskId], proc.exitCode ?? 1, stderr.trim());
	}

	return stdout;
}

/**
 * Get ready/in_progress/blocked tasks for an epic
 */
export async function getReadyTasks(epicId: string): Promise<ReadyResponse> {
	return flowctl<ReadyResponse>(["ready", "--epic", epicId, "--json"]);
}

/**
 * Get epic details
 */
export async function getEpic(epicId: string): Promise<Epic> {
	const response = await flowctl<EpicShowResponse>([
		"show",
		epicId,
		"--json",
	]);
	// Strip success field from response
	const { success: _, ...epic } = response;
	return epic as Epic;
}

/**
 * Get task details
 */
export async function getTask(taskId: string): Promise<Task> {
	const response = await flowctl<TaskShowResponse>([
		"show",
		taskId,
		"--json",
	]);
	// Strip success field from response
	const { success: _, ...task } = response;
	return task as Task;
}

/**
 * Clear cached flowctl path (useful for testing)
 */
export function clearFlowctlCache(): void {
	cachedFlowctlPath = null;
	usePython = null;
}
