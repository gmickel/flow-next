import { describe, expect, test } from 'bun:test';

import type { LogEntry } from '../lib/types.ts';

import { stripAnsi, visibleWidth } from '../lib/render.ts';
import { darkTheme } from '../themes/dark.ts';
import { OutputPanel } from './output.ts';

/** Create a mock log entry for testing */
function mockEntry(overrides: Partial<LogEntry> = {}): LogEntry {
  return {
    type: 'tool',
    content: 'Test content',
    ...overrides,
  };
}

describe('OutputPanel', () => {
  describe('rendering', () => {
    test('renders bordered header with Output label and iteration', () => {
      const panel = new OutputPanel({ theme: darkTheme, iteration: 3 });
      panel.setViewportHeight(10);
      const lines = panel.render(50);

      // First line is header
      const header = stripAnsi(lines[0]!);
      expect(header).toContain('Output'); // Label on left
      expect(header).toContain('#3'); // Iteration on right
      expect(header).toContain('┌');
      expect(header).toContain('┐');
    });

    test('renders bottom border', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.setViewportHeight(5);
      const lines = panel.render(50);

      // Last line is footer
      const footer = stripAnsi(lines.at(-1)!);
      expect(footer).toContain('└');
      expect(footer).toContain('┘');
    });

    test('renders ASCII borders in ASCII mode', () => {
      const panel = new OutputPanel({ theme: darkTheme, useAscii: true });
      panel.setViewportHeight(5);
      const lines = panel.render(50);

      const header = stripAnsi(lines[0]!);
      const footer = stripAnsi(lines.at(-1)!);
      expect(header).toContain('+');
      expect(footer).toContain('+');
      expect(header).toContain('-');
    });

    test('renders entries with tool icons', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(mockEntry({ tool: 'Read', content: 'Reading file' }));
      panel.appendLine(mockEntry({ tool: 'Bash', content: 'Running command' }));
      panel.setViewportHeight(10);
      const lines = panel.render(50);

      const content = lines.map((l) => stripAnsi(l)).join('\n');
      expect(content).toContain('▸'); // Read icon (Unicode)
      expect(content).toContain('$'); // Bash icon
    });

    test('renders success icon for successful entries', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(mockEntry({ success: true, content: 'Success' }));
      panel.setViewportHeight(10);
      const lines = panel.render(50);

      const content = lines.map((l) => stripAnsi(l)).join('\n');
      expect(content).toContain('✓'); // success icon (Unicode)
    });

    test('renders failure icon for failed entries', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(mockEntry({ success: false, content: 'Failed' }));
      panel.setViewportHeight(10);
      const lines = panel.render(50);

      const content = lines.map((l) => stripAnsi(l)).join('\n');
      expect(content).toContain('✗'); // failure icon (Unicode)
    });

    test('ASCII mode uses ASCII icons', () => {
      const panel = new OutputPanel({ theme: darkTheme, useAscii: true });
      panel.appendLine(mockEntry({ tool: 'Read', content: 'Reading' }));
      panel.appendLine(mockEntry({ tool: 'Bash', content: 'Running' }));
      panel.appendLine(mockEntry({ success: true, content: 'Success' }));
      panel.appendLine(mockEntry({ success: false, content: 'Failed' }));
      panel.setViewportHeight(10);
      const lines = panel.render(50);

      const content = lines.map((l) => stripAnsi(l)).join('\n');
      expect(content).toContain('>'); // Read icon (ASCII)
      expect(content).toContain('$'); // Bash icon
      expect(content).toContain('x'); // Failure (ASCII)
    });

    test('fills empty viewport with empty lines', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.setViewportHeight(10); // viewport inside borders = 8
      const lines = panel.render(50);

      // 1 header + 8 content + 1 footer = 10 lines total
      expect(lines).toHaveLength(10);
    });

    test('truncates long content with ellipsis', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(
        mockEntry({
          content:
            'This is a very long line that should be truncated when rendered in a narrow panel',
        })
      );
      panel.setViewportHeight(5);
      const lines = panel.render(30);

      const contentLine = stripAnsi(lines[1]!);
      expect(contentLine).toContain('…');
      expect(visibleWidth(lines[1]!)).toBeLessThanOrEqual(30);
    });

    test('handles zero width', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      const lines = panel.render(0);
      expect(lines).toHaveLength(0);
    });

    test('handles width of 2 (minimum for borders)', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.setViewportHeight(5);
      const lines = panel.render(2);
      expect(lines).toHaveLength(0);
    });

    test('lines respect width constraint', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(mockEntry({ content: 'Line 1' }));
      panel.appendLine(mockEntry({ content: 'A much longer line of content' }));
      panel.setViewportHeight(5);

      for (const width of [20, 30, 40, 50]) {
        const lines = panel.render(width);
        for (const line of lines) {
          expect(visibleWidth(line)).toBeLessThanOrEqual(width);
        }
      }
    });
  });

  describe('buffer management', () => {
    test('appendLine adds entries to buffer', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      expect(panel.getBufferLength()).toBe(0);

      panel.appendLine(mockEntry({ content: 'Entry 1' }));
      panel.appendLine(mockEntry({ content: 'Entry 2' }));

      expect(panel.getBufferLength()).toBe(2);
    });

    test('buffer respects maxBuffer limit', () => {
      const panel = new OutputPanel({ theme: darkTheme, maxBuffer: 5 });

      for (let i = 0; i < 10; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }

      expect(panel.getBufferLength()).toBe(5);
    });

    test('clearBuffer empties the buffer', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(mockEntry({ content: 'Entry 1' }));
      panel.appendLine(mockEntry({ content: 'Entry 2' }));

      panel.clearBuffer();

      expect(panel.getBufferLength()).toBe(0);
    });

    test('clearBuffer resets scroll and re-enables auto-scroll', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);
      panel.handleInput('k'); // Scroll up disables auto-scroll

      panel.clearBuffer();

      expect(panel.getScrollOffset()).toBe(0);
      expect(panel.isAutoScrollEnabled()).toBe(true);
    });
  });

  describe('setters', () => {
    test('setIteration updates iteration number', () => {
      const panel = new OutputPanel({ theme: darkTheme, iteration: 1 });
      panel.setIteration(5);
      panel.setViewportHeight(5);
      const lines = panel.render(50);

      const header = stripAnsi(lines[0]!);
      expect(header).toContain('#5'); // Iteration on right side of header
    });

    test('setViewportHeight sets viewport size', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.setViewportHeight(15);
      const lines = panel.render(50);

      // 1 header + (15-2) content + 1 footer = 15 lines
      expect(lines).toHaveLength(15);
    });
  });

  describe('scrolling', () => {
    test('auto-scroll enabled by default', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      expect(panel.isAutoScrollEnabled()).toBe(true);
    });

    test('appendLine auto-scrolls to bottom when auto-scroll enabled', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.setViewportHeight(5);

      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }

      // Should be at max scroll (20 entries - 3 viewport = 17)
      expect(panel.getScrollOffset()).toBe(panel.getBufferLength() - 3);
    });

    test('j key scrolls down', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      // First go to top
      panel.handleInput('g');
      expect(panel.getScrollOffset()).toBe(0);

      panel.handleInput('j');
      expect(panel.getScrollOffset()).toBe(1);
    });

    test('k key scrolls up and disables auto-scroll', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      panel.handleInput('k');
      expect(panel.isAutoScrollEnabled()).toBe(false);
    });

    test('scrolling to bottom re-enables auto-scroll', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      // Scroll up to disable auto-scroll
      panel.handleInput('k');
      expect(panel.isAutoScrollEnabled()).toBe(false);

      // Scroll to bottom with G
      panel.handleInput('G');
      expect(panel.isAutoScrollEnabled()).toBe(true);
    });

    test('g key goes to top', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      panel.handleInput('g');
      expect(panel.getScrollOffset()).toBe(0);
    });

    test('G key goes to max scroll', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      panel.handleInput('g'); // Go to top first
      panel.handleInput('G');

      // Should be at max scroll (20 entries - 3 viewport)
      expect(panel.getScrollOffset()).toBe(17);
    });

    test('scroll does not go below 0', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(mockEntry({ content: 'Entry' }));
      panel.setViewportHeight(5);

      panel.handleInput('k');
      panel.handleInput('k');
      panel.handleInput('k');

      expect(panel.getScrollOffset()).toBe(0);
    });

    test('down arrow scrolls down', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      panel.handleInput('g'); // Go to top
      panel.handleInput('\x1b[B'); // Down arrow
      expect(panel.getScrollOffset()).toBe(1);
    });

    test('up arrow scrolls up', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      panel.handleInput('g'); // Go to top
      panel.handleInput('j');
      panel.handleInput('j');
      panel.handleInput('\x1b[A'); // Up arrow
      expect(panel.getScrollOffset()).toBe(1);
    });

    test('page down (space) moves by viewportHeight - 2', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 50; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(12); // 10 viewport inside borders

      panel.handleInput('g'); // Go to top
      panel.handleInput(' '); // Space = page down

      // viewportHeight(12) - 2 - 2 (borders) = 8
      expect(panel.getScrollOffset()).toBe(8);
    });

    test('page up (ctrl+u) moves by viewportHeight - 2', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 50; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(12);

      // Start at scroll 20
      panel.handleInput('g');
      for (let i = 0; i < 20; i++) {
        panel.handleInput('j');
      }

      panel.handleInput('\x15'); // ctrl+u
      expect(panel.getScrollOffset()).toBe(12); // 20 - 8 = 12
    });

    test('scrollToBottom scrolls to end and enables auto-scroll', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      for (let i = 0; i < 20; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }
      panel.setViewportHeight(5);

      panel.handleInput('g'); // Go to top
      panel.handleInput('k'); // Disable auto-scroll

      panel.scrollToBottom();

      expect(panel.getScrollOffset()).toBe(17);
      expect(panel.isAutoScrollEnabled()).toBe(true);
    });
  });

  describe('auto-scroll behavior', () => {
    test('new entries auto-scroll when enabled', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.setViewportHeight(5);

      for (let i = 0; i < 10; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }

      // Should be scrolled to show latest entries
      expect(panel.getScrollOffset()).toBe(7); // 10 - 3 viewport
    });

    test('new entries do not auto-scroll when disabled', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.setViewportHeight(5);

      // Add some entries
      for (let i = 0; i < 10; i++) {
        panel.appendLine(mockEntry({ content: `Entry ${i}` }));
      }

      // Scroll up to disable auto-scroll
      panel.handleInput('k');
      const scrollBefore = panel.getScrollOffset();

      // Add more entries
      for (let i = 0; i < 5; i++) {
        panel.appendLine(mockEntry({ content: `New Entry ${i}` }));
      }

      // Scroll should remain at same position (adjusted for buffer trim if any)
      expect(panel.getScrollOffset()).toBeLessThanOrEqual(scrollBefore);
      expect(panel.isAutoScrollEnabled()).toBe(false);
    });
  });

  describe('sanitization', () => {
    test('control chars in content are neutralized', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(mockEntry({ content: 'Normal\rOverwrite\tTabbed' }));
      panel.setViewportHeight(5);
      const lines = panel.render(60);

      const content = lines.map((l) => stripAnsi(l)).join('\n');
      expect(content).toContain('Normal');
      expect(content).not.toContain('\r');
      expect(content).not.toContain('\t');
    });

    test('ANSI escape sequences in content are stripped', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(
        mockEntry({ content: 'Normal \x1b[31mRED\x1b[0m text' })
      );
      panel.setViewportHeight(5);
      const lines = panel.render(60);

      const content = lines.map((l) => stripAnsi(l)).join('\n');
      expect(content).toContain('Normal');
      expect(content).toContain('RED');
      expect(content).not.toContain('\x1b');
    });

    test('multiline content shows only first line', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      panel.appendLine(
        mockEntry({ content: 'First line\nSecond line\nThird line' })
      );
      panel.setViewportHeight(5);
      const lines = panel.render(60);

      const content = lines.map((l) => stripAnsi(l)).join('\n');
      expect(content).toContain('First line');
      expect(content).not.toContain('Second line');
    });
  });

  describe('invalidate', () => {
    test('invalidate does not throw', () => {
      const panel = new OutputPanel({ theme: darkTheme });
      expect(() => panel.invalidate()).not.toThrow();
    });
  });
});
