import { describe, expect, it, beforeEach, beforeAll } from "bun:test";
import {
	FlowctlError,
	getFlowctlPath,
	flowctl,
	getEpics,
	getTasks,
	getTaskSpec,
	getReadyTasks,
	getEpic,
	getTask,
	clearFlowctlCache,
} from "./flowctl";

// Check if .flow/ directory exists (for integration tests)
let hasFlowDir = false;
beforeAll(async () => {
	const file = Bun.file(`${process.cwd()}/.flow/config.json`);
	hasFlowDir = await file.exists();
	// Also check parent (for running from flow-next-tui subdir)
	if (!hasFlowDir) {
		const parentFile = Bun.file(`${process.cwd()}/../.flow/config.json`);
		hasFlowDir = await parentFile.exists();
	}
});

// Reset cache before each test
beforeEach(() => {
	clearFlowctlCache();
});

describe("FlowctlError", () => {
	it("formats error message with args, exit code, and stderr", () => {
		const fullCmd = ["python3", "/path/to/flowctl", "show", "fn-1", "--json"];
		const args = ["show", "fn-1", "--json"];
		const error = new FlowctlError(fullCmd, args, 1, "Epic not found");
		expect(error.message).toBe(
			"flowctl show fn-1 --json failed (exit 1): Epic not found"
		);
		expect(error.fullCommand).toEqual(fullCmd);
		expect(error.args).toEqual(args);
		expect(error.exitCode).toBe(1);
		expect(error.stderr).toBe("Epic not found");
		expect(error.name).toBe("FlowctlError");
	});
});

describe("getFlowctlPath", () => {
	// Integration test - requires flowctl to be available in the repo
	it("finds flowctl in repo plugins dir", async () => {
		// This test will work when run from the repo root
		const path = await getFlowctlPath();
		expect(path).toContain("flowctl");
	});

	it("caches the path after first lookup", async () => {
		const path1 = await getFlowctlPath();
		const path2 = await getFlowctlPath();
		expect(path1).toBe(path2);
	});

	it("error message contains helpful info when not found", async () => {
		// Capture original cwd value before mocking
		const originalCwdValue = process.cwd();
		// Point to a directory with no flowctl
		Object.defineProperty(process, "cwd", {
			value: () => "/tmp/nonexistent-flowctl-test-dir",
			configurable: true,
		});

		try {
			clearFlowctlCache();
			await getFlowctlPath();
			expect.unreachable("Should have thrown");
		} catch (err) {
			expect(err instanceof Error).toBe(true);
			expect((err as Error).message).toContain("flowctl not found");
			expect((err as Error).message).toContain("/flow-next:setup");
		} finally {
			Object.defineProperty(process, "cwd", {
				value: () => originalCwdValue,
				configurable: true,
			});
			clearFlowctlCache();
		}
	});
});

describe("flowctl", () => {
	it("parses JSON output from flowctl command", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const result = await flowctl<{ success: boolean; epics: unknown[] }>(["epics", "--json"]);
		expect(result).toHaveProperty("success");
		expect(result).toHaveProperty("epics");
	});
});

describe("getEpics", () => {
	it("returns list of epics with list-item fields", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const epics = await getEpics();
		expect(Array.isArray(epics)).toBe(true);
		if (epics.length > 0) {
			const first = epics[0];
			// EpicListItem fields
			expect(first).toHaveProperty("id");
			expect(first).toHaveProperty("title");
			expect(first).toHaveProperty("status");
			expect(first).toHaveProperty("tasks"); // count
			expect(first).toHaveProperty("done"); // count
			expect(typeof first?.tasks).toBe("number");
			expect(typeof first?.done).toBe("number");
		}
	});
});

describe("getTasks", () => {
	it("returns tasks for an epic", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const epics = await getEpics();
		if (epics.length === 0) return;

		const epicId = epics[0]?.id;
		if (!epicId) return;

		const tasks = await getTasks(epicId);
		expect(Array.isArray(tasks)).toBe(true);
		if (tasks.length > 0) {
			const first = tasks[0];
			expect(first).toHaveProperty("id");
			expect(first).toHaveProperty("title");
			expect(first).toHaveProperty("status");
			expect(first).toHaveProperty("epic");
		}
	});

	it("returns empty array for non-existent epic", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const tasks = await getTasks("fn-99999");
		expect(Array.isArray(tasks)).toBe(true);
		expect(tasks.length).toBe(0);
	});
});

describe("getTaskSpec", () => {
	it("returns markdown spec for a task", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const epics = await getEpics();
		if (epics.length === 0) return;

		const epicId = epics[0]?.id;
		if (!epicId) return;

		const tasks = await getTasks(epicId);
		if (tasks.length === 0) return;

		const taskId = tasks[0]?.id;
		if (!taskId) return;

		const spec = await getTaskSpec(taskId);
		expect(typeof spec).toBe("string");
		expect(spec.length).toBeGreaterThan(0);
	});

	it("throws FlowctlError for invalid task", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		try {
			await getTaskSpec("fn-99999.999");
			expect.unreachable("Should have thrown");
		} catch (error) {
			expect(error instanceof FlowctlError).toBe(true);
		}
	});
});

describe("getReadyTasks", () => {
	it("returns ready/in_progress/blocked categorization", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const epics = await getEpics();
		if (epics.length === 0) return;

		const epicId = epics[0]?.id;
		if (!epicId) return;

		const result = await getReadyTasks(epicId);
		expect(result).toHaveProperty("success");
		expect(result).toHaveProperty("ready");
		expect(result).toHaveProperty("in_progress");
		expect(result).toHaveProperty("blocked");
		expect(Array.isArray(result.ready)).toBe(true);
		expect(Array.isArray(result.in_progress)).toBe(true);
		expect(Array.isArray(result.blocked)).toBe(true);
	});
});

describe("getEpic", () => {
	it("returns full epic details", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const epics = await getEpics();
		if (epics.length === 0) return;

		const epicId = epics[0]?.id;
		if (!epicId) return;

		const epic = await getEpic(epicId);
		expect(epic).toHaveProperty("id");
		expect(epic).toHaveProperty("title");
		expect(epic).toHaveProperty("status");
		expect(epic).toHaveProperty("tasks"); // EpicTask[] for full epic
		// Should not have success field
		expect(epic).not.toHaveProperty("success");
	});
});

describe("getTask", () => {
	it("returns task details", async () => {
		if (!hasFlowDir) return; // Skip if no .flow/
		const epics = await getEpics();
		if (epics.length === 0) return;

		const epicId = epics[0]?.id;
		if (!epicId) return;

		const tasks = await getTasks(epicId);
		if (tasks.length === 0) return;

		const taskId = tasks[0]?.id;
		if (!taskId) return;

		const task = await getTask(taskId);
		expect(task).toHaveProperty("id");
		expect(task).toHaveProperty("title");
		expect(task).toHaveProperty("status");
		expect(task).toHaveProperty("epic");
		// Should not have success field
		expect(task).not.toHaveProperty("success");
	});
});
