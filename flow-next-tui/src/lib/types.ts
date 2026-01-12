// Task status types
export type TaskStatus = "todo" | "in_progress" | "done" | "blocked";

// Epic status types (matches flowctl EPIC_STATUS: ["open", "done"])
export type EpicStatus = "open" | "done";

// Run state (derived from progress.txt)
export type RunState = "running" | "complete" | "crashed";

// Log entry types for iter-*.log parsing
export type LogEntryType = "tool" | "response" | "error";

/**
 * Task as returned by flowctl show/tasks commands
 */
export interface Task {
	id: string; // fn-N.M
	epic: string; // fn-N
	title: string;
	status: TaskStatus;
	depends_on: string[];
	spec_path: string;
	priority: number | null;
	assignee: string | null;
	claim_note: string;
	claimed_at: string | null; // ISO timestamp
	created_at: string; // ISO timestamp
	updated_at: string; // ISO timestamp
	evidence?: TaskEvidence;
}

/**
 * Task evidence recorded on completion
 */
export interface TaskEvidence {
	commits: string[];
	tests: string[];
	prs: string[];
}

/**
 * Minimal task info in ready/blocked lists
 */
export interface TaskSummary {
	id: string;
	title: string;
	depends_on?: string[];
	blocked_by?: string[];
	assignee?: string;
}

/**
 * Task as embedded in Epic response (minimal fields)
 */
export interface EpicTask {
	id: string;
	title: string;
	status: TaskStatus;
	priority: number | null;
	depends_on: string[];
}

/**
 * Task as returned in flowctl tasks list (minimal fields)
 */
export interface TaskListItem {
	id: string;
	epic: string;
	title: string;
	status: TaskStatus;
	priority: number | null;
	depends_on: string[];
}

/**
 * Response from flowctl tasks command
 */
export interface TasksResponse {
	success: boolean;
	tasks: TaskListItem[];
	count: number;
}

/**
 * Epic as returned by flowctl show command
 */
export interface Epic {
	id: string; // fn-N
	title: string;
	status: EpicStatus;
	branch_name: string;
	spec_path: string;
	next_task: number;
	depends_on_epics: string[];
	plan_review_status: string | null;
	plan_reviewed_at: string | null; // ISO timestamp
	created_at: string; // ISO timestamp
	updated_at: string; // ISO timestamp
	tasks: EpicTask[];
}

/**
 * Ready response from flowctl ready command
 */
export interface ReadyResponse {
	success: boolean;
	epic: string;
	actor: string;
	ready: TaskSummary[];
	in_progress: TaskSummary[];
	blocked: TaskSummary[];
}

/**
 * Ralph run directory info
 */
export interface Run {
	id: string; // YYYY-MM-DD-NNN
	path: string; // full path to run dir
	epic?: string; // epic being worked on
	active: boolean; // derived from progress.txt
	iteration: number; // current iteration number
	startedAt?: string; // ISO timestamp from run start
}

/**
 * Log entry from iter-*.log JSONL files
 */
export interface LogEntry {
	type: LogEntryType;
	tool?: string; // Read, Write, Bash, Edit, etc.
	content: string;
	success?: boolean;
	timestamp?: string; // ISO timestamp if available
}

/**
 * Review receipt from impl-review
 */
export interface ReviewReceipt {
	verdict: "SHIP" | "NEEDS_WORK" | "MAJOR_RETHINK";
	timestamp: string;
	summary?: string;
	issues?: string[];
}

/**
 * flowctl validate response
 */
export interface ValidateResponse {
	success: boolean;
	epic: string;
	valid: boolean;
	errors: string[];
	warnings: string[];
	task_count: number;
}
