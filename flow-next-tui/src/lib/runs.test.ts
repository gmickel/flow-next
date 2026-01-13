import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdtemp, rm, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import {
  discoverRuns,
  isRunActive,
  getLatestRun,
  getRunDetails,
  getReceiptStatus,
  getBlockReason,
  validateRun,
  clearRepoRootCache,
} from './runs';

describe('runs', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'runs-test-'));
    clearRepoRootCache();
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true });
    clearRepoRootCache();
  });

  describe('discoverRuns', () => {
    test('returns empty array for missing directory', async () => {
      const runs = await discoverRuns(join(tempDir, 'nonexistent'));
      expect(runs).toEqual([]);
    });

    test('returns empty array for empty directory', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      const runs = await discoverRuns(runsDir);
      expect(runs).toEqual([]);
    });

    test('discovers runs sorted by date (newest first)', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      // Create runs with different dates
      await mkdir(join(runsDir, '2024-01-15-001'));
      await mkdir(join(runsDir, '2024-01-10-001'));
      await mkdir(join(runsDir, '2024-01-20-001'));

      const runs = await discoverRuns(runsDir);

      expect(runs).toHaveLength(3);
      expect(runs.at(0)?.id).toBe('2024-01-20-001');
      expect(runs.at(1)?.id).toBe('2024-01-15-001');
      expect(runs.at(2)?.id).toBe('2024-01-10-001');
    });

    test('sorts same-date runs by suffix (newest first)', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      // Create runs on same date with different suffixes
      await mkdir(join(runsDir, '2024-01-15-001'));
      await mkdir(join(runsDir, '2024-01-15-003'));
      await mkdir(join(runsDir, '2024-01-15-002'));

      const runs = await discoverRuns(runsDir);

      expect(runs).toHaveLength(3);
      expect(runs.at(0)?.id).toBe('2024-01-15-003');
      expect(runs.at(1)?.id).toBe('2024-01-15-002');
      expect(runs.at(2)?.id).toBe('2024-01-15-001');
    });

    test('sorts long format runs correctly', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      // Create runs with YYYY-MM-DD-HH-MM-SS format
      await mkdir(join(runsDir, '2024-01-15-10-30-00-001'));
      await mkdir(join(runsDir, '2024-01-15-10-30-00-002'));
      await mkdir(join(runsDir, '2024-01-15-11-00-00-001'));

      const runs = await discoverRuns(runsDir);

      expect(runs).toHaveLength(3);
      expect(runs.at(0)?.id).toBe('2024-01-15-11-00-00-001');
      expect(runs.at(1)?.id).toBe('2024-01-15-10-30-00-002');
      expect(runs.at(2)?.id).toBe('2024-01-15-10-30-00-001');
    });

    test('ignores files in runs directory', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      await mkdir(join(runsDir, '2024-01-15-001'));
      await writeFile(join(runsDir, 'not-a-run.txt'), 'ignored');

      const runs = await discoverRuns(runsDir);
      expect(runs).toHaveLength(1);
      expect(runs.at(0)?.id).toBe('2024-01-15-001');
    });

    test('includes iteration count from iter-*.log files', async () => {
      const runsDir = join(tempDir, 'runs');
      const runDir = join(runsDir, '2024-01-15-001');
      await mkdir(runDir, { recursive: true });

      await writeFile(join(runDir, 'iter-1.log'), 'log1');
      await writeFile(join(runDir, 'iter-2.log'), 'log2');
      await writeFile(join(runDir, 'iter-3.log'), 'log3');

      const runs = await discoverRuns(runsDir);
      expect(runs.at(0)?.iteration).toBe(3);
    });

    test('parses epic from progress.txt (Ralph format)', async () => {
      const runsDir = join(tempDir, 'runs');
      const runDir = join(runsDir, '20240115T103000Z-mac-user-1234-abcd');
      await mkdir(runDir, { recursive: true });

      // Real Ralph progress.txt format
      const progressContent = `# Ralph Progress Log
Run: 20240115T103000Z-mac-user-1234-abcd
Started: 2024-01-15T10:30:00Z
---
## 2024-01-15T10:30:05Z - iter 1
status=ready epic=fn-9 task=fn-9.1 reason=
claude_rc=0
verdict=
promise=CONTINUE
---
## 2024-01-15T10:35:00Z - iter 2
status=ready epic=fn-9 task=fn-9.2 reason=
claude_rc=0
verdict=
promise=CONTINUE
---`;
      await writeFile(join(runDir, 'progress.txt'), progressContent);

      const runs = await discoverRuns(runsDir);
      expect(runs).toHaveLength(1);
      expect(runs.at(0)?.epics).toEqual(['fn-9']);
    });

    test('handles real Ralph run ID format', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      // Real Ralph run IDs
      await mkdir(join(runsDir, '20240115T103000Z-mac-user-1234-abcd'));
      await mkdir(join(runsDir, '20240115T113000Z-mac-user-1234-efgh'));
      await mkdir(join(runsDir, '20240114T093000Z-mac-user-1234-ijkl'));

      const runs = await discoverRuns(runsDir);

      expect(runs).toHaveLength(3);
      // Lexicographic sort: newest first
      expect(runs.at(0)?.id).toBe('20240115T113000Z-mac-user-1234-efgh');
      expect(runs.at(1)?.id).toBe('20240115T103000Z-mac-user-1234-abcd');
      expect(runs.at(2)?.id).toBe('20240114T093000Z-mac-user-1234-ijkl');
    });
  });

  describe('isRunActive', () => {
    test('returns true when progress.txt is missing', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);

      const active = await isRunActive(runDir);
      expect(active).toBe(true);
    });

    test('returns true when progress.txt has no COMPLETE marker', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);
      await writeFile(join(runDir, 'progress.txt'), 'Task fn-1.1 in progress');

      const active = await isRunActive(runDir);
      expect(active).toBe(true);
    });

    test('returns false when progress.txt has promise=COMPLETE', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);
      await writeFile(
        join(runDir, 'progress.txt'),
        'promise=COMPLETE\nAll done'
      );

      const active = await isRunActive(runDir);
      expect(active).toBe(false);
    });

    test('returns false when progress.txt has <promise>COMPLETE</promise>', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);
      await writeFile(
        join(runDir, 'progress.txt'),
        '<promise>COMPLETE</promise>\nFinished'
      );

      const active = await isRunActive(runDir);
      expect(active).toBe(false);
    });
  });

  describe('getLatestRun', () => {
    test('returns undefined for empty array', () => {
      const latest = getLatestRun([]);
      expect(latest).toBeUndefined();
    });

    test('finds latest regardless of input order', () => {
      const runs = [
        {
          id: '2024-01-15-001',
          path: '/b',
          epics: [],
          active: false,
          iteration: 2,
        },
        {
          id: '2024-01-20-001',
          path: '/a',
          epics: [],
          active: true,
          iteration: 1,
        },
        {
          id: '2024-01-10-001',
          path: '/c',
          epics: [],
          active: false,
          iteration: 3,
        },
      ];

      const latest = getLatestRun(runs);
      expect(latest?.id).toBe('2024-01-20-001');
    });

    test('handles same-date runs with different suffixes', () => {
      const runs = [
        {
          id: '2024-01-15-001',
          path: '/a',
          epics: [],
          active: true,
          iteration: 1,
        },
        {
          id: '2024-01-15-003',
          path: '/b',
          epics: [],
          active: false,
          iteration: 2,
        },
        {
          id: '2024-01-15-002',
          path: '/c',
          epics: [],
          active: false,
          iteration: 3,
        },
      ];

      const latest = getLatestRun(runs);
      expect(latest?.id).toBe('2024-01-15-003');
    });
  });

  describe('getRunDetails', () => {
    test('returns detailed run information', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);
      await writeFile(join(runDir, 'progress.txt'), 'in progress');
      await writeFile(join(runDir, 'attempts.json'), '[]');
      await writeFile(join(runDir, 'iter-1.log'), 'log');

      const details = await getRunDetails(runDir);

      expect(details.id).toBe('2024-01-15-001');
      expect(details.path).toBe(runDir);
      expect(details.active).toBe(true);
      expect(details.iteration).toBe(1);
      expect(details.hasProgress).toBe(true);
      expect(details.hasAttempts).toBe(true);
      expect(details.hasBranches).toBe(false);
    });
  });

  describe('getReceiptStatus', () => {
    test('returns undefined for missing receipts', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);

      const status = await getReceiptStatus(runDir, 'fn-1.1');
      expect(status.plan).toBeUndefined();
      expect(status.impl).toBeUndefined();
    });

    test('returns true when plan receipt exists', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      const receiptsDir = join(runDir, 'receipts');
      await mkdir(receiptsDir, { recursive: true });
      await writeFile(join(receiptsDir, 'plan-fn-1.1.json'), '{}');

      const status = await getReceiptStatus(runDir, 'fn-1.1');
      expect(status.plan).toBe(true);
      expect(status.impl).toBeUndefined();
    });

    test('returns true when impl receipt exists', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      const receiptsDir = join(runDir, 'receipts');
      await mkdir(receiptsDir, { recursive: true });
      await writeFile(join(receiptsDir, 'impl-fn-1.1.json'), '{}');

      const status = await getReceiptStatus(runDir, 'fn-1.1');
      expect(status.plan).toBeUndefined();
      expect(status.impl).toBe(true);
    });

    test('returns both when both receipts exist', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      const receiptsDir = join(runDir, 'receipts');
      await mkdir(receiptsDir, { recursive: true });
      await writeFile(join(receiptsDir, 'plan-fn-1.1.json'), '{}');
      await writeFile(join(receiptsDir, 'impl-fn-1.1.json'), '{}');

      const status = await getReceiptStatus(runDir, 'fn-1.1');
      expect(status.plan).toBe(true);
      expect(status.impl).toBe(true);
    });

    test('rejects invalid taskId with path traversal', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);

      expect(getReceiptStatus(runDir, '../../../etc/passwd')).rejects.toThrow(
        'Invalid task ID'
      );
      expect(getReceiptStatus(runDir, 'fn-1/../../etc')).rejects.toThrow(
        'Invalid task ID'
      );
      expect(getReceiptStatus(runDir, 'invalid')).rejects.toThrow(
        'Invalid task ID'
      );
    });
  });

  describe('getBlockReason', () => {
    test('returns null when no block file exists', async () => {
      const reason = await getBlockReason('fn-1.1');
      expect(reason).toBeNull();
    });

    test('returns content from .flow/blocks/block-<task>.md', async () => {
      const blocksDir = join(tempDir, '.flow', 'blocks');
      await mkdir(blocksDir, { recursive: true });
      await writeFile(
        join(blocksDir, 'block-fn-1.1.md'),
        'Blocked: dependency failed'
      );

      // Temporarily change cwd
      const origCwd = process.cwd();
      process.chdir(tempDir);

      try {
        const reason = await getBlockReason('fn-1.1');
        expect(reason).toBe('Blocked: dependency failed');
      } finally {
        process.chdir(origCwd);
      }
    });

    test('returns content from run-specific block file', async () => {
      const runDir = join(tempDir, '2024-01-15-001');
      await mkdir(runDir);
      await writeFile(join(runDir, 'block-fn-1.1.md'), 'Run-specific block');

      const reason = await getBlockReason('fn-1.1', runDir);
      expect(reason).toBe('Run-specific block');
    });

    test('rejects invalid taskId with path traversal', async () => {
      expect(getBlockReason('../../../etc/passwd')).rejects.toThrow(
        'Invalid task ID'
      );
      expect(getBlockReason('fn-1/../etc')).rejects.toThrow('Invalid task ID');
      expect(getBlockReason('not-a-task')).rejects.toThrow('Invalid task ID');
    });
  });

  describe('validateRun', () => {
    test('throws error for non-existent run', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);
      await mkdir(join(runsDir, '2024-01-15-001'));

      expect(validateRun('2024-01-20-001', runsDir)).rejects.toThrow(
        "Run '2024-01-20-001' not found. Available: 2024-01-15-001"
      );
    });

    test('returns run and empty warnings when found', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);
      await mkdir(join(runsDir, '2024-01-15-001'));
      await writeFile(join(runsDir, '2024-01-15-001', 'progress.txt'), 'ok');

      const result = await validateRun('2024-01-15-001', runsDir);
      expect(result.run.id).toBe('2024-01-15-001');
      expect(result.warnings).toEqual([]);
    });

    test('returns warning for missing progress.txt', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);
      await mkdir(join(runsDir, '2024-01-15-001'));
      // No progress.txt file

      const result = await validateRun('2024-01-15-001', runsDir);
      expect(result.run.id).toBe('2024-01-15-001');
      expect(result.warnings).toHaveLength(1);
      expect(result.warnings[0]).toContain('corrupt');
    });

    test('lists available runs in error message', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);
      await mkdir(join(runsDir, '2024-01-15-001'));
      await mkdir(join(runsDir, '2024-01-10-001'));

      expect(validateRun('2024-01-20-001', runsDir)).rejects.toThrow(
        'Available: 2024-01-15-001, 2024-01-10-001'
      );
    });

    test('shows "none" when no runs available', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      expect(validateRun('2024-01-20-001', runsDir)).rejects.toThrow(
        'Available: none'
      );
    });

    test('rejects invalid runId with path traversal', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);

      expect(validateRun('../../../etc/passwd', runsDir)).rejects.toThrow(
        'Invalid run ID'
      );
      expect(validateRun('run/../escape', runsDir)).rejects.toThrow(
        'Invalid run ID'
      );
      expect(validateRun('run/subdir', runsDir)).rejects.toThrow(
        'Invalid run ID'
      );
    });

    test('accepts valid runId formats', async () => {
      const runsDir = join(tempDir, 'runs');
      await mkdir(runsDir);
      await mkdir(join(runsDir, '20240115T103000Z-mac-user-1234-abcd'));
      await writeFile(
        join(runsDir, '20240115T103000Z-mac-user-1234-abcd', 'progress.txt'),
        'ok'
      );

      const result = await validateRun(
        '20240115T103000Z-mac-user-1234-abcd',
        runsDir
      );
      expect(result.run.id).toBe('20240115T103000Z-mac-user-1234-abcd');
    });
  });
});
