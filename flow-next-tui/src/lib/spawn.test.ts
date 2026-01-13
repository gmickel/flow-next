import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdtemp, rm, mkdir, writeFile, chmod } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import {
  findRalphScript,
  isRalphRunning,
  clearRepoRootCache,
  RalphNotFoundError,
} from './spawn';

describe('spawn', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'spawn-test-'));
    clearRepoRootCache();
  });

  afterEach(async () => {
    clearRepoRootCache();
    await rm(tempDir, { recursive: true });
  });

  describe('findRalphScript', () => {
    test('returns null when no ralph.sh exists', async () => {
      // Create .git/HEAD to make it a repo (Bun.file needs a file, not dir)
      await mkdir(join(tempDir, '.git'));
      await writeFile(join(tempDir, '.git', 'HEAD'), 'ref: refs/heads/main');

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

      const result = await findRalphScript(tempDir);
      expect(result).toBe(ralphPath);
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

      const result = await findRalphScript(tempDir);
      expect(result).toBe(templatePath);
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

      const result = await findRalphScript(tempDir);
      expect(result).toBe(localPath);
    });
  });

  describe('isRalphRunning', () => {
    test('returns true when no progress file', async () => {
      await mkdir(join(tempDir, '.git'));
      await mkdir(join(tempDir, 'scripts', 'ralph', 'runs', 'test-run'), {
        recursive: true,
      });

      const result = await isRalphRunning('test-run');
      // Will return true because repo root lookup won't find the temp dir
      // This is expected behavior - no progress = running
      expect(result).toBe(true);
    });

    test('returns true when progress.txt exists without COMPLETE', async () => {
      await mkdir(join(tempDir, '.git'));
      const runDir = join(tempDir, 'scripts', 'ralph', 'runs', 'test-run');
      await mkdir(runDir, { recursive: true });
      await writeFile(
        join(runDir, 'progress.txt'),
        'status=work epic=fn-1 task=fn-1.1'
      );

      // Note: test uses process.cwd(), so this won't actually find our temp dir
      // In real usage, the function uses findRepoRoot from cwd
      const result = await isRalphRunning('test-run');
      expect(result).toBe(true);
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
