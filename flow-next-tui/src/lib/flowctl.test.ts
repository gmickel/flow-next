import { describe, expect, it, beforeEach, beforeAll } from 'bun:test';

import {
  FlowctlError,
  FlowctlNotFoundError,
  getFlowctlPath,
  flowctl,
  getEpics,
  getTasks,
  getTaskSpec,
  getReadyTasks,
  getEpic,
  getTask,
  clearFlowctlCache,
  isFlowctlAvailable,
} from './flowctl';

// Check if flowctl is available (for integration tests)
let hasFlowctl = false;
let hasFlowDir = false;
// Computed: can run flowctl commands that need .flow/
let canRunFlowctlJson = false;

beforeAll(async () => {
  clearFlowctlCache();
  hasFlowctl = await isFlowctlAvailable();
  // Check .flow/ directory exists (for commands that need it)
  const file = Bun.file(`${process.cwd()}/.flow/config.json`);
  hasFlowDir = await file.exists();
  if (!hasFlowDir) {
    const parentFile = Bun.file(`${process.cwd()}/../.flow/config.json`);
    hasFlowDir = await parentFile.exists();
  }
  // Both flowctl and .flow/ needed for JSON commands
  canRunFlowctlJson = hasFlowctl && hasFlowDir;
});

beforeEach(() => {
  clearFlowctlCache();
});

describe('FlowctlError', () => {
  it('formats error message with args, exit code, stderr, and kind', () => {
    const fullCmd = ['python3', '/path/to/flowctl', 'show', 'fn-1', '--json'];
    const args = ['show', 'fn-1', '--json'];
    const error = new FlowctlError(fullCmd, args, 1, 'Epic not found', 'exec');
    expect(error.message).toBe(
      'flowctl show fn-1 --json failed (exit 1): Epic not found'
    );
    expect(error.fullCommand).toEqual(fullCmd);
    expect(error.args).toEqual(args);
    expect(error.exitCode).toBe(1);
    expect(error.output).toBe('Epic not found');
    expect(error.name).toBe('FlowctlError');
    expect(error.kind).toBe('exec');
  });

  it('defaults kind to exec', () => {
    const error = new FlowctlError(['cmd'], ['arg'], 1, 'err');
    expect(error.kind).toBe('exec');
  });

  it('supports parse kind for JSON failures', () => {
    const error = new FlowctlError(['cmd'], ['arg'], 0, 'parse error', 'parse');
    expect(error.kind).toBe('parse');
    expect(error.exitCode).toBe(0);
  });
});

describe('getFlowctlPath', () => {
  it('finds flowctl in repo plugins dir', async () => {
    if (!hasFlowctl) return; // Skip if flowctl not available
    const path = await getFlowctlPath();
    expect(path).toContain('flowctl');
  });

  it('caches the path after first lookup', async () => {
    if (!hasFlowctl) return; // Skip if flowctl not available
    const path1 = await getFlowctlPath();
    const path2 = await getFlowctlPath();
    expect(path1).toBe(path2);
  });

  it('throws FlowctlNotFoundError when not found', async () => {
    clearFlowctlCache();
    try {
      await getFlowctlPath('/tmp/nonexistent-flowctl-test-dir');
      expect.unreachable('Should have thrown');
    } catch (err) {
      expect(err instanceof FlowctlNotFoundError).toBe(true);
      const notFoundErr = err as FlowctlNotFoundError;
      expect(notFoundErr.message).toContain('flowctl not found');
      expect(notFoundErr.message).toContain('/flow-next:setup');
      expect(notFoundErr.startDir).toBe('/tmp/nonexistent-flowctl-test-dir');
      expect(Array.isArray(notFoundErr.searchedPaths)).toBe(true);
      expect(notFoundErr.searchedPaths.length).toBeGreaterThan(0);
    } finally {
      clearFlowctlCache();
    }
  });
});

describe('isFlowctlAvailable', () => {
  it('returns boolean indicating availability', async () => {
    const available = await isFlowctlAvailable();
    expect(typeof available).toBe('boolean');
  });
});

describe('flowctl', () => {
  it('parses JSON output from flowctl command', async () => {
    if (!canRunFlowctlJson) return;
    const result = await flowctl<{ success: boolean; epics: unknown[] }>([
      'epics',
      '--json',
    ]);
    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('epics');
  });
});

