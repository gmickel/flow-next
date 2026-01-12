import { describe, expect, test } from "bun:test";
import type {
	Epic,
	EpicTask,
	ReadyResponse,
	Task,
	TaskEvidence,
	TaskListItem,
	TaskStatus,
	TaskSummary,
	TasksResponse,
} from "../src/lib/types";

import epicFixture from "./fixtures/epic.json";
import readyFixture from "./fixtures/ready.json";
import taskFixture from "./fixtures/task.json";
import tasksFixture from "./fixtures/tasks.json";

// Type guard for TaskStatus
function isTaskStatus(s: string): s is TaskStatus {
	return ["todo", "in_progress", "done", "blocked"].includes(s);
}

describe("types match flowctl JSON output", () => {
	test("Epic type matches epic.json fixture", () => {
		// Validate fixture has expected shape
		expect(epicFixture.success).toBe(true);
		expect(typeof epicFixture.id).toBe("string");
		expect(typeof epicFixture.title).toBe("string");
		expect(epicFixture.status).toBe("open");
		expect(typeof epicFixture.branch_name).toBe("string");
		expect(Array.isArray(epicFixture.tasks)).toBe(true);
		expect(epicFixture.tasks.length).toBeGreaterThan(0);

		// Validate task structure within epic
		const firstTask = epicFixture.tasks[0]!;
		expect(firstTask.id).toBe("fn-9.1");
		expect(firstTask.status).toBe("done");
		expect(Array.isArray(firstTask.depends_on)).toBe(true);

		// Validate status is valid
		expect(epicFixture.status === "open" || epicFixture.status === "done").toBe(true);

		// Type construction (compile-time check)
		const epicStatus = epicFixture.status as "open" | "done";
		const _epic: Epic = {
			id: epicFixture.id,
			title: epicFixture.title,
			status: epicStatus,
			branch_name: epicFixture.branch_name,
			spec_path: epicFixture.spec_path,
			next_task: epicFixture.next_task,
			depends_on_epics: epicFixture.depends_on_epics,
			plan_review_status: epicFixture.plan_review_status as
				| "ship"
				| "needs_work"
				| "major_rethink"
				| null,
			plan_reviewed_at: epicFixture.plan_reviewed_at,
			created_at: epicFixture.created_at,
			updated_at: epicFixture.updated_at,
			tasks: epicFixture.tasks.map((t): EpicTask => {
				expect(isTaskStatus(t.status)).toBe(true);
				return {
					id: t.id,
					title: t.title,
					status: t.status as TaskStatus,
					priority: t.priority,
					depends_on: t.depends_on,
				};
			}),
		};
		expect(_epic.id).toBe("fn-9");
	});

	test("Task type matches task.json fixture", () => {
		// Validate fixture has expected shape
		expect(taskFixture.success).toBe(true);
		expect(taskFixture.id).toBe("fn-9.1");
		expect(taskFixture.epic).toBe("fn-9");
		expect(taskFixture.status).toBe("done");
		expect(isTaskStatus(taskFixture.status)).toBe(true);
		// assignee can be string or null for unclaimed tasks
		expect(
			taskFixture.assignee === null || typeof taskFixture.assignee === "string",
		).toBe(true);
		expect(Array.isArray(taskFixture.depends_on)).toBe(true);

		// Validate evidence structure
		expect(taskFixture.evidence).toBeDefined();
		expect(Array.isArray(taskFixture.evidence.commits)).toBe(true);
		expect(taskFixture.evidence.commits).toContain(
			"24cde68050ac454581829a297fcbf83c0d8005f4",
		);

		// Type construction (compile-time check)
		const evidence: TaskEvidence = {
			commits: taskFixture.evidence.commits,
			tests: taskFixture.evidence.tests,
			prs: taskFixture.evidence.prs,
		};
		const _task: Task = {
			id: taskFixture.id,
			epic: taskFixture.epic,
			title: taskFixture.title,
			status: taskFixture.status as TaskStatus,
			depends_on: taskFixture.depends_on,
			spec_path: taskFixture.spec_path,
			priority: taskFixture.priority,
			assignee: taskFixture.assignee,
			claim_note: taskFixture.claim_note,
			claimed_at: taskFixture.claimed_at,
			created_at: taskFixture.created_at,
			updated_at: taskFixture.updated_at,
			evidence,
		};
		expect(_task.status).toBe("done");
	});

	test("TasksResponse type matches tasks.json fixture", () => {
		// Validate fixture has expected shape
		expect(tasksFixture.success).toBe(true);
		expect(typeof tasksFixture.count).toBe("number");
		expect(Array.isArray(tasksFixture.tasks)).toBe(true);
		expect(tasksFixture.tasks.length).toBe(tasksFixture.count);
		expect(tasksFixture.tasks.length).toBeGreaterThan(0);

		// Validate task list item structure
		const firstTask = tasksFixture.tasks[0]!;
		expect(firstTask.id).toBe("fn-9.1");
		expect(firstTask.epic).toBe("fn-9");
		expect(firstTask.status).toBe("done");
		expect(isTaskStatus(firstTask.status)).toBe(true);
		expect(Array.isArray(firstTask.depends_on)).toBe(true);

		// Type construction
		const _response: TasksResponse = {
			success: tasksFixture.success,
			count: tasksFixture.count,
			tasks: tasksFixture.tasks.map((t): TaskListItem => {
				expect(isTaskStatus(t.status)).toBe(true);
				return {
					id: t.id,
					epic: t.epic,
					title: t.title,
					status: t.status as TaskStatus,
					priority: t.priority,
					depends_on: t.depends_on,
				};
			}),
		};
		expect(_response.count).toBe(3);
	});

	test("ReadyResponse type matches ready.json fixture", () => {
		// Validate fixture has expected shape
		expect(readyFixture.success).toBe(true);
		expect(readyFixture.epic).toBe("fn-9");
		expect(typeof readyFixture.actor).toBe("string");
		expect(Array.isArray(readyFixture.ready)).toBe(true);
		expect(Array.isArray(readyFixture.in_progress)).toBe(true);
		expect(Array.isArray(readyFixture.blocked)).toBe(true);
		expect(readyFixture.ready.length).toBeGreaterThan(0);
		expect(readyFixture.blocked.length).toBeGreaterThan(0);

		// Validate TaskSummary structure
		const readyTask = readyFixture.ready[0]!;
		expect(readyTask.id).toBe("fn-9.2");
		expect(readyTask.depends_on).toContain("fn-9.1");

		const blockedTask = readyFixture.blocked[0]!;
		expect(blockedTask.blocked_by).toContain("fn-9.3");

		// Type construction
		const _ready: ReadyResponse = {
			success: readyFixture.success,
			epic: readyFixture.epic,
			actor: readyFixture.actor,
			ready: readyFixture.ready.map(
				(t): TaskSummary => ({
					id: t.id,
					title: t.title,
					depends_on: t.depends_on,
				}),
			),
			in_progress: readyFixture.in_progress.map(
				(t): TaskSummary => ({
					id: t.id,
					title: t.title,
					assignee: t.assignee,
				}),
			),
			blocked: readyFixture.blocked.map(
				(t): TaskSummary => ({
					id: t.id,
					title: t.title,
					blocked_by: t.blocked_by,
				}),
			),
		};
		expect(_ready.ready.length).toBeGreaterThan(0);
	});
});
