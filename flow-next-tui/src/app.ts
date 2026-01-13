/**
 * Main App component for flow-next TUI.
 * Wires together all components with state management and polling.
 */

import { TUI, matchesKey, ProcessTerminal, type Component } from '@mariozechner/pi-tui';
import { stat } from 'node:fs/promises';
import { join } from 'node:path';

import { Header } from './components/header.ts';
import { HelpOverlay } from './components/help-overlay.ts';
import { OutputPanel } from './components/output.ts';
import { SplitPanel } from './components/split-panel.ts';
import { StatusBar } from './components/status-bar.ts';
import { TaskDetail } from './components/task-detail.ts';
import { TaskList } from './components/task-list.ts';
import { getEpic, getTask, getTaskSpec, FlowctlNotFoundError } from './lib/flowctl.ts';
import { LogWatcher } from './lib/log-watcher.ts';
import {
  discoverRuns,
  findRepoRoot,
  getLatestRun,
  getReceiptStatus,
  getBlockReason,
} from './lib/runs.ts';
import { spawnRalph, findRalphScript, RalphNotFoundError } from './lib/spawn.ts';
import type { Epic, EpicTask, LogEntry, Run, Task } from './lib/types.ts';
import { getTheme, type Theme } from './themes/index.ts';

/**
 * App state interface
 */
export interface AppState {
  runs: Run[];
  currentRun?: Run;
  tasks: EpicTask[];
  selectedTaskIndex: number;
  outputBuffer: LogEntry[];
  iteration: number;
  elapsed: number; // seconds since run started
  showHelp: boolean;
  error?: string;
}

/**
 * App options from CLI
 */
export interface AppOptions {
  light?: boolean;
  noEmoji?: boolean;
  run?: string; // specific run ID to monitor
}

/** Compact mode threshold */
const COMPACT_WIDTH = 120;
const COMPACT_HEIGHT = 30;

/** Polling intervals (ms) */
const TASK_POLL_INTERVAL = 2000;
const TIMER_INTERVAL = 1000;

/**
 * Check if directory exists
 */
async function dirExists(path: string): Promise<boolean> {
  try {
    const s = await stat(path);
    return s.isDirectory();
  } catch {
    return false;
  }
}

/**
 * Main App component that implements pi-tui Component interface
 */
class App implements Component {
  private state: AppState;
  private theme: Theme;
  private useAscii: boolean;

  // Components
  private header: Header;
  private taskList: TaskList;
  private taskDetail: TaskDetail;
  private outputPanel: OutputPanel;
  private statusBar: StatusBar;
  private helpOverlay: HelpOverlay;
  private taskSplitPanel: SplitPanel;

  // References
  private logWatcher: LogWatcher | null = null;
  private taskPollTimer: ReturnType<typeof setInterval> | null = null;
  private timerInterval: ReturnType<typeof setInterval> | null = null;
  private tui: TUI | null = null;

  constructor(
    state: AppState,
    theme: Theme,
    useAscii: boolean,
    epic: Epic | undefined,
    currentTask: Task | undefined,
    taskSpec: string
  ) {
    this.state = state;
    this.theme = theme;
    this.useAscii = useAscii;

    // Create components
    this.header = new Header({
      state: state.currentRun?.active ? 'running' : 'complete',
      task: currentTask,
      epic,
      iteration: state.iteration,
      taskProgress: {
        done: state.tasks.filter((t) => t.status === 'done').length,
        total: state.tasks.length,
      },
      elapsed: state.elapsed,
      theme,
      useAscii,
    });

    this.taskList = new TaskList({
      tasks: state.tasks,
      selectedIndex: state.selectedTaskIndex,
      onSelect: () => {
        // Enter key - could expand task detail or similar
      },
      onSelectionChange: (task, index) => {
        this.state.selectedTaskIndex = index;
        void this.updateTaskDetail(task.id);
      },
      theme,
      useAscii,
    });

    this.taskDetail = new TaskDetail({
      task: currentTask ?? createPlaceholderTask(),
      spec: taskSpec || 'No task selected',
      theme,
      useAscii,
    });

    this.outputPanel = new OutputPanel({
      buffer: state.outputBuffer,
      iteration: state.iteration,
      theme,
      useAscii,
    });

    this.statusBar = new StatusBar({
      runId: state.currentRun?.id,
      errorCount: 0,
      theme,
    });

    this.helpOverlay = new HelpOverlay({
      theme,
      visible: state.showHelp,
      onClose: () => {
        this.state.showHelp = false;
      },
    });

    // Create split panel for TaskList | TaskDetail
    this.taskSplitPanel = new SplitPanel({
      left: this.taskList,
      right: this.taskDetail,
      ratio: 0.35,
      active: 'left',
    });
  }

