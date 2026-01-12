export interface Task {
	id: string;
	title: string;
	status: "todo" | "in_progress" | "done" | "blocked";
	spec_path?: string;
}

export interface Epic {
	id: string;
	title: string;
	status: "open" | "closed";
	tasks: Task[];
}

export interface Run {
	id: string;
	path: string;
	startedAt: Date;
	active: boolean;
}
