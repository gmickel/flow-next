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
const DEBOUNCE_MS = 50;

/**
 * Polling watchdog interval (ms) - safety net for dropped fs.watch events
 */
const POLL_INTERVAL_MS = 500;

/**
 * Drain-to-EOF settings
 */
const DRAIN_MAX_ROUNDS = 20;
const DRAIN_SETTLE_MS = 30;
const DRAIN_MAX_TOTAL_MS = 1500;

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
  private watchedFilePath: string | null = null; // Immutable path for current watcher
  private bytePosition = 0;
  private remainder = '';
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private isRunning = false;
  private pendingIteration: number | null = null; // Guard against race conditions
  private readPromise: Promise<void> = Promise.resolve(); // Serialize reads
  private textDecoder: TextDecoder | null = null; // Streaming UTF-8 decoder

  constructor(runPath: string) {
    super();
    this.runPath = runPath;
  }

  /**
   * Start watching the run directory.
   * Returns Promise<void> - callers should await to ensure initial read completes.
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      return;
    }
    this.isRunning = true;
    this.textDecoder = new TextDecoder('utf-8', { fatal: false });

    // Find current iteration log (use != null to allow iter 0)
    const latest = await this.findLatestIteration();
    if (latest != null) {
      this.currentLogPath = join(this.runPath, latest.filename);
      // Emit initial iteration so UI knows what iteration we're on
      this.emit('new-iteration', latest.num, this.currentLogPath);
      await this.drainToEOF();
      this.watchCurrentLog();
    }

    // Watch directory for new iteration logs
    this.watchDirectory();

    // Start polling watchdog as safety net
    this.startPollWatchdog();

    // If no iter found, proactively rescan (fs.watch may miss first file on some platforms)
    if (latest == null) {
      setTimeout(() => {
        if (this.isRunning && !this.currentLogPath) {
          this.rescanForNewIteration();
        }
      }, 200);
    }
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

    this.stopPollWatchdog();

    if (this.fileWatcher) {
      this.fileWatcher.close();
      this.fileWatcher = null;
    }

    if (this.dirWatcher) {
      this.dirWatcher.close();
      this.dirWatcher = null;
    }

    this.currentLogPath = null;
    this.watchedFilePath = null;
    this.bytePosition = 0;
    this.remainder = '';
    this.pendingIteration = null;
    this.readPromise = Promise.resolve();
    this.textDecoder = null;
  }

  /**
   * Start polling watchdog - safety net for dropped fs.watch events
   */
  private startPollWatchdog(): void {
    if (this.pollTimer) return;

    this.pollTimer = setInterval(() => {
      if (!this.isRunning || !this.currentLogPath) return;

      // Check if file has grown beyond our position
      stat(this.currentLogPath)
        .then((info) => {
          if (info.size > this.bytePosition) {
            this.readPromise = this.readPromise.then(() =>
              this.drainToEOF().catch((error) => {
                this.emit(
                  'error',
                  error instanceof Error ? error : new Error(String(error))
                );
              })
            );
          }
        })
        .catch(() => {
          // File may not exist - ignore
        });
    }, POLL_INTERVAL_MS);
  }

  /**
   * Stop polling watchdog
   */
  private stopPollWatchdog(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  /**
   * Find the highest iteration number from existing iter-*.log files
   * Returns both the number and the actual filename (preserves padding format)
   */
  private async findLatestIteration(): Promise<{
    num: number;
    filename: string;
  } | null> {
    try {
      const entries = await readdir(this.runPath);
      let maxIter = -1;
      let maxFilename = '';

      for (const entry of entries) {
        const match = ITER_LOG_PATTERN.exec(entry);
        if (match?.[1]) {
          const iter = Number.parseInt(match[1], 10);
          if (iter > maxIter) {
            maxIter = iter;
            maxFilename = entry;
          }
        }
      }

      return maxIter >= 0 ? { num: maxIter, filename: maxFilename } : null;
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

          // Also trigger read if event is for current log file (backup for file watcher)
          if (
            name &&
            this.currentLogPath &&
            name === basename(this.currentLogPath)
          ) {
            this.debouncedRead();
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
      .then((latest) => {
        if (latest == null) return;

        const currentIter = this.getCurrentIteration();
        if (latest.num > currentIter) {
          this.handleNewLogFile(latest.filename);
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
    this.watchedFilePath = null;

    this.currentLogPath = newLogPath;
    this.bytePosition = 0;
    this.remainder = '';
    this.pendingIteration = null;
    // Reset decoder for clean UTF-8 stream on new iteration
    this.textDecoder = new TextDecoder('utf-8', { fatal: false });

    this.emit('new-iteration', newIter, newLogPath);

    // Await initial drain before starting watcher to avoid race
    await this.drainToEOF();
    this.watchCurrentLog();
  }

  /**
   * Watch the current log file for changes
   * Captures watchedFilePath immutably to avoid logging wrong path on close
   */
  private watchCurrentLog(): void {
    if (!this.currentLogPath) return;

    // Capture path immutably for this watcher instance
    const watchedPath = this.currentLogPath;
    this.watchedFilePath = watchedPath;

    try {
      const watcher = watch(watchedPath, { persistent: false }, (eventType) => {
        if (!this.isRunning) return;

        // Ignore stale events from old watcher after path changed
        if (this.currentLogPath !== watchedPath) {
          return;
        }

        if (eventType === 'change') {
          this.debouncedRead();
        } else if (eventType === 'rename') {
          // 'rename' can occur on truncation, atomic replace, or log rotation.
          // Watcher may stop delivering events after rename - re-arm it.
          this.handleFileRename();
        }
      });

      watcher.on('error', (error) => {
        // File may have been deleted (normal at run end)
        if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
          this.emit('error', error);
        }
      });

      this.fileWatcher = watcher;
    } catch (error) {
      this.emit(
        'error',
        error instanceof Error ? error : new Error(String(error))
      );
    }
  }

  /**
   * Handle file 'rename' event: read pending data and re-arm watcher
   */
  private handleFileRename(): void {
    // Read any pending data first
    this.readPromise = this.readPromise.then(async () => {
      if (!this.isRunning || !this.currentLogPath) return;

      try {
        // Check if file still exists
        await stat(this.currentLogPath);

        // Drain pending data
        await this.drainToEOF();

        // Re-arm watcher (close old, create new)
        if (this.fileWatcher) {
          this.fileWatcher.close();
          this.fileWatcher = null;
        }
        this.watchCurrentLog();
      } catch (error) {
        // File may have been deleted - normal at run end
        if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
          this.emit(
            'error',
            error instanceof Error ? error : new Error(String(error))
          );
        }
      }
    });
  }

  /**
   * Debounce rapid file change events, then drain to EOF
   */
  private debouncedRead(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.debounceTimer = null;
      // Chain reads to serialize (prevent concurrent races)
      this.readPromise = this.readPromise.then(() =>
        this.drainToEOF().catch((error) => {
          this.emit(
            'error',
            error instanceof Error ? error : new Error(String(error))
          );
        })
      );
    }, DEBOUNCE_MS);
  }

  /**
   * Drain file to EOF - keep reading until file size stops growing
   * This handles macOS fs.watch event coalescing where one event may
   * arrive before file is fully written.
   */
  private async drainToEOF(): Promise<void> {
    if (!this.currentLogPath || !this.isRunning) return;

    const startTime = Date.now();
    let rounds = 0;
    let lastSize = -1;

    while (rounds < DRAIN_MAX_ROUNDS) {
      // Check time limit
      if (Date.now() - startTime > DRAIN_MAX_TOTAL_MS) {
        break;
      }

      const didRead = await this.readFromPositionOnce();
      rounds++;

      if (!this.isRunning) return;

      // Get current size
      try {
        const info = await stat(this.currentLogPath);
        const currentSize = info.size;

        // If we didn't read anything and size is stable, we're done
        if (!didRead && currentSize === lastSize) {
          break;
        }

        // If we're caught up to file size and didn't read, done
        if (!didRead && this.bytePosition >= currentSize) {
          break;
        }

        lastSize = currentSize;

        // Small delay to let writer flush more data
        if (didRead) {
          await new Promise((resolve) => setTimeout(resolve, DRAIN_SETTLE_MS));
        }
      } catch {
        // File may not exist - stop draining
        break;
      }
    }
  }

  /**
   * Read new content from current log file starting at bytePosition
   * Returns true if any bytes were read
   */
  private async readFromPositionOnce(): Promise<boolean> {
    if (!this.currentLogPath || !this.isRunning) return false;

    try {
      // Get file size to check if there's new content
      const fileInfo = await stat(this.currentLogPath);

      // Re-check after await (stop() may have been called)
      if (!this.isRunning) return false;

      const fileSize = fileInfo.size;

      if (fileSize <= this.bytePosition) {
        // No new content (or file truncated)
        if (fileSize < this.bytePosition) {
          // File was truncated - reset position, remainder, and decoder
          this.bytePosition = 0;
          this.remainder = '';
          this.textDecoder = new TextDecoder('utf-8', { fatal: false });
        }
        return false;
      }

      // Read new bytes (not text - avoids mid-UTF-8 corruption)
      const file = Bun.file(this.currentLogPath);
      const slice = file.slice(this.bytePosition, fileSize);
      const bytes = await slice.arrayBuffer();

      // Re-check after await (stop() may have been called)
      if (!this.isRunning) return false;

      const bytesRead = bytes.byteLength;
      this.bytePosition = fileSize;

      // Decode with streaming to handle incomplete UTF-8 codepoints at boundary
      // stream:true buffers incomplete sequences for next decode call
      const newContent = this.textDecoder
        ? this.textDecoder.decode(new Uint8Array(bytes), { stream: true })
        : new TextDecoder('utf-8').decode(new Uint8Array(bytes));

      // Parse with remainder from previous read
      const toParse = this.remainder + newContent;
      const { entries, remainder } = parseChunk(toParse);
      this.remainder = remainder;

      // Emit each entry
      for (const entry of entries) {
        if (!this.isRunning) return true; // Check before each emit
        this.emit('line', entry);
      }

      return bytesRead > 0;
    } catch (error) {
      // File may not exist yet or may have been deleted
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        this.emit(
          'error',
          error instanceof Error ? error : new Error(String(error))
        );
      }
      return false;
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