  setTui(tui: TUI): void {
    this.tui = tui;
  }

  setupLogWatcher(): void {
    if (!this.state.currentRun) return;

    this.logWatcher = new LogWatcher(this.state.currentRun.path);
    this.logWatcher.on('line', (entry) => {
      this.outputPanel.appendLine(entry);
      // Count errors
      if (entry.type === 'error' || entry.success === false) {
        const currentErrorCount = this.state.outputBuffer.filter(
          (e) => e.type === 'error' || e.success === false
        ).length;
        this.statusBar.update({ errorCount: currentErrorCount });
      }
      this.tui?.requestRender();
    });
    this.logWatcher.on('new-iteration', (iteration) => {
      this.state.iteration = iteration;
      this.outputPanel.setIteration(iteration);
      this.outputPanel.clearBuffer();
      this.header.update({ iteration });
      this.tui?.requestRender();
    });
    this.logWatcher.on('error', (err) => {
      console.error('Log watcher error:', err);
    });
  }

  async startLogWatcher(): Promise<void> {
    if (this.logWatcher) {
      await this.logWatcher.start();
    }
  }

  setupPolling(): void {
    // Polling for tasks
    if (this.state.currentRun?.epic) {
      const epicId = this.state.currentRun.epic;
      this.taskPollTimer = setInterval(() => {
        void (async () => {
          try {
            const freshEpic = await getEpic(epicId);
            this.state.tasks = freshEpic.tasks;
            this.taskList.setTasks(freshEpic.tasks);
            this.header.update({
              taskProgress: {
                done: freshEpic.tasks.filter((t) => t.status === 'done').length,
                total: freshEpic.tasks.length,
              },
            });
            this.tui?.requestRender();
          } catch {
            // Ignore poll errors
          }
        })();
      }, TASK_POLL_INTERVAL);
    }

    // Timer for elapsed time
    const startTime = Date.now();
    this.timerInterval = setInterval(() => {
      this.state.elapsed = Math.floor((Date.now() - startTime) / 1000);
      this.header.update({ elapsed: this.state.elapsed });
      this.tui?.requestRender();
    }, TIMER_INTERVAL);
  }

