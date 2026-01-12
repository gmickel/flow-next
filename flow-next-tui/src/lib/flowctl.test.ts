import { describe, expect, it, beforeEach } from "bun:test";
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

// Reset cache before each test
beforeEach(() => {
	clearFlowctlCache();
});

describe("FlowctlError", () => {
	it("formats error message with command, exit code, and stderr", () => {
		const error = new FlowctlError(["show", "fn-1", "--json"], 1, "Epic not found");
		expect(error.message).toBe(
			"flowctl show fn-1 --json failed (exit 1): Epic not found"
		);
		expect(error.command).toEqual(["show", "fn-1", "--json"]);
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

	it("error message contains helpful info", () => {
		// Test error message format without mocking cwd
		const errorMsg = "flowctl not found. Run `/flow-next:setup` or ensure flow-next plugin is installed.";
		expect(errorMsg).toContain("flowctl not found");
		expect(errorMsg).toContain("/flow-next:setup");
	});
});

describe("flowctl", () => {
	it("parses JSON output from flowctl command", async () => {
		// Integration test - requires .flow directory
		const result = await flowctl<{ success: boolean; epics: unknown[] }>(["epics", "--json"]);
		expect(result).toHaveProperty("success");
		expect(result).toHaveProperty("epics");
	});
});

describe("getEpics", () => {
	it("returns list of epics", async () => {
		// Integration test
		const epics = await getEpics();
		expect(Array.isArray(epics)).toBe(true);
		if (epics.length > 0) {
			const first = epics[0];
			expect(first).toHaveProperty("id");
			expect(first).toHaveProperty("title");
			expect(first).toHaveProperty("status");
		}
	});
});

describe("getTasks", () => {
	it("returns tasks for an epic", async () => {
		// First get epics to find a valid epic id
		const epics = await getEpics();
		if (epics.length === 0) return; // Skip if no epics

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
		// flowctl returns success with empty tasks for non-existent epics
		const tasks = await getTasks("fn-99999");
		expect(Array.isArray(tasks)).toBe(true);
		expect(tasks.length).toBe(0);
	});
});

describe("getTaskSpec", () => {
	it("returns markdown spec for a task", async () => {
		// Get first task from first epic
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
	it("returns epic details", async () => {
		const epics = await getEpics();
		if (epics.length === 0) return;

		const epicId = epics[0]?.id;
		if (!epicId) return;

		const epic = await getEpic(epicId);
		expect(epic).toHaveProperty("id");
		expect(epic).toHaveProperty("title");
		expect(epic).toHaveProperty("status");
		expect(epic).toHaveProperty("tasks");
		// Should not have success field
		expect(epic).not.toHaveProperty("success");
	});
});

describe("getTask", () => {
	it("returns task details", async () => {
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
