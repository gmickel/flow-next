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
  test('renders three rows (bordered)', () => {
    const header = new Header(defaultProps());
    const lines = header.render(80);

    expect(lines).toHaveLength(3);
  });

  test('top border contains flow-next branding', () => {
    const header = new Header(defaultProps());
    const lines = header.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('flow-next');
    expect(stripped).toContain('╭'); // rounded corner
  });

  test('content row contains status icon for running state', () => {
    const header = new Header(defaultProps({ state: 'running' }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain(STATE_ICONS.running);
    expect(stripped).toContain('Running');
  });

  test('content row contains status icon for idle state', () => {
    const header = new Header(defaultProps({ state: 'idle' }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain(STATE_ICONS.idle);
    expect(stripped).toContain('Idle');
  });

  test('content row contains status icon for complete state', () => {
    const header = new Header(defaultProps({ state: 'complete' }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain(STATE_ICONS.complete);
    expect(stripped).toContain('Done');
  });

  test('content row contains timer in MM:SS format', () => {
    const header = new Header(defaultProps({ elapsed: 125 })); // 2:05
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('02:05');
  });

  test('content row contains iteration number', () => {
    const header = new Header(defaultProps({ iteration: 3 }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('#3');
  });

  test('content row contains task progress', () => {
    const header = new Header(
      defaultProps({ taskProgress: { done: 5, total: 10 } })
    );
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('5');
    expect(stripped).toContain('10');
  });

  test('content row shows task id when provided', () => {
    const header = new Header(
      defaultProps({
        task: mockTask({ id: 'fn-9.3' }),
      })
    );
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('fn-9.3');
  });

  test('uses ASCII icons when useAscii is true', () => {
    const header = new Header(
      defaultProps({ state: 'running', useAscii: true })
    );
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain(ASCII_STATE_ICONS.running);
    expect(stripped).not.toContain(STATE_ICONS.running);
  });

  test('update() modifies state', () => {
    const header = new Header(defaultProps({ state: 'running' }));

    header.update({ state: 'complete', elapsed: 200 });
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain(STATE_ICONS.complete);
    expect(stripped).toContain('03:20'); // 200 seconds
  });

  test('handles zero elapsed time', () => {
    const header = new Header(defaultProps({ elapsed: 0 }));
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('00:00');
  });

  test('handles large elapsed time with HH:MM:SS format', () => {
    const header = new Header(defaultProps({ elapsed: 3661 })); // 1:01:01
    const lines = header.render(80);

    const stripped = stripAnsi(lines[1]!);
    expect(stripped).toContain('01:01:01');
  });

  test('renders without task or epic', () => {
    const header = new Header(defaultProps());
    const lines = header.render(80);

    expect(lines).toHaveLength(3);
    const stripped0 = stripAnsi(lines[0]!);
    const stripped1 = stripAnsi(lines[1]!);
    expect(stripped0).toContain('flow-next');
    expect(stripped1).toContain('Iter');
  });

  test('rows respect width constraint', () => {
    const header = new Header(
      defaultProps({
        task: mockTask(),
        epic: mockEpic(),
      })
    );
    const width = 80;
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

  test('narrow width returns minimal output', () => {
    const header = new Header(defaultProps());
    const lines = header.render(15);

    // Width < 20 returns minimal output
    expect(lines.length).toBeGreaterThanOrEqual(1);
  });

  test('bottom border has proper corners', () => {
    const header = new Header(defaultProps());
    const lines = header.render(80);

    const stripped = stripAnsi(lines[2]!);
    expect(stripped).toContain('╰');
    expect(stripped).toContain('╯');
  });

  test('ASCII mode uses ASCII borders', () => {
    const header = new Header(defaultProps({ useAscii: true }));
    const lines = header.render(80);

    const stripped0 = stripAnsi(lines[0]!);
    const stripped2 = stripAnsi(lines[2]!);
    expect(stripped0).toContain('+');
    expect(stripped2).toContain('+');
  });
});