  cleanup(): void {
    if (this.logWatcher) {
      this.logWatcher.stop();
    }
    if (this.taskPollTimer) {
      clearInterval(this.taskPollTimer);
    }
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }
  }

  private async updateTaskDetail(taskId: string): Promise<void> {
    try {
      const task = await getTask(taskId);
      const spec = await getTaskSpec(taskId);

      this.taskDetail.setTask(task);
      this.taskDetail.setSpec(spec);

      // Update receipts
      if (this.state.currentRun) {
        const receipts = await getReceiptStatus(this.state.currentRun.path, taskId);
        this.taskDetail.setReceipts(receipts);

        // Update block reason
        if (task.status === 'blocked') {
          const reason = await getBlockReason(taskId, this.state.currentRun.path);
          this.taskDetail.setBlockReason(reason);
        } else {
          this.taskDetail.setBlockReason(null);
        }
      }

      this.header.update({ task });
      this.tui?.requestRender();
    } catch {
      // Task may not exist - ignore
    }
  }

  render(width: number): string[] {
    const terminal = this.tui?.terminal;
    const height = terminal?.rows ?? 40;
    const isCompact = width < COMPACT_WIDTH || height < COMPACT_HEIGHT;

    // Calculate layout heights
    const headerHeight = isCompact ? 1 : 2;
    const statusBarHeight = 1;
    const contentHeight = height - headerHeight - statusBarHeight;

    // Update viewports
    if (!isCompact) {
      const taskPanelHeight = Math.floor(contentHeight * 0.4);
      const outputHeight = contentHeight - taskPanelHeight;
      this.taskDetail.setViewportHeight(taskPanelHeight);
      this.outputPanel.setViewportHeight(outputHeight);
    } else {
      this.outputPanel.setViewportHeight(contentHeight);
    }

    // Build lines
    const lines: string[] = [];

    // Header
    const headerLines = this.header.render(width);
    if (isCompact) {
      // Compact: single row header
      lines.push(headerLines[0] ?? '');
    } else {
      lines.push(...headerLines);
    }

    // Content area
    if (isCompact) {
      // Compact: full-width output only
      const outputLines = this.outputPanel.render(width);
      lines.push(...outputLines.slice(0, contentHeight));
    } else {
      // Normal: TaskList|TaskDetail above OutputPanel
      const taskPanelHeight = Math.floor(contentHeight * 0.4);
      const outputHeight = contentHeight - taskPanelHeight;

      // Task split panel
      const taskLines = this.taskSplitPanel.render(width);
      lines.push(...taskLines.slice(0, taskPanelHeight));

      // Pad if task panel is shorter
      while (lines.length < headerHeight + taskPanelHeight) {
        lines.push(' '.repeat(width));
      }

      // Output panel
      const outputLines = this.outputPanel.render(width);
      lines.push(...outputLines.slice(0, outputHeight));
    }

    // Status bar
    const statusLines = this.statusBar.render(width);
    lines.push(...statusLines);

    // Help overlay (renders on top via TUI overlay system)
    // Note: handled separately via tui.showOverlay

    return lines;
  }

  handleInput(data: string): void {
    // Help overlay takes priority (handled by TUI overlay system)

    // ? - toggle help
    if (data === '?') {
      this.state.showHelp = !this.state.showHelp;
      if (this.state.showHelp) {
        this.helpOverlay.show();
        this.tui?.showOverlay(this.helpOverlay);
      } else {
        this.helpOverlay.hide();
        this.tui?.hideOverlay();
      }
      return;
    }

    // q or Ctrl+C - quit
    if (matchesKey(data, 'q') || data === '\x03') {
      this.cleanup();
      this.tui?.stop();
      process.exit(0);
    }

    // j/k navigation - forward to task list
    if (matchesKey(data, 'j') || matchesKey(data, 'k') ||
        matchesKey(data, 'up') || matchesKey(data, 'down')) {
      this.taskList.handleInput(data);
      return;
    }

    // Other keys to output panel (scrolling)
    this.outputPanel.handleInput(data);
  }

  invalidate(): void {
    this.header.invalidate();
    this.taskList.invalidate();
    this.taskDetail.invalidate();
    this.outputPanel.invalidate();
    this.statusBar.invalidate();
    this.helpOverlay.invalidate();
  }
}

/**
 * Create and run the TUI app
 */
