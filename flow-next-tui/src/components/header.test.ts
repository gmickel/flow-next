import { describe, expect, test } from 'bun:test';

import type { Epic, Task } from '../lib/types.ts';

import { stripAnsi, visibleWidth } from '../lib/render.ts';
import { darkTheme } from '../themes/dark.ts';
import {
  ASCII_STATE_ICONS,
  Header,
  type HeaderProps,
  STATE_ICONS,
} from './header.ts';

/** Create a mock task for testing */
function mockTask(overrides?: Partial<Task>): Task {
  return {
    id: 'fn-9.1',
    epic: 'fn-9',
    title: 'Test task title',
    status: 'in_progress',
    depends_on: [],
    spec_path: '.flow/tasks/fn-9.1.md',
    priority: null,
    assignee: null,
    claim_note: '',
    claimed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

/** Create a mock epic for testing */
function mockEpic(overrides?: Partial<Epic>): Epic {
  return {
    id: 'fn-9',
    title: 'Test epic title',
    status: 'open',
    branch_name: 'feature/test',
    spec_path: '.flow/specs/fn-9.md',
    next_task: 2,
    depends_on_epics: [],
    plan_review_status: 'unknown',
    plan_reviewed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    tasks: [],
    ...overrides,
  };
}

/** Create default header props */
function defaultProps(overrides?: Partial<HeaderProps>): HeaderProps {
  return {
    state: 'running',
    iteration: 1,
    taskProgress: { done: 3, total: 7 },
    elapsed: 125, // 2:05
    theme: darkTheme,
    ...overrides,
  };
}

describe('Header', () => {
  test('renders two rows', () => {
    const header = new Header(defaultProps());
    const lines = header.render(80);

    expect(lines).toHaveLength(2);
  });

  test('row 1 contains status icon for running state', () => {
    const header = new Header(defaultProps({ state: 'running' }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain(STATE_ICONS.running);
  });

  test('row 1 contains status icon for idle state', () => {
    const header = new Header(defaultProps({ state: 'idle' }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain(STATE_ICONS.idle);
  });

  test('row 1 contains status icon for complete state', () => {
    const header = new Header(defaultProps({ state: 'complete' }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain(STATE_ICONS.complete);
  });

  test('row 1 contains flow-next branding', () => {
    const header = new Header(defaultProps());
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('flow-next');
  });

  test('row 1 contains timer in MM:SS format', () => {
    const header = new Header(defaultProps({ elapsed: 125 })); // 2:05
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('02:05');
  });

  test('row 1 shows task in brackets when provided', () => {
    const header = new Header(
      defaultProps({
        task: mockTask({ id: 'fn-9.3', title: 'Add validation' }),
      })
    );
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('「');
    expect(stripped).toContain('fn-9.3');
    expect(stripped).toContain('Add validation');
    expect(stripped).toContain('」');
  });

  test('row 2 contains iteration number', () => {
    const header = new Header(defaultProps({ iteration: 3 }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('Iter #3');
  });

  test('row 2 contains task progress', () => {
    const header = new Header(
      defaultProps({ taskProgress: { done: 5, total: 10 } })
    );
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('5/10 tasks');
  });

  test('row 2 shows epic info when provided', () => {
    const header = new Header(
      defaultProps({
        epic: mockEpic({ id: 'fn-9', title: 'flow-next-tui MVP' }),
      })
    );
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('fn-9');
    expect(stripped).toContain('flow-next-tui MVP');
  });

  test('uses ASCII icons when useAscii is true', () => {
    const header = new Header(
      defaultProps({ state: 'running', useAscii: true })
    );
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain(ASCII_STATE_ICONS.running);
    expect(stripped).not.toContain(STATE_ICONS.running);
  });

  test('truncates long task title', () => {
    const longTitle =
      'This is a very long task title that should be truncated when the width is limited';
    const header = new Header(
      defaultProps({
        task: mockTask({ title: longTitle }),
      })
    );
    const lines = header.render(60);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('…');
    expect(stripped.length).toBeLessThanOrEqual(60);
  });

  test('truncates long epic title', () => {
    const longTitle =
      'This is a very long epic title that should be truncated when the width is limited';
    const header = new Header(
      defaultProps({
        epic: mockEpic({ title: longTitle }),
      })
    );
    const lines = header.render(60);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('…');
    expect(stripped.length).toBeLessThanOrEqual(60);
  });

  test('update() modifies state', () => {
    const header = new Header(defaultProps({ state: 'running' }));

    header.update({ state: 'complete', elapsed: 200 });
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain(STATE_ICONS.complete);
    expect(stripped).toContain('03:20'); // 200 seconds
  });

  test('handles zero elapsed time', () => {
    const header = new Header(defaultProps({ elapsed: 0 }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('00:00');
  });

  test('handles large elapsed time', () => {
    const header = new Header(defaultProps({ elapsed: 3661 })); // 61:01
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('61:01');
  });

  test('renders without task or epic', () => {
    const header = new Header(defaultProps());
    const lines = header.render(80);

    expect(lines).toHaveLength(2);
    const stripped0 = stripAnsi(lines[0]!);
    const stripped1 = stripAnsi(lines[1]!);
    expect(stripped0).toContain('flow-next');
    expect(stripped1).toContain('Iter #');
  });

  test('rows respect width constraint', () => {
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
      })
    );
    const width = 50;
    const lines = header.render(width);

    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(width);
    }
  });

  test('handleInput does nothing (no-op)', () => {
    const header = new Header(defaultProps());
    // Should not throw
    header.handleInput('j');
    header.handleInput('q');
  });

  test('invalidate does nothing (no-op)', () => {
    const header = new Header(defaultProps());
    // Should not throw
    header.invalidate();
  });

  test('narrow width still renders', () => {
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
      })
    );
    const lines = header.render(20);

    expect(lines).toHaveLength(2);
    // Should not crash or produce lines exceeding width
    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(20);
    }
  });

  test('very narrow width=10 respects constraint', () => {
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
      })
    );
    const width = 10;
    const lines = header.render(width);

    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(width);
    }
  });

  test('very narrow width=5 respects constraint', () => {
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
      })
    );
    const width = 5;
    const lines = header.render(width);

    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(width);
    }
  });

  test('width=0 returns empty or minimal output', () => {
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
      })
    );
    const lines = header.render(0);

    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(0);
    }
  });

  test('width without task/epic still respects constraint at narrow width', () => {
    const header = new Header(defaultProps());
    const width = 10;
    const lines = header.render(width);

    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(width);
    }
  });

  test('width=7 (timerWidth+2) edge case respects constraint and shows full timer', () => {
    // Timer is 5 chars (MM:SS), so width=7 is timerWidth+2
    // This tests the minWidth path boundary
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
        elapsed: 125, // 02:05 = 5 chars
      })
    );
    const width = 7;
    const lines = header.render(width);

    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(width);
    }
    // Timer should be fully intact when width > timerWidth
    expect(stripAnsi(lines[0]!)).toContain('02:05');
  });

  test('width=6 (timerWidth+1) boundary respects constraint', () => {
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
        elapsed: 125,
      })
    );
    const width = 6;
    const lines = header.render(width);

    expect(lines).toHaveLength(2);
    for (const line of lines) {
      expect(visibleWidth(line)).toBeLessThanOrEqual(width);
    }
  });
});