describe('getEpics', () => {
  it('returns list of epics with list-item fields', async () => {
    if (!canRunFlowctlJson) return;
    const epics = await getEpics();
    expect(Array.isArray(epics)).toBe(true);
    if (epics.length > 0) {
      const first = epics[0];
      expect(first).toHaveProperty('id');
      expect(first).toHaveProperty('title');
      expect(first).toHaveProperty('status');
      expect(first).toHaveProperty('tasks');
      expect(first).toHaveProperty('done');
      expect(typeof first?.tasks).toBe('number');
      expect(typeof first?.done).toBe('number');
    }
  });
});

describe('getTasks', () => {
  it('returns tasks for an epic', async () => {
    if (!canRunFlowctlJson) return;
    const epics = await getEpics();
    if (epics.length === 0) return;

    const epicId = epics[0]?.id;
    if (!epicId) return;

    const tasks = await getTasks(epicId);
    expect(Array.isArray(tasks)).toBe(true);
    if (tasks.length > 0) {
      const first = tasks[0];
      expect(first).toHaveProperty('id');
      expect(first).toHaveProperty('title');
      expect(first).toHaveProperty('status');
      expect(first).toHaveProperty('epic');
    }
  });

  it('returns empty array for non-existent epic', async () => {
    if (!canRunFlowctlJson) return;
    const tasks = await getTasks('fn-99999');
    expect(Array.isArray(tasks)).toBe(true);
    expect(tasks.length).toBe(0);
  });
});

describe('getTaskSpec', () => {
  it('returns markdown spec for a task', async () => {
    if (!canRunFlowctlJson) return;
    const epics = await getEpics();
    if (epics.length === 0) return;

    const epicId = epics[0]?.id;
    if (!epicId) return;

    const tasks = await getTasks(epicId);
    if (tasks.length === 0) return;

    const taskId = tasks[0]?.id;
    if (!taskId) return;

    const spec = await getTaskSpec(taskId);
    expect(typeof spec).toBe('string');
    expect(spec.length).toBeGreaterThan(0);
  });

  it('throws FlowctlError for invalid task', async () => {
    if (!canRunFlowctlJson) return;
    try {
      await getTaskSpec('fn-99999.999');
      expect.unreachable('Should have thrown');
    } catch (error) {
      expect(error instanceof FlowctlError).toBe(true);
      expect((error as FlowctlError).kind).toBe('exec');
    }
  });
});

describe('getReadyTasks', () => {
  it('returns ready/in_progress/blocked categorization', async () => {
    if (!canRunFlowctlJson) return;
    const epics = await getEpics();
    if (epics.length === 0) return;

    const epicId = epics[0]?.id;
    if (!epicId) return;

    const result = await getReadyTasks(epicId);
    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('ready');
    expect(result).toHaveProperty('in_progress');
    expect(result).toHaveProperty('blocked');
    expect(Array.isArray(result.ready)).toBe(true);
    expect(Array.isArray(result.in_progress)).toBe(true);
    expect(Array.isArray(result.blocked)).toBe(true);
  });
});

describe('getEpic', () => {
  it('returns full epic details', async () => {
    if (!canRunFlowctlJson) return;
    const epics = await getEpics();
    if (epics.length === 0) return;

    const epicId = epics[0]?.id;
    if (!epicId) return;

    const epic = await getEpic(epicId);
    expect(epic).toHaveProperty('id');
    expect(epic).toHaveProperty('title');
    expect(epic).toHaveProperty('status');
    expect(epic).toHaveProperty('tasks');
    expect(epic).not.toHaveProperty('success');
  });
});

describe('getTask', () => {
  it('returns task details', async () => {
    if (!canRunFlowctlJson) return;
    const epics = await getEpics();
    if (epics.length === 0) return;

    const epicId = epics[0]?.id;
    if (!epicId) return;

    const tasks = await getTasks(epicId);
    if (tasks.length === 0) return;

    const taskId = tasks[0]?.id;
    if (!taskId) return;

    const task = await getTask(taskId);
    expect(task).toHaveProperty('id');
    expect(task).toHaveProperty('title');
    expect(task).toHaveProperty('status');
    expect(task).toHaveProperty('epic');
    expect(task).not.toHaveProperty('success');
  });
});
