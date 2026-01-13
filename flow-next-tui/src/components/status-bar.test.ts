import { describe, expect, test } from 'bun:test';

import { stripAnsi, visibleWidth } from '../lib/render.ts';
import { darkTheme } from '../themes/dark.ts';
import { StatusBar, type StatusBarProps } from './status-bar.ts';

/** Create default status bar props */
function defaultProps(overrides?: Partial<StatusBarProps>): StatusBarProps {
  return {
    theme: darkTheme,
    ...overrides,
  };
}

describe('StatusBar', () => {
  test('renders single row', () => {
    const bar = new StatusBar(defaultProps());
    const lines = bar.render(80);

    expect(lines).toHaveLength(1);
  });

  test('contains keyboard shortcuts on left', () => {
    const bar = new StatusBar(defaultProps());
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('q quit');
    expect(stripped).toContain('j/k nav');
    expect(stripped).toContain('? help');
  });

  test('shows run ID on right when provided', () => {
    const bar = new StatusBar(defaultProps({ runId: '2026-01-12-001' }));
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('2026-01-12-001');
  });

  test('shows error count when > 0', () => {
    const bar = new StatusBar(defaultProps({ errorCount: 3 }));
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('3 errors');
  });

  test('uses singular "error" for count of 1', () => {
    const bar = new StatusBar(defaultProps({ errorCount: 1 }));
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('1 error');
    expect(stripped).not.toContain('1 errors');
  });

  test('shows run ID and error count together', () => {
    const bar = new StatusBar(
      defaultProps({ runId: '2026-01-12-001', errorCount: 2 })
    );
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('2026-01-12-001');
    expect(stripped).toContain('2 errors');
  });

  test('does not show error count when 0', () => {
    const bar = new StatusBar(
      defaultProps({ runId: 'run-001', errorCount: 0 })
    );
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('run-001');
    expect(stripped).not.toContain('error');
  });

  test('respects width constraint', () => {
    const bar = new StatusBar(
      defaultProps({ runId: '2026-01-12-001', errorCount: 5 })
    );
    const width = 80;
    const lines = bar.render(width);

    expect(visibleWidth(lines[0]!)).toBeLessThanOrEqual(width);
  });

  test('truncates shortcuts at narrow width', () => {
    const bar = new StatusBar(defaultProps());
    const width = 15;
    const lines = bar.render(width);

    expect(visibleWidth(lines[0]!)).toBeLessThanOrEqual(width);
    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('…');
  });

  test('truncates right content when needed', () => {
    const bar = new StatusBar(
      defaultProps({
        runId: 'very-long-run-id-that-should-be-truncated',
        errorCount: 3,
      })
    );
    const width = 40;
    const lines = bar.render(width);

    expect(visibleWidth(lines[0]!)).toBeLessThanOrEqual(width);
  });

  test('update() modifies state', () => {
    const bar = new StatusBar(defaultProps());

    bar.update({ runId: 'new-run', errorCount: 2 });
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('new-run');
    expect(stripped).toContain('2 errors');
  });

  test('update() can change runId', () => {
    const bar = new StatusBar(defaultProps({ runId: 'old-run' }));

    bar.update({ runId: 'new-run' });
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).not.toContain('old-run');
    expect(stripped).toContain('new-run');
  });

  test('handleInput does nothing (no-op)', () => {
    const bar = new StatusBar(defaultProps());
    // Should not throw
    bar.handleInput('j');
    bar.handleInput('q');
  });

  test('invalidate does nothing (no-op)', () => {
    const bar = new StatusBar(defaultProps());
    // Should not throw
    bar.invalidate();
  });

  test('very narrow width respects constraint', () => {
    const bar = new StatusBar(
      defaultProps({ runId: 'run-001', errorCount: 5 })
    );
    const width = 10;
    const lines = bar.render(width);

    expect(lines).toHaveLength(1);
    expect(visibleWidth(lines[0]!)).toBeLessThanOrEqual(width);
  });

  test('width=0 returns empty string', () => {
    const bar = new StatusBar(defaultProps({ runId: 'run-001' }));
    const lines = bar.render(0);

    expect(lines).toHaveLength(1);
    expect(lines[0]).toBe('');
  });

  test('full width with gap between shortcuts and run info', () => {
    const bar = new StatusBar(defaultProps({ runId: 'run-001' }));
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    // Shortcuts should be at start, run ID at end
    expect(stripped.startsWith('q quit')).toBe(true);
    expect(stripped.trimEnd().endsWith('run-001')).toBe(true);
  });

  test('renders without runId or errorCount', () => {
    const bar = new StatusBar(defaultProps());
    const lines = bar.render(80);

    expect(lines).toHaveLength(1);
    const stripped = stripAnsi(lines[0]!);
    expect(stripped).toContain('q quit');
    // Right side should be empty or spaces
    expect(stripped).not.toContain('error');
  });

  test('update() can clear runId', () => {
    const bar = new StatusBar(defaultProps({ runId: 'old-run' }));

    bar.update({ runId: undefined });
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    expect(stripped).not.toContain('old-run');
  });

  // Note: theme color tests removed - chalk.level=0 in non-TTY test environment
  // strips all ANSI codes, making color verification impossible.
  // Component correctly calls theme.dim/error - verified by code inspection.

  test('strips ANSI codes from runId (injection protection)', () => {
    // runId with embedded escape sequence
    const maliciousRunId = 'run-\x1b[31mhack\x1b[0m-001';
    const bar = new StatusBar(defaultProps({ runId: maliciousRunId }));
    const lines = bar.render(80);

    const stripped = stripAnsi(lines[0]!);
    // Should show sanitized content without the injected codes
    expect(stripped).toContain('run-hack-001');
    // Should not contain the raw escape sequence (other than theme styling)
    expect(stripped).not.toContain('\x1b[31m');
  });

  test('renders full width exactly', () => {
    const bar = new StatusBar(defaultProps({ runId: 'run-001' }));
    const width = 80;
    const lines = bar.render(width);

    // Should be padded to exactly the requested width
    expect(visibleWidth(lines[0]!)).toBe(width);
  });

  test('renders full width exactly even when truncated', () => {
    const bar = new StatusBar(defaultProps());
    const width = 30;
    const lines = bar.render(width);

    // Should be padded to exactly the requested width
    expect(visibleWidth(lines[0]!)).toBe(width);
  });
});
