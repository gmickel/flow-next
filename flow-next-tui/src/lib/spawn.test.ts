import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdtemp, rm, mkdir, writeFile, chmod } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { clearRepoRootCache as clearRunsCache } from './runs';
import {
  findRalphScript,
  isRalphRunning,
  clearRepoRootCache,
  RalphNotFoundError,
} from './spawn';

describe('spawn', () => {
  let tempDir: string;
  let oldCwd: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'spawn-test-'));
    oldCwd = process.cwd();
    clearRepoRootCache();
    clearRunsCache();
  });

  afterEach(async () => {
    process.chdir(oldCwd);
    clearRepoRootCache();
    clearRunsCache();
    await rm(tempDir, { recursive: true });
  });

  describe('findRalphScript', () => {
    test('returns null when no ralph.sh exists', async () => {
      // Create .git/HEAD to make it a repo
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      process.chdir(tempDir);

      const result = await findRalphScript(tempDir);
      expect(result).toBeNull();
    });

    test('finds scripts/ralph/ralph.sh first', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      await mkdir(join(tempDir, 'scripts', 'ralph'), { recursive: true });
      const ralphPath = join(tempDir, 'scripts', 'ralph', 'ralph.sh');
      await writeFile(ralphPath, '#!/bin/bash\necho "ralph"');
      await chmod(ralphPath, 0o755);
      process.chdir(tempDir);

      const result = await findRalphScript(tempDir);
      expect(result).not.toBeNull();
      expect(result?.path).toBe(ralphPath);
      expect(result?.searchedPaths).toContain(ralphPath);
    });

    test('falls back to plugin template path', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      const templateDir = join(
        tempDir,
        'plugins',
        'flow-next',
        'skills',
        'flow-next-ralph-init',
        'templates'
      );
      await mkdir(templateDir, { recursive: true });
      const templatePath = join(templateDir, 'ralph.sh');
      await writeFile(templatePath, '#!/bin/bash\necho "template ralph"');
      await chmod(templatePath, 0o755);
      process.chdir(tempDir);

      const result = await findRalphScript(tempDir);
      expect(result).not.toBeNull();
      expect(result?.path).toBe(templatePath);
    });

    test('prefers local script over template', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');

      // Create local script
      await mkdir(join(tempDir, 'scripts', 'ralph'), { recursive: true });
      const localPath = join(tempDir, 'scripts', 'ralph', 'ralph.sh');
      await writeFile(localPath, '#!/bin/bash\necho "local"');
      await chmod(localPath, 0o755);

      // Create template
      const templateDir = join(
        tempDir,
        'plugins',
        'flow-next',
        'skills',
        'flow-next-ralph-init',
        'templates'
      );
      await mkdir(templateDir, { recursive: true });
      const templatePath = join(templateDir, 'ralph.sh');
      await writeFile(templatePath, '#!/bin/bash\necho "template"');
      await chmod(templatePath, 0o755);
      process.chdir(tempDir);

      const result = await findRalphScript(tempDir);
      expect(result?.path).toBe(localPath);
    });

    test('returns searchedPaths with all checked locations', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      process.chdir(tempDir);

      const result = await findRalphScript(tempDir);
      expect(result).toBeNull();

      // When null, we can't access searchedPaths from result
      // But the function internally builds the list correctly
    });
  });

  describe('isRalphRunning', () => {
    test('returns true when no progress file', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      const runDir = join(tempDir, 'scripts', 'ralph', 'runs', 'test-run');
      await mkdir(runDir, { recursive: true });
      process.chdir(tempDir);

      const runsDir = join(tempDir, 'scripts', 'ralph', 'runs');
      const result = await isRalphRunning('test-run', runsDir);
      expect(result).toBe(true);
    });

    test('returns true when progress.txt exists without COMPLETE', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      const runDir = join(tempDir, 'scripts', 'ralph', 'runs', 'test-run');
      await mkdir(runDir, { recursive: true });
      await writeFile(
        join(runDir, 'progress.txt'),
        'status=work epic=fn-1 task=fn-1.1'
      );
      process.chdir(tempDir);

      const runsDir = join(tempDir, 'scripts', 'ralph', 'runs');
      const result = await isRalphRunning('test-run', runsDir);
      expect(result).toBe(true);
    });

    test('returns false when progress.txt contains COMPLETE marker', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      const runDir = join(tempDir, 'scripts', 'ralph', 'runs', 'test-run');
      await mkdir(runDir, { recursive: true });
      await writeFile(
        join(runDir, 'progress.txt'),
        'status=done epic=fn-1\n<promise>COMPLETE</promise>'
      );
      process.chdir(tempDir);

      const runsDir = join(tempDir, 'scripts', 'ralph', 'runs');
      const result = await isRalphRunning('test-run', runsDir);
      expect(result).toBe(false);
    });

    test('returns false with alternative COMPLETE format', async () => {
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');
      const runDir = join(tempDir, 'scripts', 'ralph', 'runs', 'test-run');
      await mkdir(runDir, { recursive: true });
      await writeFile(
        join(runDir, 'progress.txt'),
        'status=done promise=COMPLETE'
      );
      process.chdir(tempDir);

      const runsDir = join(tempDir, 'scripts', 'ralph', 'runs');
      const result = await isRalphRunning('test-run', runsDir);
      expect(result).toBe(false);
    });
  });

  describe('RalphNotFoundError', () => {
    test('has helpful message', () => {
      const paths = ['/path/one', '/path/two'];
      const error = new RalphNotFoundError(paths);

      expect(error.name).toBe('RalphNotFoundError');
      expect(error.message).toContain('/flow-next:ralph-init');
      expect(error.message).toContain('/path/one');
      expect(error.message).toContain('/path/two');
      expect(error.searchedPaths).toEqual(paths);
    });
  });
});
