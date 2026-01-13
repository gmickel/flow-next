import { EventEmitter } from 'node:events';
import { watch, type FSWatcher } from 'node:fs';
import { readdir, stat } from 'node:fs/promises';
import { basename, join } from 'node:path';

import type { LogEntry } from './types';

import { parseChunk } from './parser';

/**
 * Events emitted by LogWatcher
 */
export interface LogWatcherEvents {
  line: (entry: LogEntry) => void;
  error: (error: Error) => void;
  'new-iteration': (iteration: number, logPath: string) => void;
}

/**
 * Debounce delay for file change events (ms)
 */
const DEBOUNCE_MS = 100;

/**
 * Pattern for iteration log files
 */
const ITER_LOG_PATTERN = /^iter-(\d+)\.log$/;

/**
 * Watch a Ralph run directory for log updates.
 * Emits 'line' events for each parsed LogEntry.
 * Emits 'new-iteration' when a new iter-*.log file appears.
 * Emits 'error' on watch errors.
 */
export class LogWatcher extends EventEmitter {
  private runPath: string;
  private dirWatcher: FSWatcher | null = null;
  private fileWatcher: FSWatcher | null = null;
  private currentLogPath: string | null = null;
  private bytePosition = 0;
  private remainder = '';
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private isRunning = false;
  private pendingIteration: number | null = null; // Guard against race conditions
  private readPromise: Promise<void> = Promise.resolve(); // Serialize reads

  constructor(runPath: string) {
    super();
    this.runPath = runPath;
  }

  /**
   * Start watching the run directory.
   * Note: Returns Promise - callers should await to ensure initial read completes.
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      return;
    }
    this.isRunning = true;

    // Find current iteration log (use != null to allow iter 0)
    const currentIter = await this.findLatestIteration();
    if (currentIter != null) {
      this.currentLogPath = join(this.runPath, `iter-${currentIter}.log`);
      await this.readFromPosition();
      this.watchCurrentLog();
    }

    // Watch directory for new iteration logs
    this.watchDirectory();
  }

  /**
   * Stop watching and clean up
   */
  stop(): void {
    this.isRunning = false;

    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }

    if (this.fileWatcher) {
      this.fileWatcher.close();
      this.fileWatcher = null;
    }

    if (this.dirWatcher) {
      this.dirWatcher.close();
      this.dirWatcher = null;
    }