export async function createApp(options: AppOptions = {}): Promise<void> {
  const theme = getTheme(options.light);
  const useAscii = options.noEmoji ?? false;

  // Initial state
  const state: AppState = {
    runs: [],
    currentRun: undefined,
    tasks: [],
    selectedTaskIndex: 0,
    outputBuffer: [],
    iteration: 0,
    elapsed: 0,
    showHelp: false,
    error: undefined,
  };

  // Validate prerequisites
  const repoRoot = await findRepoRoot();

  // Check .flow/ exists
  const flowDir = join(repoRoot, '.flow');
  if (!(await dirExists(flowDir))) {
    renderError(
      'No .flow/ directory. Run flowctl init or ensure you\'re in a flow-next project.',
      theme
    );
    process.exit(1);
  }

  // Check scripts/ralph/ exists
  const ralphDir = join(repoRoot, 'scripts', 'ralph');
  if (!(await dirExists(ralphDir))) {
    renderError(
      'No scripts/ralph/. Run /flow-next:ralph-init to scaffold Ralph.',
      theme
    );
    process.exit(1);
  }

  // Discover runs
  try {
    state.runs = await discoverRuns();
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    renderError(`Failed to discover runs: ${msg}`, theme);
    process.exit(1);
  }

  // Select run
  if (options.run) {
    // User specified run
    const run = state.runs.find((r) => r.id === options.run);
    if (!run) {
      renderError(
        `Run '${options.run}' not found. Available: ${state.runs.map((r) => r.id).join(', ') || 'none'}`,
        theme
      );
      process.exit(1);
    }
    state.currentRun = run;
  } else if (state.runs.length > 0) {
    // Auto-select latest
    state.currentRun = getLatestRun(state.runs);
  } else {
    // No runs - prompt to start Ralph
    const shouldStart = await promptStartRalph(theme);
    if (shouldStart) {
      try {
        // Need an epic to start Ralph - check for open epics
        const { getEpics } = await import('./lib/flowctl.ts');
        const epics = await getEpics();
        const openEpics = epics.filter((e) => e.status === 'open');

        if (openEpics.length === 0) {
          renderError('No open epics. Create an epic first with flowctl epic create.', theme);
          process.exit(1);
        }

        // Use first open epic
        const epicId = openEpics[0]?.id;
        if (!epicId) {
          renderError('No epic ID found.', theme);
          process.exit(1);
        }

        console.log(theme.dim(`Starting Ralph on ${epicId}...`));
        const result = await spawnRalph(epicId);
        console.log(theme.success(`Ralph started: ${result.runId} (pid ${result.pid})`));

        // Re-discover runs
        state.runs = await discoverRuns();
        state.currentRun = state.runs.find((r) => r.id === result.runId);
      } catch (err) {
        if (err instanceof RalphNotFoundError) {
          renderError(err.message, theme);
        } else {
          const msg = err instanceof Error ? err.message : String(err);
          renderError(`Failed to start Ralph: ${msg}`, theme);
        }
        process.exit(1);
      }
    } else {
      renderError('No runs found. Start Ralph with: cd scripts/ralph && ./ralph.sh', theme);
      process.exit(1);
    }
  }

  // Load initial epic/tasks if we have a run with epic
  let epic: Epic | undefined;
  let currentTask: Task | undefined;
  let taskSpec = '';

  if (state.currentRun?.epic) {
    try {
      epic = await getEpic(state.currentRun.epic);
      state.tasks = epic.tasks;
      state.iteration = state.currentRun.iteration;

      // Find current task (first in_progress or first todo)
      const inProgress = state.tasks.find((t) => t.status === 'in_progress');
      const firstTodo = state.tasks.find((t) => t.status === 'todo');
      const activeTask = inProgress ?? firstTodo;

      if (activeTask) {
        state.selectedTaskIndex = state.tasks.findIndex((t) => t.id === activeTask.id);
        currentTask = await getTask(activeTask.id);
        taskSpec = await getTaskSpec(activeTask.id);
      }
    } catch (err) {
      if (err instanceof FlowctlNotFoundError) {
        state.error = err.message;
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        state.error = `Failed to load epic: ${msg}`;
      }
    }
  }

  // Create app component
  const app = new App(state, theme, useAscii, epic, currentTask, taskSpec);

  // Create terminal and TUI
  const terminal = new ProcessTerminal();
  const tui = new TUI(terminal);

  // Wire up
  app.setTui(tui);
  tui.addChild(app);
  tui.setFocus(app);

  // Set up watchers and polling
  app.setupLogWatcher();
  app.setupPolling();

  // Handle process signals
  process.on('SIGINT', () => {
    app.cleanup();
    tui.stop();
    process.exit(0);
  });
  process.on('SIGTERM', () => {
    app.cleanup();
    tui.stop();
    process.exit(0);
  });

  // Start log watcher
  await app.startLogWatcher();

  // Start TUI
  tui.start();

  // Keep process alive
  await new Promise(() => {});
}

/**
 * Create placeholder task for initial state
 */
function createPlaceholderTask(): Task {
  return {
    id: 'fn-0.0',
    epic: 'fn-0',
    title: 'No task selected',
    status: 'todo',
    depends_on: [],
    spec_path: '',
    priority: null,
    assignee: null,
    claim_note: '',
    claimed_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

/**
 * Render error and exit
 */
function renderError(message: string, theme: Theme): void {
  console.error(theme.error(`Error: ${message}`));
}

/**
 * Prompt user to start Ralph
 */
async function promptStartRalph(theme: Theme): Promise<boolean> {
  // Check if ralph.sh exists first
  const result = await findRalphScript();
  if (!result) {
    return false; // Can't start Ralph anyway
  }

  console.log(theme.warning('No runs found.'));
  console.log(theme.dim('Start Ralph now? [y/n]'));

  // Read single character from stdin
  return new Promise((resolve) => {
    const { stdin } = process;

    // Check if stdin is a TTY
    if (!stdin.isTTY) {
      resolve(false);
      return;
    }

    stdin.setRawMode(true);
    stdin.resume();
    stdin.setEncoding('utf8');

    const onData = (key: string): void => {
      stdin.setRawMode(false);
      stdin.pause();
      stdin.removeListener('data', onData);

      if (key === 'y' || key === 'Y') {
        resolve(true);
      } else {
        resolve(false);
      }
    };

    stdin.on('data', onData);
  });
}
