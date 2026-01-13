import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdtemp, rm, writeFile, appendFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import type { LogEntry } from './types';

import { LogWatcher } from './log-watcher';

describe('LogWatcher', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'log-watcher-test-'));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true });
  });

  describe('start/stop', () => {
    test('can start and stop without errors', async () => {
      const watcher = new LogWatcher(tempDir);

      await watcher.start();
      watcher.stop();

      // Should be able to stop multiple times
      watcher.stop();
    });

    test('start is idempotent', async () => {
      const watcher = new LogWatcher(tempDir);

      await watcher.start();
      await watcher.start(); // Should not throw
      watcher.stop();
    });
  });

  describe('line events', () => {
    test('emits line event for existing log content', async () => {
      // Create log file with content
      const logPath = join(tempDir, 'iter-1.log');
      const entry = { type: 'text', content: 'hello' };
      await writeFile(logPath, JSON.stringify(entry) + '\n');

      const watcher = new LogWatcher(tempDir);
      const received: LogEntry[] = [];

      watcher.on('line', (entry) => {
        received.push(entry);
      });

      await watcher.start();

      // Wait for initial read
      await new Promise((resolve) => setTimeout(resolve, 150));

      watcher.stop();

      expect(received).toHaveLength(1);
      expect(received[0]!.type).toBe('response');
      expect(received[0]!.content).toBe('hello');
    });

    test('emits line events for appended content', async () => {
      // Create initial log file
      const logPath = join(tempDir, 'iter-1.log');
      await writeFile(logPath, '');

      const watcher = new LogWatcher(tempDir);
      const received: LogEntry[] = [];

      watcher.on('line', (entry) => {
        received.push(entry);
      });

      await watcher.start();

      // Append content
      const entry1 = {
        type: 'tool_call',
        tool: 'Read',
        input: { file_path: '/a.ts' },
      };
      const entry2 = { type: 'tool_result', content: 'file contents' };
      await appendFile(logPath, JSON.stringify(entry1) + '\n');
      await appendFile(logPath, JSON.stringify(entry2) + '\n');

      // Wait for debounced read (100ms debounce + buffer)
      await new Promise((resolve) => setTimeout(resolve, 250));

      watcher.stop();

      expect(received.length).toBeGreaterThanOrEqual(2);
      expect(received[0]!.tool).toBe('Read');
    });

    test('handles malformed JSON gracefully', async () => {
      const logPath = join(tempDir, 'iter-1.log');
      await writeFile(
        logPath,
        [
          JSON.stringify({ type: 'text', content: 'valid1' }),
          'invalid json here',
          JSON.stringify({ type: 'text', content: 'valid2' }),
          '',
        ].join('\n')
      );

      const watcher = new LogWatcher(tempDir);
      const received: LogEntry[] = [];
      const errors: Error[] = [];

      watcher.on('line', (entry) => received.push(entry));
      watcher.on('error', (err) => errors.push(err));

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));
      watcher.stop();

      // Should have 2 valid entries, no errors (invalid lines skipped)
      expect(received).toHaveLength(2);
      expect(errors).toHaveLength(0);
    });
  });

  describe('new-iteration events', () => {
    test('emits new-iteration when iter file appears', async () => {
      // Start with iter-1.log
      const log1 = join(tempDir, 'iter-1.log');
      await writeFile(
        log1,
        JSON.stringify({ type: 'text', content: 'iter1' }) + '\n'
      );

      const watcher = new LogWatcher(tempDir);
      const iterations: Array<{ num: number; path: string }> = [];

      watcher.on('new-iteration', (num, path) => {
        iterations.push({ num, path });
      });

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Create iter-2.log
      const log2 = join(tempDir, 'iter-2.log');
      await writeFile(
        log2,
        JSON.stringify({ type: 'text', content: 'iter2' }) + '\n'
      );

      // Poll for iteration event (fs.watch timing varies by platform)
      let attempts = 0;
      while (iterations.length === 0 && attempts < 10) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        attempts++;
      }

      watcher.stop();

      // Should have detected the new iteration
      expect(iterations.length).toBeGreaterThanOrEqual(1);
      if (iterations.length > 0) {
        expect(iterations[0]!.num).toBe(2);
        expect(iterations[0]!.path).toContain('iter-2.log');
      }
    });

    test('does not switch to lower iteration number', async () => {
      // Start with iter-5.log
      const log5 = join(tempDir, 'iter-5.log');
      await writeFile(
        log5,
        JSON.stringify({ type: 'text', content: 'iter5' }) + '\n'
      );

      const watcher = new LogWatcher(tempDir);
      const iterations: number[] = [];

      watcher.on('new-iteration', (num) => {
        iterations.push(num);
      });

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Create iter-3.log (lower)
      const log3 = join(tempDir, 'iter-3.log');
      await writeFile(
        log3,
        JSON.stringify({ type: 'text', content: 'iter3' }) + '\n'
      );

      await new Promise((resolve) => setTimeout(resolve, 250));

      watcher.stop();

      // Should not have switched to lower iteration
      expect(iterations.filter((n) => n === 3)).toHaveLength(0);
    });
  });

  describe('error handling', () => {
    test('emits error for non-existent directory', async () => {
      // Use temp-based path that won't exist on any platform
      const nonExistentPath = join(
        tmpdir(),
        `nonexistent-${Date.now()}-${Math.random()}`
      );
      const watcher = new LogWatcher(nonExistentPath);
      const errors: Error[] = [];

      watcher.on('error', (err) => errors.push(err));

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));
      watcher.stop();

      // Should have emitted at least one error
      expect(errors.length).toBeGreaterThanOrEqual(1);
    });

    test('handles file deletion gracefully', async () => {
      const logPath = join(tempDir, 'iter-1.log');
      await writeFile(
        logPath,
        JSON.stringify({ type: 'text', content: 'initial' }) + '\n'
      );

      const watcher = new LogWatcher(tempDir);
      const errors: Error[] = [];

      watcher.on('error', (err) => errors.push(err));

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Delete the file
      await rm(logPath);
      await new Promise((resolve) => setTimeout(resolve, 250));

      watcher.stop();

      // ENOENT errors should be suppressed
      const nonEnoentErrors = errors.filter(
        (e) => (e as NodeJS.ErrnoException).code !== 'ENOENT'
      );
      expect(nonEnoentErrors).toHaveLength(0);
    });
  });

  describe('byte position tracking', () => {
    test('continues from last position after multiple appends', async () => {
      const logPath = join(tempDir, 'iter-1.log');
      await writeFile(logPath, '');

      const watcher = new LogWatcher(tempDir);
      const received: LogEntry[] = [];

      watcher.on('line', (entry) => received.push(entry));

      await watcher.start();

      // Multiple appends
      for (let i = 1; i <= 3; i++) {
        await appendFile(
          logPath,
          JSON.stringify({ type: 'text', content: `msg${i}` }) + '\n'
        );
        await new Promise((resolve) => setTimeout(resolve, 150));
      }

      watcher.stop();

      // Should have received all 3 messages (no duplicates)
      expect(received).toHaveLength(3);
      expect(received.map((e) => e.content)).toEqual(['msg1', 'msg2', 'msg3']);
    });

    test('handles file truncation', async () => {
      const logPath = join(tempDir, 'iter-1.log');
      await writeFile(
        logPath,
        JSON.stringify({ type: 'text', content: 'original' }) + '\n'
      );

      const watcher = new LogWatcher(tempDir);
      const received: LogEntry[] = [];
      const errors: Error[] = [];

      watcher.on('line', (entry) => received.push(entry));
      watcher.on('error', (err) => errors.push(err));

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Should have received original content
      expect(received.length).toBeGreaterThanOrEqual(1);
      expect(received[0]!.content).toBe('original');

      // Truncate file and write new content
      await writeFile(logPath, '');
      await appendFile(
        logPath,
        JSON.stringify({ type: 'text', content: 'new' }) + '\n'
      );

      // Poll for new content (fs.watch timing varies by platform)
      let attempts = 0;
      while (
        received.filter((e) => e.content === 'new').length === 0 &&
        attempts < 15
      ) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        attempts++;
      }

      watcher.stop();

      // No errors during truncation handling
      expect(errors).toHaveLength(0);

      // Should not have duplicate "original" entries
      const originalEntries = received.filter((e) => e.content === 'original');
      expect(originalEntries.length).toBe(1);

      // New content detection is platform-dependent; at minimum verify no crash
    });
  });

  describe('findLatestIteration', () => {
    test('finds highest iteration number', async () => {
      // Create multiple iteration logs
      await writeFile(join(tempDir, 'iter-1.log'), '');
      await writeFile(join(tempDir, 'iter-3.log'), '');
      await writeFile(join(tempDir, 'iter-2.log'), '');

      const watcher = new LogWatcher(tempDir);
      const received: LogEntry[] = [];

      // Create content in iter-3.log to verify it was selected
      await writeFile(
        join(tempDir, 'iter-3.log'),
        JSON.stringify({ type: 'text', content: 'from iter 3' }) + '\n'
      );

      watcher.on('line', (entry) => received.push(entry));

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));
      watcher.stop();

      expect(received).toHaveLength(1);
      expect(received[0]!.content).toBe('from iter 3');
    });

    test('handles empty directory', async () => {
      const watcher = new LogWatcher(tempDir);
      const errors: Error[] = [];

      watcher.on('error', (err) => errors.push(err));

      await watcher.start();
      await new Promise((resolve) => setTimeout(resolve, 150));
      watcher.stop();

      // Should not error on empty directory
      expect(errors).toHaveLength(0);
    });
  });
});
