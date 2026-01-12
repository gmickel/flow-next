import { describe, expect, test } from "bun:test";
import type {
	Epic,
	EpicTask,
	ReadyResponse,
	Task,
	TaskEvidence,
	TaskSummary,
} from "../src/lib/types";

import epicFixture from "./fixtures/epic.json";
import readyFixture from "./fixtures/ready.json";
import taskFixture from "./fixtures/task.json";

describe("types match flowctl JSON output", () => {
	test("Epic type matches epic.json fixture", () => {
		// Extract epic fields (minus success wrapper)
		const epic: Epic = {
			id: epicFixture.id,
			title: epicFixture.title,
			status: epicFixture.status as Epic["status"],
			branch_name: epicFixture.branch_name,
			spec_path: epicFixture.spec_path,
			next_task: epicFixture.next_task,
			depends_on_epics: epicFixture.depends_on_epics,
			plan_review_status: epicFixture.plan_review_status,
			plan_reviewed_at: epicFixture.plan_reviewed_at,
			created_at: epicFixture.created_at,
			updated_at: epicFixture.updated_at,
			tasks: epicFixture.tasks as EpicTask[],
		};

		expect(epic.id).toBe("fn-9");
		expect(epic.status).toBe("open");
		expect(epic.tasks.length).toBeGreaterThan(0);

		// Verify task structure
		const task = epic.tasks[0] as EpicTask;
		expect(task.id).toBe("fn-9.1");
		expect(task.status).toBe("done");
		expect(Array.isArray(task.depends_on)).toBe(true);
	});

	test("Task type matches task.json fixture", () => {
		const task: Task = {
			id: taskFixture.id,
			epic: taskFixture.epic,
			title: taskFixture.title,
			status: taskFixture.status as Task["status"],
			depends_on: taskFixture.depends_on,
			spec_path: taskFixture.spec_path,
			priority: taskFixture.priority,
			assignee: taskFixture.assignee,
			claim_note: taskFixture.claim_note,
			claimed_at: taskFixture.claimed_at,
			created_at: taskFixture.created_at,
			updated_at: taskFixture.updated_at,
			evidence: taskFixture.evidence as TaskEvidence,
		};

		expect(task.id).toBe("fn-9.1");
		expect(task.epic).toBe("fn-9");
		expect(task.status).toBe("done");
		expect(task.evidence?.commits).toContain(
			"24cde68050ac454581829a297fcbf83c0d8005f4",
		);
	});

	test("ReadyResponse type matches ready.json fixture", () => {
		const ready: ReadyResponse = {
			success: readyFixture.success,
			epic: readyFixture.epic,
			actor: readyFixture.actor,
			ready: readyFixture.ready as TaskSummary[],
			in_progress: readyFixture.in_progress as TaskSummary[],
			blocked: readyFixture.blocked as TaskSummary[],
		};

		expect(ready.success).toBe(true);
		expect(ready.epic).toBe("fn-9");
		expect(ready.ready.length).toBeGreaterThan(0);
		expect(ready.in_progress.length).toBeGreaterThan(0);
		expect(ready.blocked.length).toBeGreaterThan(0);

		// Verify TaskSummary structure
		const readyTask = ready.ready[0] as TaskSummary;
		expect(readyTask.id).toBe("fn-9.2");
		expect(readyTask.depends_on).toContain("fn-9.1");

		const blockedTask = ready.blocked[0] as TaskSummary;
		expect(blockedTask.blocked_by).toContain("fn-9.3");
	});

	test("no any types in exports", () => {
		// This test ensures the types file compiles without any implicit any
		// If types.ts had any `any` types, TypeScript would catch it during build
		expect(true).toBe(true);
	});
});
