import { describe, expect, test } from 'bun:test';

import type { EpicTask } from '../lib/types.ts';

import { stripAnsi, visibleWidth } from '../lib/render.ts';
import { darkTheme } from '../themes/dark.ts';
import { ASCII_ICONS, STATUS_ICONS, TaskList } from './task-list.ts';

/** No-op onSelect for tests that don't need it */
const noop = () => {};

/** Create a mock task for testing */
function mockTask(overrides: Partial<EpicTask> = {}): EpicTask {
  return {
    id: 'fn-1.1',
    title: 'Test task',
    status: 'todo',
    priority: null,
    depends_on: [],
    ...overrides,
  };
}

describe('TaskList', () => {
  describe('rendering', () => {
    test('renders empty state when no tasks', () => {
      const list = new TaskList({
        tasks: [],
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(40);

      // Header + empty message = 2 lines
      expect(lines).toHaveLength(2);
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('No tasks');
    });

    test('empty state respects width constraint', () => {
      const list = new TaskList({
        tasks: [],
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(15);

      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(15);
      }
    });

    test('renders task with status icon and full id', () => {
      const tasks = [mockTask({ id: 'fn-1.3', title: 'Add validation' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(50);

      expect(lines.length).toBeGreaterThanOrEqual(2); // header + task
      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(STATUS_ICONS.todo);
      expect(allText).toContain('fn-1.3'); // Full id, not just 1.3
      expect(allText).toContain('Add validation');
    });

    test('renders done task with success icon', () => {
      const tasks = [mockTask({ status: 'done' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(40);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(STATUS_ICONS.done);
    });

    test('renders in_progress task with progress icon', () => {
      const tasks = [mockTask({ status: 'in_progress' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(40);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(STATUS_ICONS.in_progress);
    });

    test('renders blocked task with blocked icon and dependency indicator', () => {
      // Use actual blocked status
      const tasks = [mockTask({ status: 'blocked', depends_on: ['fn-1.2'] })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(60);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(STATUS_ICONS.blocked);
      expect(allText).toContain('→ 1.2');
    });

    test('blocked task without deps shows blocked icon but no indicator', () => {
      const tasks = [mockTask({ status: 'blocked', depends_on: [] })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(60);

      // Line 1 is task content (line 0 is header)
      const taskLine = stripAnsi(lines[1]!);
      expect(taskLine).toContain(STATUS_ICONS.blocked);
      expect(taskLine).not.toContain('→');
    });

    test('done task with dependencies shows done icon, no dependency indicator', () => {
      const tasks = [mockTask({ status: 'done', depends_on: ['fn-1.2'] })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(60);

      // Line 1 is task content
      const taskLine = stripAnsi(lines[1]!);
      expect(taskLine).toContain(STATUS_ICONS.done);
      // Done tasks should NOT show dependency indicator even if they have deps
      expect(taskLine).not.toContain('→');
    });

    test('in_progress task with dependencies shows progress icon, no dependency indicator', () => {
      const tasks = [
        mockTask({ status: 'in_progress', depends_on: ['fn-1.2'] }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(60);

      // Line 1 is task content
      const taskLine = stripAnsi(lines[1]!);
      expect(taskLine).toContain(STATUS_ICONS.in_progress);
      // In progress tasks should NOT show dependency indicator
      expect(taskLine).not.toContain('→');
    });

    test('todo task with dependencies shows todo icon, no dependency indicator', () => {
      // Todo tasks are not blocked just because they have deps
      const tasks = [mockTask({ status: 'todo', depends_on: ['fn-1.2'] })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(60);

      // Line 1 is task content
      const taskLine = stripAnsi(lines[1]!);
      expect(taskLine).toContain(STATUS_ICONS.todo);
      // Todo with deps is NOT blocked - only status: blocked shows indicator
      expect(taskLine).not.toContain('→');
    });

    test('blocked status uses warning color (unselected row)', () => {
      // Create a mock theme that marks warning color
      const mockTheme = {
        ...darkTheme,
        warning: (s: string) => `[WARN]${s}[/WARN]`,
      };
      // Use two tasks, select the second so first (blocked) row uses per-segment colors
      const tasks = [
        mockTask({ status: 'blocked', depends_on: ['fn-1.2'] }),
        mockTask({ id: 'fn-1.2', status: 'todo' }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 1,
        onSelect: noop,
        theme: mockTheme,
      });
      const lines = list.render(60);

      // Blocked icon (first task row = lines[1], unselected) should have warning color
      expect(lines[1]).toContain('[WARN]');
    });

    test('ASCII mode uses text icons', () => {
      const tasks = [mockTask({ status: 'done' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        useAscii: true,
      });
      const lines = list.render(40);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain(ASCII_ICONS.done);
    });

    test('truncates long titles with ellipsis', () => {
      const tasks = [
        mockTask({
          title: 'This is a very long task title that should be truncated',
        }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(35);

      const allText = lines.map((l) => stripAnsi(l)).join('\n');
      expect(allText).toContain('…');
      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(35);
      }
    });

    test('lines never exceed width even at moderately narrow widths', () => {
      // Test edge case: blocked task with dep indicator at narrow width
      const tasks = [
        mockTask({
          status: 'blocked',
          depends_on: ['fn-1.2'],
          title: 'Long title',
        }),
        mockTask({ id: 'fn-1.2', title: 'Another long title here' }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      // Test various widths - all lines must fit
      // Note: component has minimum usable width due to borders
      for (const width of [15, 20, 25, 30]) {
        const lines = list.render(width);
        for (const line of lines) {
          expect(visibleWidth(line)).toBeLessThanOrEqual(width);
        }
      }
    });

    test('drops dependency indicator when width too narrow', () => {
      // Blocked task with dep at narrow width should drop dep, not overflow
      const tasks = [
        mockTask({ status: 'blocked', depends_on: ['fn-1.2'], title: 'Task' }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      // At narrow widths, lines should fit without overflow
      const lines = list.render(20);
      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(20);
      }
    });

    test('selected row is padded to full width', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2', title: 'Second' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(50);

      // Header (line 0) should be full width
      expect(visibleWidth(lines[0]!)).toBe(50);
      // First task row (line 1, selected) should also be full width
      expect(visibleWidth(lines[1]!)).toBe(50);
    });

    test('unselected rows also padded to full width in bordered layout', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2', title: 'Second' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(50);

      // With bordered layout, all rows are full width
      expect(visibleWidth(lines[1]!)).toBe(50); // first task (selected)
      expect(visibleWidth(lines[2]!)).toBe(50); // second task
    });

    test('selected row preserves status colors with selection background', () => {
      // The implementation applies per-segment bg+fg using chalk.bgAnsi256().ansi256()
      // We can verify this by checking the row has ANSI codes (when in TTY)
      // Since tests don't run in TTY, just verify width and basic structure
      const tasks = [
        mockTask({ status: 'done' }),
        mockTask({ id: 'fn-1.2', status: 'todo' }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const lines = list.render(50);

      // Header + 2 tasks = 3 lines
      expect(lines.length).toBeGreaterThanOrEqual(3);

      // Both task rows should contain the status icons (content preserved)
      expect(stripAnsi(lines[1]!)).toContain(STATUS_ICONS.done);
      expect(stripAnsi(lines[2]!)).toContain(STATUS_ICONS.todo);
    });

    test('scroll indicator shown when tasks exceed maxVisible', () => {
      const tasks = Array.from({ length: 15 }, (_, i) =>
        mockTask({ id: `fn-1.${i + 1}`, title: `Task ${i + 1}` })
      );
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        maxVisible: 5,
      });
      const lines = list.render(50);

      // Last line should be scroll indicator with format "↕ N/M"
      const lastLine = stripAnsi(lines[lines.length - 1]!);
      expect(lastLine).toMatch(/\d+\/\d+/);
    });

    test('no scroll indicator when tasks fit in maxVisible', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        maxVisible: 10,
      });
      const lines = list.render(50);

      // Should have header + 2 task lines, no scroll indicator
      expect(lines).toHaveLength(3);
    });

    test('scroll indicator respects width constraint', () => {
      const tasks = Array.from({ length: 15 }, (_, i) =>
        mockTask({ id: `fn-1.${i + 1}`, title: `Task ${i + 1}` })
      );
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        maxVisible: 5,
      });

      // At reasonable narrow width, scroll indicator should fit
      const lines = list.render(20);
      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(20);
      }
    });

    test('maxVisible is clamped to at least 1', () => {
      const tasks = [
        mockTask(),
        mockTask({ id: 'fn-1.2' }),
        mockTask({ id: 'fn-1.3' }),
      ];

      // Test with 0
      const list1 = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        maxVisible: 0,
      });
      const lines1 = list1.render(50);
      // Should render at least 1 task + scroll indicator
      expect(lines1.length).toBeGreaterThanOrEqual(1);

      // Test with negative
      const list2 = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        maxVisible: -5,
      });
      const lines2 = list2.render(50);
      // Should render at least 1 task + scroll indicator
      expect(lines2.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('navigation', () => {
    test('j key moves selection down', () => {
      const tasks = [
        mockTask(),
        mockTask({ id: 'fn-1.2' }),
        mockTask({ id: 'fn-1.3' }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      expect(list.getSelectedIndex()).toBe(0);
      list.handleInput('j');
      expect(list.getSelectedIndex()).toBe(1);
    });

    test('k key moves selection up', () => {
      const tasks = [
        mockTask(),
        mockTask({ id: 'fn-1.2' }),
        mockTask({ id: 'fn-1.3' }),
      ];
      const list = new TaskList({
        tasks,
        selectedIndex: 2,
        onSelect: noop,
        theme: darkTheme,
      });

      expect(list.getSelectedIndex()).toBe(2);
      list.handleInput('k');
      expect(list.getSelectedIndex()).toBe(1);
    });

    test('down arrow moves selection down', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      list.handleInput('\x1b[B'); // Down arrow escape sequence
      expect(list.getSelectedIndex()).toBe(1);
    });

    test('up arrow moves selection up', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 1,
        onSelect: noop,
        theme: darkTheme,
      });

      list.handleInput('\x1b[A'); // Up arrow escape sequence
      expect(list.getSelectedIndex()).toBe(0);
    });

    test('j wraps to top when at bottom', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 1,
        onSelect: noop,
        theme: darkTheme,
      });

      list.handleInput('j');
      expect(list.getSelectedIndex()).toBe(0);
    });

    test('k wraps to bottom when at top', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      list.handleInput('k');
      expect(list.getSelectedIndex()).toBe(1);
    });

    test('navigation with empty list does not crash or mutate index', () => {
      const list = new TaskList({
        tasks: [],
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      expect(() => list.handleInput('j')).not.toThrow();
      expect(() => list.handleInput('k')).not.toThrow();
      // Index should remain 0, not go negative or grow
      expect(list.getSelectedIndex()).toBe(0);
    });
  });

  describe('selection', () => {
    test('enter key fires onSelect callback', () => {
      let selected: EpicTask | undefined;
      const tasks = [mockTask({ id: 'fn-1.5' }), mockTask({ id: 'fn-1.6' })];
      const list = new TaskList({
        tasks,
        theme: darkTheme,
        selectedIndex: 1,
        onSelect: (task) => {
          selected = task;
        },
      });

      list.handleInput('\r'); // Enter
      expect(selected).toBeDefined();
      expect(selected!.id).toBe('fn-1.6');
    });

    test('onSelectionChange fires when selection moves', () => {
      let changedTo: EpicTask | undefined;
      let changedIndex: number | undefined;
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        theme: darkTheme,
        selectedIndex: 0,
        onSelect: noop,
        onSelectionChange: (task, index) => {
          changedTo = task;
          changedIndex = index;
        },
      });

      list.handleInput('j');
      expect(changedTo).toBeDefined();
      expect(changedTo!.id).toBe('fn-1.2');
      expect(changedIndex).toBe(1);
    });

    test('getSelectedTask returns current selection', () => {
      const tasks = [mockTask({ id: 'fn-1.1' }), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 1,
        onSelect: noop,
        theme: darkTheme,
      });

      const selected = list.getSelectedTask();
      expect(selected).toBeDefined();
      expect(selected!.id).toBe('fn-1.2');
    });

    test('setSelectedIndex updates selection', () => {
      let changedTo: EpicTask | undefined;
      const tasks = [
        mockTask(),
        mockTask({ id: 'fn-1.2' }),
        mockTask({ id: 'fn-1.3' }),
      ];
      const list = new TaskList({
        tasks,
        theme: darkTheme,
        selectedIndex: 0,
        onSelect: noop,
        onSelectionChange: (task) => {
          changedTo = task;
        },
      });

      list.setSelectedIndex(2);
      expect(list.getSelectedIndex()).toBe(2);
      expect(changedTo!.id).toBe('fn-1.3');
    });

    test('setSelectedIndex clamps to valid range', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      list.setSelectedIndex(100);
      expect(list.getSelectedIndex()).toBe(1); // clamped to max

      list.setSelectedIndex(-5);
      expect(list.getSelectedIndex()).toBe(0); // clamped to min
    });

    test('constructor clamps out-of-range selectedIndex', () => {
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];

      // Test high value
      const list1 = new TaskList({
        tasks,
        selectedIndex: 100,
        onSelect: noop,
        theme: darkTheme,
      });
      expect(list1.getSelectedIndex()).toBe(1); // clamped to max

      // Test negative value
      const list2 = new TaskList({
        tasks,
        selectedIndex: -5,
        onSelect: noop,
        theme: darkTheme,
      });
      expect(list2.getSelectedIndex()).toBe(0); // clamped to 0

      // Test empty tasks with non-zero index
      const list3 = new TaskList({
        tasks: [],
        selectedIndex: 5,
        onSelect: noop,
        theme: darkTheme,
      });
      expect(list3.getSelectedIndex()).toBe(0); // clamped to 0 for empty list
    });

    test('setSelectedIndex does not fire callback if index unchanged', () => {
      let callCount = 0;
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        theme: darkTheme,
        selectedIndex: 1,
        onSelect: noop,
        onSelectionChange: () => {
          callCount++;
        },
      });

      list.setSelectedIndex(1);
      expect(callCount).toBe(0);
    });
  });

  describe('setTasks', () => {
    test('setTasks updates task list', () => {
      const list = new TaskList({
        tasks: [mockTask()],
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      const newTasks = [mockTask({ id: 'fn-2.1' }), mockTask({ id: 'fn-2.2' })];

      list.setTasks(newTasks);
      const lines = list.render(50);

      // Line 1 is first task (line 0 is header)
      expect(stripAnsi(lines[1]!)).toContain('fn-2.1');
    });

    test('setTasks clamps selection when new list is shorter', () => {
      const tasks = Array.from({ length: 5 }, (_, i) =>
        mockTask({ id: `fn-1.${i + 1}` })
      );
      const list = new TaskList({
        tasks,
        selectedIndex: 4,
        onSelect: noop,
        theme: darkTheme,
      });

      list.setTasks([mockTask()]); // Now only 1 task
      expect(list.getSelectedIndex()).toBe(0);
    });

    test('setTasks notifies when selection changes due to clamping', () => {
      let changedTo: EpicTask | undefined;
      let changedIndex: number | undefined;
      const tasks = Array.from({ length: 5 }, (_, i) =>
        mockTask({ id: `fn-1.${i + 1}` })
      );
      const list = new TaskList({
        tasks,
        selectedIndex: 4,
        onSelect: noop,
        theme: darkTheme,
        onSelectionChange: (task, index) => {
          changedTo = task;
          changedIndex = index;
        },
      });

      // Reduce to 2 tasks - selection should clamp from 4 to 1 and notify
      list.setTasks([mockTask({ id: 'fn-2.1' }), mockTask({ id: 'fn-2.2' })]);
      expect(list.getSelectedIndex()).toBe(1);
      expect(changedIndex).toBe(1);
      expect(changedTo!.id).toBe('fn-2.2');
    });

    test('setTasks does not notify when selection unchanged', () => {
      let callCount = 0;
      const tasks = [mockTask(), mockTask({ id: 'fn-1.2' })];
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        onSelectionChange: () => {
          callCount++;
        },
      });

      // Replace with same-length list - selection stays at 0
      list.setTasks([mockTask({ id: 'fn-2.1' }), mockTask({ id: 'fn-2.2' })]);
      expect(list.getSelectedIndex()).toBe(0);
      expect(callCount).toBe(0);
    });

    test('setTasks handles empty list', () => {
      const list = new TaskList({
        tasks: [mockTask()],
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });

      list.setTasks([]);
      expect(list.getSelectedIndex()).toBe(0);
      expect(list.getSelectedTask()).toBeUndefined();
    });
  });

  describe('scrolling', () => {
    test('scrolls to keep selected item visible', () => {
      const tasks = Array.from({ length: 20 }, (_, i) =>
        mockTask({ id: `fn-1.${i + 1}`, title: `Task ${i + 1}` })
      );
      const list = new TaskList({
        tasks,
        selectedIndex: 15,
        onSelect: noop,
        theme: darkTheme,
        maxVisible: 5,
      });
      const lines = list.render(50);

      // Selected task should be visible in rendered output
      const hasSelectedTask = lines.some((line) =>
        stripAnsi(line).includes('fn-1.16')
      );
      expect(hasSelectedTask).toBe(true);
    });

    test('scroll position updates when navigating', () => {
      const tasks = Array.from({ length: 20 }, (_, i) =>
        mockTask({ id: `fn-1.${i + 1}`, title: `Task ${i + 1}` })
      );
      const list = new TaskList({
        tasks,
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
        maxVisible: 5,
      });

      // Navigate to bottom
      for (let i = 0; i < 15; i++) {
        list.handleInput('j');
      }

      const lines = list.render(50);
      // Task 16 should be visible
      const hasTask16 = lines.some((line) =>
        stripAnsi(line).includes('fn-1.16')
      );
      expect(hasTask16).toBe(true);
    });
  });

  describe('invalidate', () => {
    test('invalidate does not throw', () => {
      const list = new TaskList({
        tasks: [mockTask()],
        selectedIndex: 0,
        onSelect: noop,
        theme: darkTheme,
      });
      expect(() => list.invalidate()).not.toThrow();
    });
  });
});
