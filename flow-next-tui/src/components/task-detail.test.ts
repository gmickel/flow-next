import { describe, expect, test } from 'bun:test';

import type { ReceiptStatus } from '../lib/runs.ts';
import type { Task } from '../lib/types.ts';

import { stripAnsi, visibleWidth } from '../lib/render.ts';
import { darkTheme } from '../themes/dark.ts';
import { TaskDetail } from './task-detail.ts';
import { STATUS_ICONS, ASCII_ICONS } from './task-list.ts';

/** Create a mock task for testing */
function mockTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'fn-1.1',
    epic: 'fn-1',
    title: 'Test task',
    status: 'todo',
    depends_on: [],
    spec_path: '.flow/tasks/fn-1.1.md',
    priority: null,
    assignee: null,
    claim_note: '',
    claimed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('TaskDetail', () => {
  describe('rendering', () => {
    test('renders task title with status icon', () => {
      const task = mockTask({ title: 'Add validation' });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(50);

      expect(lines.length).toBeGreaterThan(0);
      // Line 0 is panel header, content starts at line 1+
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(STATUS_ICONS.todo);
      expect(allText).toContain('Add validation');
    });

    test('renders metadata line with id and status', () => {
      const task = mockTask({ id: 'fn-2.5', status: 'in_progress' });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(60);

      // Content is wrapped in borders, search all text
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('fn-2.5');
      expect(allText).toContain('in progress');
    });

    test('renders receipt indicators', () => {
      const task = mockTask();
      const receipts: ReceiptStatus = { plan: true, impl: false };
      const detail = new TaskDetail({
        task,
        spec: '',
        receipts,
        theme: darkTheme,
      });
      const lines = detail.render(50);

      // Content is wrapped in borders, search all text
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Plan');
      expect(allText).toContain('Impl');
      // Has both check and cross
      expect(allText).toContain('✓');
      expect(allText).toContain('✗');
    });

    test('renders receipt with dash for undefined status', () => {
      const task = mockTask();
      const receipts: ReceiptStatus = { plan: true }; // impl undefined
      const detail = new TaskDetail({
        task,
        spec: '',
        receipts,
        theme: darkTheme,
      });
      const lines = detail.render(50);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Plan');
      expect(allText).toContain('✓');
      expect(allText).toContain('-'); // dash for undefined impl
    });

    test('renders done task with success icon', () => {
      const task = mockTask({ status: 'done' });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(50);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(STATUS_ICONS.done);
    });

    test('renders blocked task with blocked icon', () => {
      const task = mockTask({ status: 'blocked' });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(50);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(STATUS_ICONS.blocked);
    });

    test('renders block reason for blocked tasks', () => {
      const task = mockTask({ status: 'blocked' });
      const blockReason = 'Waiting for fn-1.2 to complete';
      const detail = new TaskDetail({
        task,
        spec: '',
        blockReason,
        theme: darkTheme,
      });
      const lines = detail.render(60);

      // Should have block header and reason
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Blocked');
      expect(allText).toContain('Waiting for fn-1.2');
    });

    test('does not render block reason for non-blocked tasks', () => {
      const task = mockTask({ status: 'todo' });
      const blockReason = 'This should not appear';
      const detail = new TaskDetail({
        task,
        spec: '',
        blockReason,
        theme: darkTheme,
      });
      const lines = detail.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).not.toContain('This should not appear');
    });

    test('renders markdown spec content', () => {
      const task = mockTask();
      const spec = '## Description\n\nThis is the task description.';
      const detail = new TaskDetail({ task, spec, theme: darkTheme });
      const lines = detail.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Description');
      expect(allText).toContain('task description');
    });

    test('ASCII mode uses text icons', () => {
      const task = mockTask({ status: 'done' });
      const detail = new TaskDetail({
        task,
        spec: '',
        theme: darkTheme,
        useAscii: true,
      });
      const lines = detail.render(50);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(ASCII_ICONS.done);
    });

    test('ASCII mode uses Y/N for receipts', () => {
      const task = mockTask();
      const receipts: ReceiptStatus = { plan: true, impl: false };
      const detail = new TaskDetail({
        task,
        spec: '',
        receipts,
        theme: darkTheme,
        useAscii: true,
      });
      const lines = detail.render(50);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Y');
      expect(allText).toContain('N');
    });

    test('truncates long title with ellipsis', () => {
      const task = mockTask({
        title:
          'This is a very long task title that should be truncated at narrow width',
      });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(30);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('…');
      // All lines should respect width
      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(30);
      }
    });

    test('handles empty spec', () => {
      const task = mockTask();
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(50);

      // Should still render header
      expect(lines.length).toBeGreaterThanOrEqual(3); // title, meta, receipts
    });

    test('handles zero width', () => {
      const task = mockTask();
      const detail = new TaskDetail({ task, spec: '# Test', theme: darkTheme });
      const lines = detail.render(0);

      expect(lines).toHaveLength(0);
    });

    test('lines respect width constraint', () => {
      const task = mockTask({
        title: 'A very long title that exceeds the width',
      });
      const spec =
        '## Long heading that is quite long\n\nSome paragraph content here.';
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      for (const width of [20, 30, 40, 50]) {
        const lines = detail.render(width);
        for (const line of lines) {
          expect(visibleWidth(line)).toBeLessThanOrEqual(width);
        }
      }
    });
  });

  describe('setters', () => {
    test('setTask updates task and resets scroll', () => {
      const task1 = mockTask({ id: 'fn-1.1', title: 'First task' });
      const task2 = mockTask({ id: 'fn-1.2', title: 'Second task' });
      const detail = new TaskDetail({
        task: task1,
        spec: '',
        theme: darkTheme,
      });

      // Simulate scrolling
      detail.handleInput('j');
      detail.handleInput('j');

      // Update task
      detail.setTask(task2);
      const lines = detail.render(50);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Second task');
      expect(detail.getScrollOffset()).toBe(0);
    });

    test('setSpec updates markdown content', () => {
      const task = mockTask();
      const detail = new TaskDetail({
        task,
        spec: 'Initial spec',
        theme: darkTheme,
      });
      detail.setSpec('## New content\n\nUpdated spec.');

      const lines = detail.render(50);
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('New content');
    });

    test('setReceipts updates receipt status', () => {
      const task = mockTask();
      const detail = new TaskDetail({
        task,
        spec: '',
        receipts: { plan: false },
        theme: darkTheme,
      });

      detail.setReceipts({ plan: true, impl: true });
      const lines = detail.render(50);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText.match(/✓/g)?.length).toBe(2);
    });

    test('setBlockReason updates block reason', () => {
      const task = mockTask({ status: 'blocked' });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });

      detail.setBlockReason('New block reason');
      const lines = detail.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('New block reason');
    });
  });

  describe('scrolling', () => {
    test('j key scrolls down', () => {
      const task = mockTask();
      const spec = Array.from({ length: 20 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50); // Initialize content height
      detail.setViewportHeight(5); // Small viewport enables scrolling
      expect(detail.getScrollOffset()).toBe(0);

      detail.handleInput('j');
      expect(detail.getScrollOffset()).toBe(1);
    });

    test('k key scrolls up', () => {
      const task = mockTask();
      const spec = Array.from({ length: 20 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(5);
      detail.handleInput('j');
      detail.handleInput('j');
      expect(detail.getScrollOffset()).toBe(2);

      detail.handleInput('k');
      expect(detail.getScrollOffset()).toBe(1);
    });

    test('scroll does not go below 0', () => {
      const task = mockTask();
      const detail = new TaskDetail({ task, spec: 'Test', theme: darkTheme });

      detail.render(50);
      detail.handleInput('k');
      detail.handleInput('k');

      expect(detail.getScrollOffset()).toBe(0);
    });

    test('g key goes to top', () => {
      const task = mockTask();
      const spec = Array.from({ length: 20 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.handleInput('j');
      detail.handleInput('j');
      detail.handleInput('j');

      detail.handleInput('g');
      expect(detail.getScrollOffset()).toBe(0);
    });

    test('G key goes to max scroll (not totalHeight - 1)', () => {
      const task = mockTask();
      const spec = Array.from({ length: 30 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10); // Set viewport to 10 lines
      const maxScroll = detail.getMaxScroll();

      detail.handleInput('G');
      expect(detail.getScrollOffset()).toBe(maxScroll);
      // maxScroll should be totalHeight - viewportHeight, not totalHeight - 1
      expect(maxScroll).toBe(
        detail.getTotalHeight() - detail.getViewportHeight()
      );
    });

    test('uppercase G is distinct from lowercase g', () => {
      const task = mockTask();
      const spec = Array.from({ length: 30 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10);

      // G should go to max scroll
      detail.handleInput('G');
      expect(detail.getScrollOffset()).toBe(detail.getMaxScroll());

      // g should go to top
      detail.handleInput('g');
      expect(detail.getScrollOffset()).toBe(0);
    });

    test('down arrow scrolls down', () => {
      const task = mockTask();
      const spec = Array.from({ length: 20 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(5);
      detail.handleInput('\x1b[B'); // Down arrow
      expect(detail.getScrollOffset()).toBe(1);
    });

    test('up arrow scrolls up', () => {
      const task = mockTask();
      const spec = Array.from({ length: 20 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(5);
      detail.handleInput('j');
      detail.handleInput('\x1b[A'); // Up arrow
      expect(detail.getScrollOffset()).toBe(0);
    });

    test('resetScroll resets scroll position', () => {
      const task = mockTask();
      const spec = Array.from({ length: 20 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(5);
      detail.handleInput('j');
      detail.handleInput('j');

      detail.resetScroll();
      expect(detail.getScrollOffset()).toBe(0);
    });

    test('getTotalHeight returns content height', () => {
      const task = mockTask();
      const spec = 'Line 1\nLine 2\nLine 3';
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      const height = detail.getTotalHeight();

      // Should be at least header lines (3-4) + spec lines
      expect(height).toBeGreaterThanOrEqual(5);
    });

    test('setViewportHeight sets viewport and clamps scroll', () => {
      const task = mockTask();
      const spec = Array.from({ length: 30 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(5);
      expect(detail.getViewportHeight()).toBe(5);

      // Scroll to end, then reduce viewport - scroll should stay clamped
      detail.handleInput('G');
      const scrollBefore = detail.getScrollOffset();
      detail.setViewportHeight(10); // Larger viewport = smaller maxScroll
      expect(detail.getScrollOffset()).toBeLessThanOrEqual(scrollBefore);
    });

    test('page down (space) moves by viewportHeight - 2', () => {
      const task = mockTask();
      const spec = Array.from({ length: 50 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10);
      expect(detail.getScrollOffset()).toBe(0);

      detail.handleInput(' '); // space = page down
      expect(detail.getScrollOffset()).toBe(8); // viewportHeight(10) - 2 = 8
    });

    test('page down (ctrl+d) moves by viewportHeight - 2', () => {
      const task = mockTask();
      const spec = Array.from({ length: 50 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10);

      detail.handleInput('\x04'); // ctrl+d
      expect(detail.getScrollOffset()).toBe(8);
    });

    test('page up (ctrl+u) moves by viewportHeight - 2', () => {
      const task = mockTask();
      const spec = Array.from({ length: 50 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10);

      // Go to end first
      detail.handleInput('G');
      const endOffset = detail.getScrollOffset();

      detail.handleInput('\x15'); // ctrl+u
      expect(detail.getScrollOffset()).toBe(endOffset - 8); // viewportHeight(10) - 2 = 8
    });

    test('page down does not exceed maxScroll', () => {
      const task = mockTask();
      const spec = Array.from({ length: 15 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10);
      const maxScroll = detail.getMaxScroll();

      // Multiple page downs should not exceed maxScroll
      detail.handleInput(' ');
      detail.handleInput(' ');
      detail.handleInput(' ');
      expect(detail.getScrollOffset()).toBeLessThanOrEqual(maxScroll);
    });

    test('page up does not go below 0', () => {
      const task = mockTask();
      const spec = Array.from({ length: 15 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10);

      // Start at 0, page up should stay at 0
      detail.handleInput('\x15');
      expect(detail.getScrollOffset()).toBe(0);
    });

    test('scroll respects maxScroll not totalHeight - 1', () => {
      const task = mockTask();
      const spec = Array.from({ length: 30 }, (_, i) => `Line ${i + 1}`).join(
        '\n'
      );
      const detail = new TaskDetail({ task, spec, theme: darkTheme });

      detail.render(50);
      detail.setViewportHeight(10);
      const totalHeight = detail.getTotalHeight();
      const maxScroll = detail.getMaxScroll();

      // maxScroll should be totalHeight - viewportHeight
      expect(maxScroll).toBe(totalHeight - 10);

      // j key should stop at maxScroll, not totalHeight - 1
      for (let i = 0; i < 100; i++) {
        detail.handleInput('j');
      }
      expect(detail.getScrollOffset()).toBe(maxScroll);
      expect(detail.getScrollOffset()).toBeLessThan(totalHeight - 1);
    });
  });

  describe('invalidate', () => {
    test('invalidate does not throw', () => {
      const task = mockTask();
      const detail = new TaskDetail({ task, spec: '# Test', theme: darkTheme });

      expect(() => detail.invalidate()).not.toThrow();
    });
  });

  describe('sanitization', () => {
    test('control chars in task title are neutralized', () => {
      const task = mockTask({ title: 'Legit\rPWN\tSpoofed' });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(60);

      // \r and \t should be replaced with spaces, not executed
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Legit');
      expect(allText).not.toContain('\r');
      expect(allText).not.toContain('\t');
      // PWN should still be visible (not overwriting), separated by space
      expect(allText).toContain('PWN');
    });

    test('control chars in task id are neutralized', () => {
      const task = mockTask({ id: 'fn-1\x00evil' });
      const detail = new TaskDetail({ task, spec: '', theme: darkTheme });
      const lines = detail.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('fn-1');
      expect(allText).not.toContain('\x00');
    });

    test('control chars in spec are neutralized except newlines', () => {
      const task = mockTask();
      const spec = 'Line1\nLine2\rOverwrite\tTabbed';
      const detail = new TaskDetail({ task, spec, theme: darkTheme });
      const lines = detail.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      // newlines preserved (multiple lines rendered)
      expect(allText).toContain('Line1');
      expect(allText).toContain('Line2');
      // \r and \t replaced with space, not executed
      expect(allText).not.toContain('\r');
      expect(allText).not.toContain('\t');
      expect(allText).toContain('Overwrite');
    });

    test('control chars in blockReason are neutralized', () => {
      const task = mockTask({ status: 'blocked' });
      const blockReason = 'Blocked\rby\ttask';
      const detail = new TaskDetail({
        task,
        spec: '',
        blockReason,
        theme: darkTheme,
      });
      const lines = detail.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Blocked');
      expect(allText).toContain('by');
      expect(allText).toContain('task');
      expect(allText).not.toContain('\r');
      expect(allText).not.toContain('\t');
    });

    test('ANSI escape sequences in spec are stripped', () => {
      const task = mockTask();
      const spec = 'Normal \x1b[31mRED\x1b[0m text';
      const detail = new TaskDetail({ task, spec, theme: darkTheme });
      const lines = detail.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('Normal');
      expect(allText).toContain('RED');
      expect(allText).toContain('text');
      expect(allText).not.toContain('\x1b');
    });
  });
});