    this.currentLogPath = null;
    this.bytePosition = 0;
    this.remainder = '';
    this.pendingIteration = null;
    this.readPromise = Promise.resolve();
  }

  /**
   * Find the highest iteration number from existing iter-*.log files
   */
  private async findLatestIteration(): Promise<number | null> {
    try {
      const entries = await readdir(this.runPath);
      let maxIter = -1;

      for (const entry of entries) {
        const match = ITER_LOG_PATTERN.exec(entry);
        if (match?.[1]) {
          const iter = Number.parseInt(match[1], 10);
          if (iter > maxIter) {
            maxIter = iter;
          }
        }
      }

      return maxIter >= 0 ? maxIter : null;
    } catch {
      return null;
    }
  }

  /**
   * Watch the run directory for new iter-*.log files
   */
  private watchDirectory(): void {
    try {
      this.dirWatcher = watch(
        this.runPath,
        { persistent: false },
        (eventType, filename) => {
          if (!this.isRunning) return;

          // Note: fs.watch eventType is platform-dependent and unreliable.
          // 'rename' typically indicates create/delete but isn't guaranteed.
          // handleNewLogFile has guards (iteration comparison, pendingIteration)
          // that prevent redundant switches, so we process all events.

          // Normalize filename (can be Buffer on some platforms)
          const name =
            typeof filename === 'string'
              ? filename
              : ((filename as Buffer | null)?.toString() ?? '');

          // Check if it's a new iteration log
          if (name && ITER_LOG_PATTERN.test(name)) {
            this.handleNewLogFile(name);
          } else if (!name) {
            // On some platforms fs.watch delivers null/empty filename.
            // Rescan to detect any new iteration.
            this.rescanForNewIteration();
          }
        }
      );

      this.dirWatcher.on('error', (error) => {
        this.emit('error', error);
      });
    } catch (error) {
      this.emit(
        'error',
        error instanceof Error ? error : new Error(String(error))
      );
    }
  }

  /**
   * Handle a potentially new iteration log file
   */
  private handleNewLogFile(filename: string): void {
    const match = ITER_LOG_PATTERN.exec(filename);
    if (!match?.[1]) return;

    const newIter = Number.parseInt(match[1], 10);
    const newLogPath = join(this.runPath, filename);

    // Only switch if this is a newer iteration (including pending)
    const currentIter = this.getCurrentIteration();
    if (newIter <= currentIter) {
      return;
    }

    // Also skip if we're already switching to this or higher iteration
    if (this.pendingIteration != null && newIter <= this.pendingIteration) {
      return;
    }

    // Mark as pending to prevent race conditions
    this.pendingIteration = newIter;

    // Switch to new log (async to await initial read)
    this.switchToNewLog(newIter, newLogPath).catch((error) => {
      this.emit(
        'error',
        error instanceof Error ? error : new Error(String(error))
      );
    });
  }

  /**
   * Rescan for new iterations (used when fs.watch doesn't provide filename)
   */
  private rescanForNewIteration(): void {
    this.findLatestIteration()
      .then((latestIter) => {
        if (latestIter == null) return;

        const currentIter = this.getCurrentIteration();
        if (latestIter > currentIter) {
          this.handleNewLogFile(`iter-${latestIter}.log`);
        }
      })
      .catch((error) => {
        this.emit(
          'error',
          error instanceof Error ? error : new Error(String(error))
        );
      });
  }

  /**
   * Get current iteration number from currentLogPath
   */
  private getCurrentIteration(): number {
    if (!this.currentLogPath) return -1;
    const match = ITER_LOG_PATTERN.exec(basename(this.currentLogPath));
    return match?.[1] ? Number.parseInt(match[1], 10) : -1;
  }

  /**
   * Switch to a new log file, waiting for file existence and initial read
   */
  private async switchToNewLog(
    newIter: number,
    newLogPath: string
  ): Promise<void> {
    // Keep old watcher until we confirm new file exists (avoid orphan state)
    const oldWatcher = this.fileWatcher;

    // Wait for file to exist (fs.watch event can fire before file is created)
    let attempts = 0;
    let fileExists = false;
    while (attempts < 10) {
      try {
        await stat(newLogPath);
        fileExists = true;
        break;
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
          attempts++;
          await new Promise((resolve) => setTimeout(resolve, 50));
        } else {
          throw error;
        }
      }
    }

    // If file never appeared, schedule a rescan and keep old watcher active
    if (!fileExists) {
      this.pendingIteration = null;
      // Schedule rescan in case file appears later (slow FS, race)
      setTimeout(() => {
        if (this.isRunning) {
          this.rescanForNewIteration();
        }
      }, 500);
      return;
    }

    // Check if this switch is stale (higher iteration now pending) - keep old watcher
    if (this.pendingIteration != null && newIter < this.pendingIteration) {
      return;
    }

    if (!this.isRunning) {
      this.pendingIteration = null;
      return;
    }

    // Now safe to close old watcher and commit to new file
    if (oldWatcher) {
      oldWatcher.close();
    }
    this.fileWatcher = null;

    this.currentLogPath = newLogPath;
    this.bytePosition = 0;
    this.remainder = '';
    this.pendingIteration = null;

    this.emit('new-iteration', newIter, newLogPath);

    // Await initial read before starting watcher to avoid race
    await this.readFromPosition();
    this.watchCurrentLog();
  }

  /**
   * Watch the current log file for changes
   */
  private watchCurrentLog(): void {
    if (!this.currentLogPath) return;

    try {
      this.fileWatcher = watch(
        this.currentLogPath,
        { persistent: false },
        (eventType) => {
          if (!this.isRunning) return;

          // Handle both 'change' and 'rename' events
          // 'rename' can occur on truncation, atomic replace, or log rotation
          if (eventType === 'change' || eventType === 'rename') {
            this.debouncedRead();
          }
        }
      );

      this.fileWatcher.on('error', (error) => {
        // File may have been deleted (normal at run end)
        if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
          this.emit('error', error);
        }
      });
    } catch (error) {
      this.emit(
        'error',
        error instanceof Error ? error : new Error(String(error))
      );
    }
  }

  /**
   * Debounce rapid file change events
   */
  private debouncedRead(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.debounceTimer = null;
      // Chain reads to serialize (prevent concurrent readFromPosition races)
      this.readPromise = this.readPromise.then(() =>
        this.readFromPosition().catch((error) => {
          this.emit(
            'error',
            error instanceof Error ? error : new Error(String(error))
          );
        })
      );
    }, DEBOUNCE_MS);
  }

  /**
   * Read new content from current log file starting at bytePosition
   */
  private async readFromPosition(): Promise<void> {
    if (!this.currentLogPath || !this.isRunning) return;

    try {
      // Get file size to check if there's new content
      const fileInfo = await stat(this.currentLogPath);

      // Re-check after await (stop() may have been called)
      if (!this.isRunning) return;

      const fileSize = fileInfo.size;

      if (fileSize <= this.bytePosition) {
        // No new content (or file truncated)
        if (fileSize < this.bytePosition) {
          // File was truncated - reset
          this.bytePosition = 0;
          this.remainder = '';
        }
        return;
      }

      // Read new bytes
      const file = Bun.file(this.currentLogPath);
      const slice = file.slice(this.bytePosition, fileSize);
      const newContent = await slice.text();

      // Re-check after await (stop() may have been called)
      if (!this.isRunning) return;

      this.bytePosition = fileSize;

      // Parse with remainder from previous read
      const toParse = this.remainder + newContent;
      const { entries, remainder } = parseChunk(toParse);
      this.remainder = remainder;

      // Emit each entry
      for (const entry of entries) {
        if (!this.isRunning) return; // Check before each emit
        this.emit('line', entry);
      }
    } catch (error) {
      // File may not exist yet or may have been deleted
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        this.emit(
          'error',
          error instanceof Error ? error : new Error(String(error))
        );
      }
    }
  }

  // Typed event methods
  override on<K extends keyof LogWatcherEvents>(
    event: K,
    listener: LogWatcherEvents[K]
  ): this {
    return super.on(event, listener);
  }

  override once<K extends keyof LogWatcherEvents>(
    event: K,
    listener: LogWatcherEvents[K]
  ): this {
    return super.once(event, listener);
  }

  override off<K extends keyof LogWatcherEvents>(
    event: K,
    listener: LogWatcherEvents[K]
  ): this {
    return super.off(event, listener);
  }

  override emit<K extends keyof LogWatcherEvents>(
    event: K,
    ...args: Parameters<LogWatcherEvents[K]>
  ): boolean {
    return super.emit(event, ...args);
  }
}
