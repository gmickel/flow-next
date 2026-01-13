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

  constructor(runPath: string) {
    super();
    this.runPath = runPath;
  }

  /**
   * Start watching the run directory
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      return;
    }
    this.isRunning = true;

    // Find current iteration log
    const currentIter = await this.findLatestIteration();
    if (currentIter) {
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

          // Check if it's a new iteration log
          if (filename && ITER_LOG_PATTERN.test(filename)) {
            this.handleNewLogFile(filename);
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

    // Only switch if this is a newer iteration
    if (this.currentLogPath) {
      const currentMatch = ITER_LOG_PATTERN.exec(basename(this.currentLogPath));
      const currentIter = currentMatch?.[1]
        ? Number.parseInt(currentMatch[1], 10)
        : -1;

      if (newIter <= currentIter) {
        return;
      }
    }

    // Switch to new log
    if (this.fileWatcher) {
      this.fileWatcher.close();
      this.fileWatcher = null;
    }

    this.currentLogPath = newLogPath;
    this.bytePosition = 0;
    this.remainder = '';

    this.emit('new-iteration', newIter, newLogPath);

    // Read existing content before watching for changes
    this.readFromPosition().catch((error) => {
      this.emit(
        'error',
        error instanceof Error ? error : new Error(String(error))
      );
    });

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

          if (eventType === 'change') {
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
      this.readFromPosition().catch((error) => {
        this.emit(
          'error',
          error instanceof Error ? error : new Error(String(error))
        );
      });
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

      this.bytePosition = fileSize;

      // Parse with remainder from previous read
      const toParse = this.remainder + newContent;
      const { entries, remainder } = parseChunk(toParse);
      this.remainder = remainder;

      // Emit each entry
      for (const entry of entries) {
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
