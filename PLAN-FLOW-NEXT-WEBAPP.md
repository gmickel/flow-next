# Flow-Next Web App: Comprehensive Implementation Plan

> A Next.js web application providing a Kanban-based UI for AI-assisted project development using the flow-next plugin and Claude Agent SDK.

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [SQLite Job Queue Libraries](#4-sqlite-job-queue-libraries)
5. [Kanban Board Design](#5-kanban-board-design)
6. [Plugin Integration Strategy](#6-plugin-integration-strategy)
7. [Command Prompts System](#7-command-prompts-system)
8. [flowctl-ts: TypeScript Port](#8-flowctl-ts-typescript-port)
9. [Agent Integration Layer](#9-agent-integration-layer)
10. [Real-Time Log Streaming](#10-real-time-log-streaming)
11. [Database Schema](#11-database-schema)
12. [Frontend Components](#12-frontend-components)
13. [Notification System](#13-notification-system)
14. [Automated Documentation](#14-automated-documentation)
15. [Deployment Architecture](#15-deployment-architecture)
16. [Development Phases](#16-development-phases)
17. [Risk Analysis](#17-risk-analysis)
18. [Future Enhancements](#18-future-enhancements)

---

## 1. Executive Summary

Build a TypeScript/Next.js web application that provides a visual Kanban interface on top of the flow-next plugin, enabling users to manage AI-assisted project development from idea inception through autonomous implementation and review.

### Core Workflow

```
Ideas → Spec Interview → Spec Review → Ralph (Autonomous Work) → Implementation Review → Done
```

### Key Principles

1. **Plugin Integrity**: Skills and agents remain in the standard Claude Code plugin structure—the web app invokes them via the Claude Agent SDK, not by embedding them
2. **Editable Prompts**: Command prompts stored in SQLite with version history and a UI editor
3. **SQLite-Only**: No Redis dependency—SQLite for all data storage and job queuing
4. **File-Based Streaming**: Real-time log streaming via file watching, not database polling
5. **Self-Hostable**: Docker-based deployment for VPS or homelab

---

## 2. Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Next.js App (App Router)                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     Frontend (React 18)                            │  │
│  │  Kanban Board │ Interview Wizard │ Log Viewer │ Prompt Editor     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              Server Actions + Route Handlers (API)                 │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────────┐  │
│  │  SQLite Queue   │  │  Command        │  │  flowctl-ts           │  │
│  │  (Sidequest.js) │  │  Prompts (DB)   │  │  (.flow/ state)       │  │
│  └─────────────────┘  └─────────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
              │                    │                      │
              │                    │                      │
              ▼                    ▼                      ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    SQLite DB    │    │  Claude Agent SDK   │    │  Target Repository  │
│                 │    │                     │    │                     │
│  - projects     │    │  Invokes with:      │    │  .claude/plugins/   │
│  - jobs         │    │  --plugin-dir       │    │    flow-next/       │
│  - logs         │    │  pointing to ───────┼───▶│      skills/        │
│  - prompts      │    │  plugin location    │    │      agents/        │
│  - users        │    │                     │    │      commands/      │
│  - notifications│    │                     │    │                     │
└─────────────────┘    └─────────────────────┘    │  .flow/             │
                                                  │    epics/           │
                                                  │    specs/           │
                                                  │    tasks/           │
                                                  └─────────────────────┘
```

### Data Flow

1. **User creates idea** → Stored in SQLite `projects` table
2. **User moves to "Ready for Spec"** → Job queued, Claude Agent SDK invoked with plugin-dir
3. **Claude discovers skills/agents** → Executes `flow-next-interview` skill from plugin directory
4. **Interview questions generated** → Stored in SQLite, user notified
5. **User answers questions** → Answers stored, spec generated via SDK
6. **Spec review** → External review via Codex backend
7. **Ralph autonomous loop** → Background job runs iteratively until complete
8. **Logs streamed** → Written to files, watched and streamed via SSE
9. **Implementation review** → Final review before merge
10. **PR/Changelog generated** → Artifacts created automatically

---

## 3. Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Framework** | Next.js 14+ (App Router) | SSR, Server Actions, Route Handlers, unified frontend/backend |
| **Language** | TypeScript (strict mode) | Type safety, Claude Agent SDK compatibility |
| **UI Framework** | React 18 + Tailwind CSS | Component ecosystem, utility-first styling |
| **Component Library** | shadcn/ui | Copy-paste components, fully customizable, accessible |
| **Drag-and-Drop** | @dnd-kit/core | Modern, accessible, mobile-friendly |
| **State Management** | Zustand + TanStack Query | Lightweight client state + server state sync |
| **Database** | SQLite (better-sqlite3) | Zero-dependency, single-file, portable |
| **ORM** | Drizzle ORM | Type-safe, lightweight, excellent SQLite support |
| **Job Queue** | Sidequest.js | SQLite-native, dashboard, TypeScript, active maintenance |
| **Agent SDK** | @anthropic-ai/claude-agent-sdk | Official Claude Code programmatic integration |
| **Real-time** | Server-Sent Events + chokidar | File watching for low-latency log streaming |
| **Notifications** | Web Push API + ntfy.sh | Browser push + mobile/desktop native |
| **Containerization** | Docker Compose | Self-hosted VPS/homelab deployment |

---

## 4. SQLite Job Queue Libraries

### Research Summary

| Library | TypeScript | Performance | Features | Maintenance |
|---------|------------|-------------|----------|-------------|
| **[Sidequest.js](https://github.com/sidequestjs/sidequest)** | ✅ Native | Good | Dashboard, multi-DB, scheduled jobs, WAL mode | ✅ Active (v1.12.0) |
| **[Liteque](https://github.com/karakeep-app/liteque)** | ✅ Native | Good | Zod validation, simple API, Drizzle ORM | ✅ Active |
| **[plainjob](https://github.com/justplainstuff/plainjob)** | ✅ Native | 15k jobs/s | Cron jobs, better-sqlite3/bun:sqlite | ✅ Active |
| **[better-queue-sqlite](https://www.npmjs.com/package/better-queue-sqlite)** | ❌ JS | Moderate | Store adapter for better-queue | ⚠️ Stable |
| **[node-persistent-queue](https://github.com/damoclark/node-persistent-queue)** | ❌ JS | Moderate | FIFO, crash recovery | ⚠️ Stable |

### Recommendation: Sidequest.js

**Why Sidequest.js:**
- **Active maintenance** from the creator of node-cron (5M+ downloads/month)
- **Web dashboard** for monitoring jobs and queues
- **SQLite WAL mode** support for improved concurrency
- **TypeScript native** with full type safety
- **Scheduled jobs** for recurring tasks
- **Job lifecycle management** with retry, exponential backoff, snooze
- **Worker threads** for non-blocking processing

**Installation:**
```bash
npm install sidequest @sidequest/sqlite-backend
```

**Basic Usage:**
```typescript
import Sidequest, { Job } from 'sidequest';

// Initialize with SQLite
await Sidequest.start({
  backend: {
    driver: "@sidequest/sqlite-backend",
    config: "./data/jobs.db",
  },
  dashboard: {
    enabled: true,
    port: 8678,
  },
});

// Define a job
export class RalphJob extends Job {
  static queue = 'ralph';

  async run(projectId: string, epicId: string) {
    // Ralph implementation
    return { status: 'completed' };
  }
}

// Enqueue
await Sidequest.build(RalphJob).enqueue(projectId, epicId);
```

### Alternative: Liteque (Lightweight Option)

If dashboard isn't needed and simpler is preferred:

```typescript
import { SqliteQueue, Runner, buildDBClient } from 'liteque';
import { z } from 'zod';

const db = buildDBClient({ path: './data/queue.db' });

const ralphQueue = new SqliteQueue<{ projectId: string; epicId: string }>({
  db,
  name: 'ralph',
  validator: z.object({ projectId: z.string(), epicId: z.string() }),
});

const runner = new Runner({
  queue: ralphQueue,
  concurrency: 1,
  handler: async (job) => {
    // Process job
  },
});

runner.start();
```

---

## 5. Kanban Board Design

### Column Definitions

| Column | Status Code | Description | Trigger Action |
|--------|-------------|-------------|----------------|
| **Ideas** | `idea` | Raw feature concepts | None (manual) |
| **Ready for Spec** | `spec_pending` | Queued for AI interview | Auto-start interview job |
| **Spec: Answers Needed** | `spec_interview` | Questions generated, awaiting user | Show interview wizard |
| **Spec: Ready for Review** | `spec_review` | Spec complete, needs approval | Enable review actions |
| **Ready for Ralph** | `ralph_pending` | Approved spec, queued for work | Enable "Start Ralph" |
| **Ralph: Working** | `ralph_active` | Autonomous loop in progress | Show live logs |
| **Work: Ready for Review** | `impl_review` | Implementation complete | Enable merge/reject |

### Card Data Model

```typescript
interface ProjectCard {
  id: string;                    // UUID
  title: string;                 // User-provided title
  description: string;           // Initial idea text
  status: CardStatus;            // Column placement
  priority: 'low' | 'medium' | 'high' | 'critical';
  position: number;              // Order within column

  // Repository association
  repoId: string;                // FK to repos table
  repoPath: string;              // Absolute path (denormalized for convenience)

  // Flow-next integration
  epicId?: string;               // fn-N-xxx after spec generation
  branch?: string;               // Git branch name

  // Interview state
  interviewSessionId?: string;   // Claude session ID for resumption

  // Review state
  specReviewStatus?: 'ship' | 'needs_work' | 'major_rethink';
  implReviewStatus?: 'ship' | 'needs_work' | 'major_rethink';

  // Ralph state
  ralphJobId?: string;           // Sidequest job ID
  ralphIteration?: number;       // Current iteration
  ralphStatus?: 'running' | 'paused' | 'blocked' | 'completed' | 'failed';

  // Artifacts
  pullRequestUrl?: string;
  changelogEntry?: string;

  // Metadata
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
}

type CardStatus =
  | 'idea'
  | 'spec_pending'
  | 'spec_interview'
  | 'spec_review'
  | 'ralph_pending'
  | 'ralph_active'
  | 'impl_review'
  | 'done';
```

---

## 6. Plugin Integration Strategy

### Critical Principle

**Skills and agents MUST remain in the standard Claude Code plugin directory structure.** The web app does not store or manage skill/agent prompts—it only tells the Claude Agent SDK where to find them.

### Plugin Location Options

**Option A: Symlink in Target Repo**
```
target-repo/
└── .claude/
    └── plugins/
        └── flow-next -> /path/to/flow/plugins/flow-next
```

**Option B: Global Plugin Directory**
```
~/.claude/plugins/flow-next/
├── skills/
├── agents/
└── commands/
```

**Option C: App-Managed Plugin Copy**
```
~/.flow-app/plugins/flow-next/
├── skills/
├── agents/
└── commands/
```

### SDK Invocation

```typescript
// src/lib/agents/sdk-runner.ts
import { query } from '@anthropic-ai/claude-agent-sdk';
import path from 'path';

interface RunAgentOptions {
  repoPath: string;
  prompt: string;
  pluginDir?: string;
  maxTurns?: number;
  permissionMode?: 'default' | 'acceptEdits' | 'bypassPermissions';
}

export async function runAgent(options: RunAgentOptions) {
  const {
    repoPath,
    prompt,
    pluginDir = getDefaultPluginDir(),
    maxTurns = 100,
    permissionMode = 'acceptEdits',
  } = options;

  const result = query({
    prompt,
    options: {
      cwd: repoPath,
      pluginDir,  // Claude Code discovers skills/agents from here
      allowedTools: [
        'Read', 'Write', 'Edit', 'Glob', 'Grep',
        'Bash', 'Task', 'Skill', 'WebSearch', 'WebFetch'
      ],
      maxTurns,
      permissionMode,
    }
  });

  return result;
}

function getDefaultPluginDir(): string {
  // Check environment variable first
  if (process.env.FLOW_PLUGIN_DIR) {
    return process.env.FLOW_PLUGIN_DIR;
  }

  // Default to app-managed location
  return path.join(process.env.HOME || '~', '.flow-app', 'plugins', 'flow-next');
}
```

### What the App Invokes vs What Claude Discovers

| Component | Managed By | Location |
|-----------|------------|----------|
| **Skills** (flow-next-plan, flow-next-work, etc.) | Claude Code | Plugin directory |
| **Agents** (repo-scout, practice-scout, etc.) | Claude Code | Plugin directory |
| **Command Prompts** (orchestration layer) | Web App | SQLite database |
| **flowctl-ts** (state management) | Web App | App codebase |

---

## 7. Command Prompts System

### Design Goals

1. **Editable**: Users can customize prompts without code changes
2. **Versioned**: Track changes, enable rollback
3. **Template Variables**: Dynamic content injection
4. **Seeded Defaults**: Ship with sensible defaults

### Database Schema

```typescript
// src/lib/db/schema.ts

export const commandPrompts = sqliteTable('command_prompts', {
  id: text('id').primaryKey(),
  slug: text('slug').unique().notNull(),        // 'interview', 'plan', 'work', etc.
  name: text('name').notNull(),                  // Display name
  description: text('description'),              // Help text for users
  prompt: text('prompt').notNull(),              // Markdown prompt template
  variables: text('variables').default('[]'),    // JSON array of available variables
  isSystem: integer('is_system', { mode: 'boolean' }).default(false),
  version: integer('version').default(1),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const commandPromptHistory = sqliteTable('command_prompt_history', {
  id: text('id').primaryKey(),
  promptId: text('prompt_id').references(() => commandPrompts.id).notNull(),
  prompt: text('prompt').notNull(),
  version: integer('version').notNull(),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  changedBy: text('changed_by'),
});
```

### Default Prompts

```typescript
// src/lib/db/seed-prompts.ts

export const DEFAULT_PROMPTS = [
  {
    slug: 'interview',
    name: 'Specification Interview',
    description: 'Generates interview questions to refine a feature specification',
    variables: ['title', 'description', 'repoPath'],
    prompt: `You are an expert software architect conducting a specification interview.

## Project Idea
Title: {{title}}
Description: {{description}}

## Your Task
1. First, explore the codebase at {{repoPath}} to understand existing patterns and architecture
2. Use the Skill tool to invoke 'flow-next-interview' for deep specification refinement
3. The skill will generate targeted questions across these categories:
   - Scope: Boundaries, what's included/excluded
   - Architecture: Technical approach, patterns, integrations
   - Edge cases: Error handling, failure modes
   - Constraints: Performance, security, compatibility

Let the skill handle the interview process. It will use AskUserQuestion to gather answers.`,
  },
  {
    slug: 'plan',
    name: 'Plan Generation',
    description: 'Creates an epic with dependency-ordered tasks from a specification',
    variables: ['title', 'spec', 'repoPath', 'epicId'],
    prompt: `You are creating an implementation plan for a software feature.

## Feature
Title: {{title}}
Epic ID: {{epicId}}

## Specification
{{spec}}

## Instructions
Use the Skill tool to invoke 'flow-next-plan' with this specification.

The skill will:
1. Run parallel research agents (repo-scout, practice-scout, docs-scout, etc.)
2. Analyze the codebase for relevant patterns
3. Generate dependency-ordered tasks
4. Create the epic and tasks in .flow/

Wait for the skill to complete and report the results.`,
  },
  {
    slug: 'work',
    name: 'Task Implementation',
    description: 'Implements a specific task from an epic',
    variables: ['taskId', 'taskTitle', 'taskDescription', 'acceptance', 'repoPath'],
    prompt: `You are implementing a task in a software project.

## Task
ID: {{taskId}}
Title: {{taskTitle}}

## Description
{{taskDescription}}

## Acceptance Criteria
{{acceptance}}

## Instructions
Use the Skill tool to invoke 'flow-next-work' with task ID {{taskId}}.

The skill will:
1. Re-anchor context by reading relevant files
2. Implement the required changes
3. Write and run tests
4. Prepare changes for review

Follow the skill's guidance and ensure all acceptance criteria are met.`,
  },
  {
    slug: 'plan-review',
    name: 'Plan Review',
    description: 'Carmack-level review of an implementation plan',
    variables: ['epicId', 'spec', 'repoPath'],
    prompt: `You are performing a Carmack-level review of an implementation plan.

## Epic
ID: {{epicId}}

## Specification
{{spec}}

## Instructions
Use the Skill tool to invoke 'flow-next-plan-review' with epic ID {{epicId}}.

The skill will coordinate the review using the configured backend (Codex or export).

Review criteria:
- Completeness: Does the plan cover all requirements?
- Feasibility: Can this be implemented as designed?
- Architecture: Is the technical approach sound?
- Risks: Are there security or scalability concerns?
- Testability: Can the implementation be verified?

Wait for the review verdict (SHIP, NEEDS_WORK, or MAJOR_RETHINK).`,
  },
  {
    slug: 'impl-review',
    name: 'Implementation Review',
    description: 'Carmack-level review of completed implementation',
    variables: ['epicId', 'branch', 'repoPath'],
    prompt: `You are performing a Carmack-level review of a completed implementation.

## Epic
ID: {{epicId}}
Branch: {{branch}}

## Instructions
Use the Skill tool to invoke 'flow-next-impl-review'.

The skill will:
1. Analyze changes vs main branch
2. Run comprehensive code review
3. Return verdict (SHIP, NEEDS_WORK, or MAJOR_RETHINK)

Review criteria:
- Correctness: Does the code do what it should?
- Simplicity: Is it as simple as possible?
- DRY: Is there unnecessary duplication?
- Edge cases: Are error conditions handled?
- Tests: Is there adequate test coverage?
- Security: Are there any vulnerabilities?`,
  },
];
```

### Prompt Rendering

```typescript
// src/lib/prompts/renderer.ts
import { db } from '@/lib/db/client';
import { commandPrompts } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function renderPrompt(
  slug: string,
  variables: Record<string, string>
): Promise<string> {
  const prompt = await db.query.commandPrompts.findFirst({
    where: eq(commandPrompts.slug, slug),
  });

  if (!prompt) {
    throw new Error(`Prompt not found: ${slug}`);
  }

  // Replace template variables: {{variableName}}
  let rendered = prompt.prompt;
  for (const [key, value] of Object.entries(variables)) {
    rendered = rendered.replaceAll(`{{${key}}}`, value);
  }

  return rendered;
}
```

### Prompt Editor UI

The app includes a settings page at `/settings/prompts` where users can:
- View all command prompts
- Edit prompt content with syntax highlighting
- See available template variables
- View version history
- Revert to previous versions

---

## 8. flowctl-ts: TypeScript Port

### Module Structure

```
src/lib/flowctl/
├── index.ts              # Public API exports
├── types.ts              # All type definitions
├── constants.ts          # Schema version, defaults
│
├── core/
│   ├── config.ts         # .flow/config.json management
│   ├── init.ts           # Initialize .flow/ directory
│   └── detect.ts         # Detect existing .flow/
│
├── epic/
│   ├── create.ts         # Create epic with ID generation
│   ├── read.ts           # Load epic from JSON
│   ├── update.ts         # Update epic fields
│   ├── close.ts          # Mark epic done
│   └── list.ts           # List all epics
│
├── task/
│   ├── create.ts         # Create task under epic
│   ├── read.ts           # Load task JSON + markdown
│   ├── update.ts         # Update task fields
│   ├── transition.ts     # Status transitions
│   └── list.ts           # List tasks for epic
│
├── spec/
│   ├── read.ts           # Read spec markdown
│   ├── write.ts          # Write/update spec
│   └── parse.ts          # Parse spec sections
│
├── memory/
│   ├── init.ts           # Initialize memory system
│   ├── add.ts            # Add pitfall/convention/decision
│   ├── read.ts           # Read memory files
│   └── search.ts         # Search across memory
│
├── workflow/
│   ├── next.ts           # Get next actionable item
│   ├── ready.ts          # Check if task ready (deps met)
│   └── graph.ts          # Dependency graph utilities
│
├── review/
│   ├── codex.ts          # Codex review integration
│   ├── prompts.ts        # Review prompt templates
│   └── verdict.ts        # Parse verdict tags
│
└── utils/
    ├── id.ts             # ID generation
    ├── git.ts            # Git operations
    ├── actor.ts          # Actor detection
    └── fs.ts             # File system helpers
```

### Core Types

```typescript
// src/lib/flowctl/types.ts

export interface FlowConfig {
  schemaVersion: 2;
  memory: {
    enabled: boolean;
  };
  review: {
    backend: 'codex' | 'export' | 'none';
  };
}

export interface Epic {
  id: string;                    // fn-N-xxx
  title: string;
  status: 'open' | 'done';
  createdAt: Date;
  assignee: string;
  planReviewStatus: 'ship' | 'needs_work' | 'major_rethink' | 'unknown';
  planReviewedAt?: Date;
  branchName?: string;
  dependsOnEpics: string[];
  taskCount: number;
  doneTaskCount: number;
}

export interface Task {
  id: string;                    // fn-N-xxx.M
  epicId: string;
  title: string;
  status: 'todo' | 'in_progress' | 'blocked' | 'done';
  priority: number;
  assignee?: string;
  dependsOn: string[];
  createdAt: Date;
  startedAt?: Date;
  doneAt?: Date;
}

export interface TaskSpec {
  description: string;
  acceptance: string[];
  doneSummary?: string;
  evidence?: string[];
}

export interface MemoryEntry {
  type: 'pitfall' | 'convention' | 'decision';
  content: string;
  addedAt: Date;
  source?: string;
}

export type ReviewVerdict = 'SHIP' | 'NEEDS_WORK' | 'MAJOR_RETHINK';
```

### Public API

```typescript
// src/lib/flowctl/index.ts

// Initialization
export async function initFlow(repoPath: string): Promise<void>;
export async function detectFlow(repoPath: string): Promise<boolean>;
export async function getConfig(repoPath: string): Promise<FlowConfig>;
export async function setConfig(repoPath: string, updates: Partial<FlowConfig>): Promise<void>;

// Epic operations
export async function createEpic(repoPath: string, title: string): Promise<Epic>;
export async function getEpic(repoPath: string, epicId: string): Promise<Epic>;
export async function listEpics(repoPath: string, filter?: { status?: string }): Promise<Epic[]>;
export async function updateEpic(repoPath: string, epicId: string, updates: Partial<Epic>): Promise<Epic>;
export async function closeEpic(repoPath: string, epicId: string): Promise<Epic>;

// Task operations
export async function createTask(repoPath: string, epicId: string, title: string, spec: TaskSpec): Promise<Task>;
export async function getTask(repoPath: string, taskId: string): Promise<Task & { spec: TaskSpec }>;
export async function listTasks(repoPath: string, epicId: string): Promise<Task[]>;
export async function startTask(repoPath: string, taskId: string): Promise<Task>;
export async function completeTask(repoPath: string, taskId: string, summary: string, evidence: string[]): Promise<Task>;
export async function blockTask(repoPath: string, taskId: string, reason: string): Promise<Task>;

// Spec operations
export async function getSpec(repoPath: string, epicId: string): Promise<string>;
export async function setSpec(repoPath: string, epicId: string, content: string): Promise<void>;

// Workflow
export async function getNextAction(repoPath: string): Promise<{ type: 'plan' | 'work' | 'none'; id?: string }>;
export async function isTaskReady(repoPath: string, taskId: string): Promise<boolean>;

// Memory
export async function initMemory(repoPath: string): Promise<void>;
export async function addMemory(repoPath: string, entry: Omit<MemoryEntry, 'addedAt'>): Promise<void>;
export async function searchMemory(repoPath: string, query: string): Promise<MemoryEntry[]>;

// Git utilities
export async function createBranch(repoPath: string, branchName: string): Promise<void>;
export async function getChangedFiles(repoPath: string, base?: string): Promise<string[]>;
export async function getCurrentBranch(repoPath: string): Promise<string>;
```

### ID Generation (Ported from Python)

```typescript
// src/lib/flowctl/utils/id.ts

const SUFFIX_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789';

export function generateEpicSuffix(length = 3): string {
  let result = '';
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  for (let i = 0; i < length; i++) {
    result += SUFFIX_CHARS[array[i] % SUFFIX_CHARS.length];
  }
  return result;
}

export async function getNextEpicId(repoPath: string): Promise<string> {
  const epicsDir = path.join(repoPath, '.flow', 'epics');
  const files = await fs.readdir(epicsDir).catch(() => []);

  const maxNum = files.reduce((max, file) => {
    const match = file.match(/^fn-(\d+)-/);
    return match ? Math.max(max, parseInt(match[1], 10)) : max;
  }, 0);

  const suffix = generateEpicSuffix();
  return `fn-${maxNum + 1}-${suffix}`;
}

export function getNextTaskId(epicId: string, existingTasks: Task[]): string {
  const maxNum = existingTasks.reduce((max, task) => {
    const match = task.id.match(/\.(\d+)$/);
    return match ? Math.max(max, parseInt(match[1], 10)) : max;
  }, 0);

  return `${epicId}.${maxNum + 1}`;
}
```

---

## 9. Agent Integration Layer

### Interview Flow

```typescript
// src/lib/agents/interview.ts
import { query } from '@anthropic-ai/claude-agent-sdk';
import { renderPrompt } from '@/lib/prompts/renderer';
import { db } from '@/lib/db/client';
import { interviewQuestions, projects } from '@/lib/db/schema';
import { writeLogEntry } from '@/lib/logs/writer';

export async function runInterview(projectId: string): Promise<void> {
  const project = await getProjectWithRepo(projectId);

  // Render prompt from database
  const prompt = await renderPrompt('interview', {
    title: project.title,
    description: project.description,
    repoPath: project.repo.path,
  });

  // Create log file for streaming
  const logFile = await createLogFile(projectId, 'interview');

  // Run Claude Agent SDK
  const result = query({
    prompt,
    options: {
      cwd: project.repo.path,
      pluginDir: getPluginDir(),
      allowedTools: ['Read', 'Grep', 'Glob', 'Skill', 'Task', 'AskUserQuestion'],
      maxTurns: 50,
    },
  });

  for await (const message of result) {
    // Log all messages for streaming
    await writeLogEntry(logFile, {
      type: message.type,
      content: message,
      timestamp: new Date(),
    });

    // Capture session ID for resumption
    if (message.type === 'system' && message.subtype === 'init') {
      await db.update(projects)
        .set({ interviewSessionId: message.session_id })
        .where(eq(projects.id, projectId));
    }

    // Extract questions from skill output
    if (message.type === 'assistant') {
      const questions = parseQuestionsFromResponse(message.message.content);
      if (questions.length > 0) {
        await saveQuestions(projectId, questions);
      }
    }
  }
}
```

### Ralph Job Handler

```typescript
// src/lib/jobs/ralph.ts
import { Job } from 'sidequest';
import { query } from '@anthropic-ai/claude-agent-sdk';
import * as flowctl from '@/lib/flowctl';
import { renderPrompt } from '@/lib/prompts/renderer';
import { writeLogEntry, createLogFile } from '@/lib/logs/writer';
import { db } from '@/lib/db/client';
import { projects } from '@/lib/db/schema';

interface RalphConfig {
  maxIterations: number;
  requirePlanReview: boolean;
  branchMode: 'new' | 'current';
}

export class RalphJob extends Job {
  static queue = 'ralph';
  static maxAttempts = 1;  // Ralph handles its own retries

  async run(projectId: string, epicId: string, config: RalphConfig) {
    const project = await getProjectWithRepo(projectId);
    const repoPath = project.repo.path;
    const logFile = await createLogFile(projectId, 'ralph');

    let iteration = 0;

    while (iteration < config.maxIterations) {
      iteration++;

      // Update progress
      await db.update(projects)
        .set({ ralphIteration: iteration })
        .where(eq(projects.id, projectId));

      await writeLogEntry(logFile, {
        level: 'info',
        message: `Starting iteration ${iteration}`,
        timestamp: new Date(),
      });

      // Get next action from flowctl
      const action = await flowctl.getNextAction(repoPath);

      await writeLogEntry(logFile, {
        level: 'info',
        message: `Next action: ${action.type}`,
        data: action,
        timestamp: new Date(),
      });

      if (action.type === 'none') {
        await writeLogEntry(logFile, {
          level: 'info',
          message: 'All tasks complete, closing epic',
          timestamp: new Date(),
        });
        await flowctl.closeEpic(repoPath, epicId);
        return { status: 'completed', iterations: iteration };
      }

      if (action.type === 'work') {
        const taskId = action.id!;
        const task = await flowctl.getTask(repoPath, taskId);

        // Render work prompt
        const prompt = await renderPrompt('work', {
          taskId: task.id,
          taskTitle: task.title,
          taskDescription: task.spec.description,
          acceptance: task.spec.acceptance.join('\n- '),
          repoPath,
        });

        await flowctl.startTask(repoPath, taskId);

        // Run Claude
        const result = query({
          prompt,
          options: {
            cwd: repoPath,
            pluginDir: getPluginDir(),
            permissionMode: 'acceptEdits',
            maxTurns: 50,
          },
        });

        let summary = '';
        for await (const message of result) {
          await writeLogEntry(logFile, {
            type: message.type,
            content: message,
            timestamp: new Date(),
          });

          if (message.type === 'assistant') {
            summary = extractText(message);
          }
        }

        await flowctl.completeTask(repoPath, taskId, summary, []);
      }
    }

    return { status: 'max_iterations', iterations: iteration };
  }
}
```

---

## 10. Real-Time Log Streaming

### Design: File Watching (Not DB Polling)

Log streaming uses file watching via `chokidar` for low-latency updates.

### Log File Structure

```
~/.flow-app/logs/
├── {projectId}/
│   ├── interview-{timestamp}.jsonl
│   ├── ralph-{timestamp}.jsonl
│   └── review-{timestamp}.jsonl
```

### Log Writer

```typescript
// src/lib/logs/writer.ts
import fs from 'fs/promises';
import path from 'path';

const LOG_DIR = path.join(process.env.HOME || '~', '.flow-app', 'logs');

export interface LogEntry {
  timestamp: Date;
  level?: 'debug' | 'info' | 'warn' | 'error';
  type?: string;
  message?: string;
  content?: unknown;
  data?: unknown;
}

export async function createLogFile(projectId: string, phase: string): Promise<string> {
  const projectDir = path.join(LOG_DIR, projectId);
  await fs.mkdir(projectDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const logFile = path.join(projectDir, `${phase}-${timestamp}.jsonl`);

  // Create empty file
  await fs.writeFile(logFile, '');

  return logFile;
}

export async function writeLogEntry(logFile: string, entry: LogEntry): Promise<void> {
  const line = JSON.stringify({
    ...entry,
    timestamp: entry.timestamp.toISOString(),
  }) + '\n';

  await fs.appendFile(logFile, line);
}

export async function getActiveLogFile(projectId: string): Promise<string | null> {
  const projectDir = path.join(LOG_DIR, projectId);

  try {
    const files = await fs.readdir(projectDir);
    const sorted = files.sort().reverse();
    return sorted[0] ? path.join(projectDir, sorted[0]) : null;
  } catch {
    return null;
  }
}
```

### SSE Route Handler with File Watching

```typescript
// src/app/api/logs/[projectId]/stream/route.ts
import { NextRequest } from 'next/server';
import chokidar from 'chokidar';
import fs from 'fs/promises';
import { getActiveLogFile } from '@/lib/logs/writer';

export async function GET(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const projectId = params.projectId;
  const encoder = new TextEncoder();

  let isActive = true;
  let watcher: chokidar.FSWatcher | null = null;
  let fileHandle: fs.FileHandle | null = null;
  let bytesRead = 0;

  request.signal.addEventListener('abort', () => {
    isActive = false;
    watcher?.close();
    fileHandle?.close();
  });

  const stream = new ReadableStream({
    async start(controller) {
      const logFile = await getActiveLogFile(projectId);

      if (!logFile) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'info', message: 'Waiting for logs...' })}\n\n`));
      } else {
        // Read existing content
        fileHandle = await fs.open(logFile, 'r');
        const existingContent = await fileHandle.readFile('utf-8');
        bytesRead = Buffer.byteLength(existingContent);

        for (const line of existingContent.split('\n').filter(Boolean)) {
          controller.enqueue(encoder.encode(`data: ${line}\n\n`));
        }

        // Watch for changes
        watcher = chokidar.watch(logFile, {
          persistent: true,
          usePolling: false,
          awaitWriteFinish: {
            stabilityThreshold: 100,
            pollInterval: 50,
          },
        });

        watcher.on('change', async () => {
          if (!isActive || !fileHandle) return;

          try {
            const stats = await fileHandle.stat();
            if (stats.size > bytesRead) {
              const buffer = Buffer.alloc(stats.size - bytesRead);
              await fileHandle.read(buffer, 0, buffer.length, bytesRead);
              bytesRead = stats.size;

              const newContent = buffer.toString('utf-8');
              for (const line of newContent.split('\n').filter(Boolean)) {
                controller.enqueue(encoder.encode(`data: ${line}\n\n`));
              }
            }
          } catch (error) {
            console.error('Error reading log file:', error);
          }
        });
      }

      // Keep-alive ping every 30 seconds
      const pingInterval = setInterval(() => {
        if (isActive) {
          controller.enqueue(encoder.encode(': ping\n\n'));
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

### Frontend Log Hook

```typescript
// src/hooks/use-log-stream.ts
import { useEffect, useState, useCallback } from 'react';

interface LogEntry {
  timestamp: string;
  level?: string;
  type?: string;
  message?: string;
  content?: unknown;
}

export function useLogStream(projectId: string | null) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const eventSource = new EventSource(`/api/logs/${projectId}/stream`);

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const entry = JSON.parse(event.data) as LogEntry;
        setLogs((prev) => [...prev, entry]);
      } catch {
        // Ignore parse errors (e.g., ping messages)
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      setError('Connection lost, retrying...');
    };

    return () => {
      eventSource.close();
    };
  }, [projectId]);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  return { logs, isConnected, error, clearLogs };
}
```

---

## 11. Database Schema

### Complete Schema

```typescript
// src/lib/db/schema.ts
import { sqliteTable, text, integer, real, index } from 'drizzle-orm/sqlite-core';
import { relations } from 'drizzle-orm';

// Users
export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  email: text('email').unique().notNull(),
  name: text('name'),
  ntfyTopic: text('ntfy_topic'),
  pushSubscriptions: text('push_subscriptions').default('[]'),
  preferences: text('preferences').default('{}'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
});

// Repositories
export const repos = sqliteTable('repos', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  path: text('path').unique().notNull(),
  defaultBranch: text('default_branch').default('main'),
  pluginInstalled: integer('plugin_installed', { mode: 'boolean' }).default(false),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
});

// Projects (Kanban cards)
export const projects = sqliteTable('projects', {
  id: text('id').primaryKey(),
  title: text('title').notNull(),
  description: text('description'),
  status: text('status').notNull().default('idea'),
  priority: text('priority').default('medium'),
  position: integer('position').default(0),

  repoId: text('repo_id').references(() => repos.id),
  epicId: text('epic_id'),
  branch: text('branch'),

  interviewSessionId: text('interview_session_id'),

  ralphJobId: text('ralph_job_id'),
  ralphIteration: integer('ralph_iteration'),
  ralphStatus: text('ralph_status'),

  specReviewStatus: text('spec_review_status'),
  implReviewStatus: text('impl_review_status'),

  pullRequestUrl: text('pull_request_url'),
  changelogEntry: text('changelog_entry'),

  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
  createdBy: text('created_by').references(() => users.id),
}, (table) => ({
  statusIdx: index('idx_projects_status').on(table.status),
  repoIdx: index('idx_projects_repo').on(table.repoId),
}));

// Interview Questions
export const interviewQuestions = sqliteTable('interview_questions', {
  id: text('id').primaryKey(),
  projectId: text('project_id').references(() => projects.id).notNull(),
  category: text('category').notNull(),
  question: text('question').notNull(),
  required: integer('required', { mode: 'boolean' }).default(true),
  answer: text('answer'),
  answeredAt: integer('answered_at', { mode: 'timestamp' }),
  orderIndex: integer('order_index').default(0),
});

// Command Prompts
export const commandPrompts = sqliteTable('command_prompts', {
  id: text('id').primaryKey(),
  slug: text('slug').unique().notNull(),
  name: text('name').notNull(),
  description: text('description'),
  prompt: text('prompt').notNull(),
  variables: text('variables').default('[]'),
  isSystem: integer('is_system', { mode: 'boolean' }).default(false),
  version: integer('version').default(1),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

// Prompt History (for versioning)
export const commandPromptHistory = sqliteTable('command_prompt_history', {
  id: text('id').primaryKey(),
  promptId: text('prompt_id').references(() => commandPrompts.id).notNull(),
  prompt: text('prompt').notNull(),
  version: integer('version').notNull(),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  changedBy: text('changed_by'),
});

// Notifications
export const notifications = sqliteTable('notifications', {
  id: text('id').primaryKey(),
  userId: text('user_id').references(() => users.id).notNull(),
  projectId: text('project_id').references(() => projects.id),
  type: text('type').notNull(),
  title: text('title').notNull(),
  body: text('body'),
  actionUrl: text('action_url'),
  read: integer('read', { mode: 'boolean' }).default(false),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
}, (table) => ({
  userIdx: index('idx_notifications_user').on(table.userId),
  unreadIdx: index('idx_notifications_unread').on(table.userId, table.read),
}));

// Relations
export const projectsRelations = relations(projects, ({ one, many }) => ({
  repo: one(repos, { fields: [projects.repoId], references: [repos.id] }),
  questions: many(interviewQuestions),
  notifications: many(notifications),
  creator: one(users, { fields: [projects.createdBy], references: [users.id] }),
}));

export const interviewQuestionsRelations = relations(interviewQuestions, ({ one }) => ({
  project: one(projects, { fields: [interviewQuestions.projectId], references: [projects.id] }),
}));

export const notificationsRelations = relations(notifications, ({ one }) => ({
  user: one(users, { fields: [notifications.userId], references: [users.id] }),
  project: one(projects, { fields: [notifications.projectId], references: [projects.id] }),
}));
```

---

## 12. Frontend Components

### Directory Structure

```
src/components/
├── ui/                           # shadcn/ui primitives
│   ├── button.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   ├── dropdown-menu.tsx
│   ├── input.tsx
│   ├── textarea.tsx
│   ├── badge.tsx
│   ├── progress.tsx
│   ├── tabs.tsx
│   └── ...
│
├── kanban/
│   ├── board.tsx                 # Main DnD context + columns
│   ├── column.tsx                # Single column with droppable area
│   ├── card.tsx                  # Draggable project card
│   ├── card-actions.tsx          # Card context menu
│   ├── new-idea-dialog.tsx       # Create new idea modal
│   └── column-header.tsx         # Column title + count
│
├── project/
│   ├── detail-panel.tsx          # Slide-out project details
│   ├── overview-tab.tsx          # Basic info + status
│   ├── spec-tab.tsx              # Specification viewer/editor
│   ├── tasks-tab.tsx             # Task list from .flow/
│   ├── logs-tab.tsx              # Embedded log viewer
│   ├── artifacts-tab.tsx         # PR, changelog, etc.
│   └── action-bar.tsx            # Context-sensitive actions
│
├── interview/
│   ├── wizard.tsx                # Multi-step wizard container
│   ├── wizard-progress.tsx       # Progress indicator
│   ├── question-card.tsx         # Single question display
│   ├── answer-input.tsx          # Text/select input
│   └── wizard-navigation.tsx     # Previous/Next/Submit
│
├── logs/
│   ├── log-viewer.tsx            # Virtualized log display
│   ├── log-entry.tsx             # Single log line
│   ├── log-filters.tsx           # Level/type filters
│   └── connection-status.tsx     # SSE connection indicator
│
├── prompts/
│   ├── prompt-list.tsx           # List all prompts
│   ├── prompt-editor.tsx         # Monaco/CodeMirror editor
│   └── prompt-variables.tsx      # Variable reference panel
│
├── settings/
│   ├── repo-manager.tsx          # Add/remove repositories
│   ├── notification-prefs.tsx    # Push notification settings
│   └── user-profile.tsx          # User settings
│
└── shared/
    ├── notification-bell.tsx     # Header notification icon
    ├── notification-dropdown.tsx # Notification list
    ├── repo-selector.tsx         # Repository dropdown
    ├── status-badge.tsx          # Status indicators
    ├── priority-badge.tsx        # Priority indicators
    └── loading-skeleton.tsx      # Loading states
```

### Key Component: Kanban Board

```typescript
// src/components/kanban/board.tsx
'use client';

import { useState } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { KanbanColumn } from './column';
import { ProjectCard } from './card';
import { moveProject } from '@/actions/projects';
import type { Project, CardStatus } from '@/types';

const COLUMNS: { id: CardStatus; title: string; color: string }[] = [
  { id: 'idea', title: 'Ideas', color: 'bg-slate-50' },
  { id: 'spec_pending', title: 'Ready for Spec', color: 'bg-blue-50' },
  { id: 'spec_interview', title: 'Answers Needed', color: 'bg-amber-50' },
  { id: 'spec_review', title: 'Spec Review', color: 'bg-purple-50' },
  { id: 'ralph_pending', title: 'Ready for Ralph', color: 'bg-green-50' },
  { id: 'ralph_active', title: 'Ralph Working', color: 'bg-green-100' },
  { id: 'impl_review', title: 'Work Review', color: 'bg-indigo-50' },
];

export function KanbanBoard({ projects }: { projects: Project[] }) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const activeProject = projects.find((p) => p.id === activeId);

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const projectId = active.id as string;
    const newStatus = over.id as CardStatus;
    const project = projects.find((p) => p.id === projectId);

    if (project && project.status !== newStatus) {
      await moveProject(projectId, newStatus);
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={(e) => setActiveId(e.active.id as string)}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 p-4 overflow-x-auto min-h-[calc(100vh-4rem)]">
        {COLUMNS.map((column) => (
          <KanbanColumn
            key={column.id}
            id={column.id}
            title={column.title}
            color={column.color}
            projects={projects.filter((p) => p.status === column.id)}
          />
        ))}
      </div>

      <DragOverlay>
        {activeProject && <ProjectCard project={activeProject} isDragging />}
      </DragOverlay>
    </DndContext>
  );
}
```

---

## 13. Notification System

### Notification Types

| Event | Type | Priority | Channels |
|-------|------|----------|----------|
| Interview questions ready | `interview_ready` | High | Push, In-app |
| Spec review verdict | `spec_review` | High | Push, In-app |
| Ralph blocked/failed | `ralph_blocked` | Critical | Push, In-app |
| Ralph completed | `ralph_complete` | Medium | Push, In-app |
| Implementation review verdict | `impl_review` | High | Push, In-app |
| PR ready for merge | `pr_ready` | Medium | In-app |

### Web Push Integration

```typescript
// src/lib/notifications/web-push.ts
import webpush from 'web-push';

webpush.setVapidDetails(
  'mailto:admin@example.com',
  process.env.VAPID_PUBLIC_KEY!,
  process.env.VAPID_PRIVATE_KEY!
);

export async function sendPushNotification(
  subscription: PushSubscription,
  notification: { title: string; body: string; url?: string }
) {
  try {
    await webpush.sendNotification(
      subscription,
      JSON.stringify({
        title: notification.title,
        body: notification.body,
        data: { url: notification.url },
      })
    );
  } catch (error) {
    console.error('Push notification failed:', error);
    // Handle expired subscriptions
  }
}
```

### ntfy.sh Integration (Mobile/Desktop Native)

```typescript
// src/lib/notifications/ntfy.ts

export async function sendNtfyNotification(
  topic: string,
  notification: {
    title: string;
    body: string;
    priority?: 'min' | 'low' | 'default' | 'high' | 'urgent';
    url?: string;
  }
) {
  const headers: Record<string, string> = {
    'Title': notification.title,
  };

  if (notification.priority) {
    headers['Priority'] = notification.priority;
  }

  if (notification.url) {
    headers['Click'] = notification.url;
  }

  await fetch(`https://ntfy.sh/${topic}`, {
    method: 'POST',
    headers,
    body: notification.body,
  });
}
```

---

## 14. Automated Documentation

### Changelog Generation

```typescript
// src/lib/artifacts/changelog.ts
import { query } from '@anthropic-ai/claude-agent-sdk';
import * as flowctl from '@/lib/flowctl';
import { execSync } from 'child_process';

export async function generateChangelog(
  repoPath: string,
  epicId: string,
  branch: string
): Promise<string> {
  // Get commits from branch
  const commits = execSync(
    `git log main..${branch} --pretty=format:"%s" --no-merges`,
    { cwd: repoPath, encoding: 'utf-8' }
  ).split('\n').filter(Boolean);

  // Get spec for context
  const spec = await flowctl.getSpec(repoPath, epicId);

  const prompt = `Generate a changelog entry for this feature.

## Specification
${spec}

## Commits
${commits.map((c) => `- ${c}`).join('\n')}

## Instructions
Write a concise changelog entry (2-4 bullet points) focusing on user-facing changes.
Use past tense. Start each bullet with a verb (Added, Fixed, Improved, etc.)
Do not include implementation details.`;

  const result = query({
    prompt,
    options: { maxTurns: 5 },
  });

  let changelog = '';
  for await (const message of result) {
    if (message.type === 'assistant') {
      changelog = extractText(message);
    }
  }

  return changelog;
}
```

### PR Description Generation

```typescript
// src/lib/artifacts/pull-request.ts
import { execSync } from 'child_process';
import * as flowctl from '@/lib/flowctl';

export async function createPullRequest(
  repoPath: string,
  epicId: string,
  branch: string
): Promise<string> {
  const epic = await flowctl.getEpic(repoPath, epicId);
  const spec = await flowctl.getSpec(repoPath, epicId);
  const tasks = await flowctl.listTasks(repoPath, epicId);

  // Generate description
  const description = `## Summary
${spec.split('\n').slice(0, 10).join('\n')}

## Tasks Completed
${tasks.map((t) => `- [x] ${t.title}`).join('\n')}

## Test Plan
- [ ] All tests pass
- [ ] Manual testing completed
- [ ] No regressions introduced
`;

  // Create PR via gh CLI
  const prUrl = execSync(
    `gh pr create --title "${epic.title}" --body "${description.replace(/"/g, '\\"')}" --base main --head ${branch}`,
    { cwd: repoPath, encoding: 'utf-8' }
  ).trim();

  return prUrl;
}
```

---

## 15. Deployment Architecture

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=file:/data/flow-app.db
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY}
      - VAPID_PRIVATE_KEY=${VAPID_PRIVATE_KEY}
      - FLOW_PLUGIN_DIR=/plugins/flow-next
    volumes:
      - app-data:/data
      - app-logs:/logs
      - ${REPOS_PATH:-./repos}:/repos:rw
      - ./plugins/flow-next:/plugins/flow-next:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  app-data:
  app-logs:
```

### Dockerfile

```dockerfile
# Dockerfile
FROM node:22-alpine AS base

# Install dependencies
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# Build
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && pnpm build

# Production
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

### Environment Variables

```bash
# .env.example

# Database
DATABASE_URL=file:./data/flow-app.db

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Web Push (generate with: npx web-push generate-vapid-keys)
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=

# Plugin location
FLOW_PLUGIN_DIR=/path/to/flow-next

# Optional: ntfy.sh server (default: https://ntfy.sh)
NTFY_SERVER=https://ntfy.sh
```

---

## 16. Development Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] Next.js project scaffolding (App Router, TypeScript strict)
- [ ] Drizzle ORM + SQLite setup with migrations
- [ ] Basic database schema (users, repos, projects)
- [ ] Kanban board UI with drag-and-drop
- [ ] Project CRUD (ideas column only)
- [ ] Repository management (add/list/remove)

### Phase 2: flowctl-ts Core (Weeks 3-4)
- [ ] Port core flowctl functions to TypeScript
- [ ] Epic CRUD operations
- [ ] Task CRUD operations
- [ ] Spec read/write
- [ ] ID generation utilities
- [ ] Git utilities (branch, diff)

### Phase 3: Command Prompts (Week 5)
- [ ] Prompt database schema + migrations
- [ ] Seed default prompts
- [ ] Prompt rendering with variables
- [ ] Prompt editor UI
- [ ] Version history + rollback

### Phase 4: Interview Flow (Weeks 6-7)
- [ ] Claude Agent SDK integration
- [ ] Interview job handler
- [ ] Question extraction + storage
- [ ] Interview wizard UI
- [ ] Answer submission
- [ ] Spec generation from answers

### Phase 5: Log Streaming (Week 8)
- [ ] Log file writer
- [ ] chokidar file watcher
- [ ] SSE route handler
- [ ] Log viewer component (virtualized)
- [ ] Connection status indicator

### Phase 6: Ralph Integration (Weeks 9-10)
- [ ] Sidequest.js setup
- [ ] Ralph job handler
- [ ] Progress tracking
- [ ] Ralph controls (start/pause/stop)
- [ ] Status display in UI

### Phase 7: Reviews & Artifacts (Weeks 11-12)
- [ ] Spec review integration
- [ ] Implementation review integration
- [ ] Verdict handling
- [ ] Changelog generation
- [ ] PR creation

### Phase 8: Notifications (Week 13)
- [ ] Web Push setup
- [ ] ntfy.sh integration
- [ ] Notification triggers
- [ ] Notification center UI
- [ ] User preferences

### Phase 9: Polish & Deploy (Weeks 14-15)
- [ ] Mobile-responsive refinements
- [ ] Error handling + recovery
- [ ] Loading states
- [ ] Docker configuration
- [ ] Health checks
- [ ] Documentation

---

## 17. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Claude SDK API changes | Medium | High | Pin versions, abstract SDK layer |
| Plugin structure changes | Low | Medium | Version check, migration scripts |
| Long-running Ralph jobs | High | Medium | Timeouts, health checks, pause/resume |
| Context window exhaustion | Medium | High | Session chunking, fresh context per task |
| SQLite concurrency limits | Low | Medium | WAL mode, connection pooling |
| File watching reliability | Low | Low | Fallback to polling, health checks |

---

## 18. Future Enhancements

### Near-Term
- Multi-user collaboration with real-time presence
- GitHub/GitLab issue sync
- Custom interview question templates
- Task dependency visualization

### Long-Term
- Parallel Ralph workers (multiple projects)
- Analytics dashboard (time tracking, velocity)
- Plugin marketplace integration
- Mobile native app (React Native)

---

## Appendix: File Count Estimates

| Component | Files | Lines (est.) |
|-----------|-------|--------------|
| flowctl-ts | ~25 | ~2,500 |
| Server Actions | ~10 | ~1,000 |
| Route Handlers | ~8 | ~600 |
| React Components | ~35 | ~3,000 |
| Hooks | ~10 | ~500 |
| Database/Schema | ~5 | ~400 |
| Job Handlers | ~5 | ~800 |
| Prompts System | ~5 | ~400 |
| Types | ~8 | ~300 |
| **Total** | **~111** | **~9,500** |

---

## References

### Libraries
- [Sidequest.js](https://github.com/sidequestjs/sidequest) - SQLite job queue
- [Liteque](https://github.com/karakeep-app/liteque) - Alternative lightweight queue
- [plainjob](https://github.com/justplainstuff/plainjob) - High-performance option
- [@anthropic-ai/claude-agent-sdk](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk) - Claude Code SDK
- [@dnd-kit/core](https://dndkit.com/) - Drag and drop
- [Drizzle ORM](https://orm.drizzle.team/) - TypeScript ORM
- [chokidar](https://github.com/paulmillr/chokidar) - File watching

### Documentation
- [Next.js App Router](https://nextjs.org/docs/app)
- [Claude Agent SDK Guide](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/sdk)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query)
