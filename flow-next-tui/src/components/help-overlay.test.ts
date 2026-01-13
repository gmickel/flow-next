import { describe, expect, test } from 'bun:test';

import { stripAnsi, visibleWidth } from '../lib/render.ts';
import { darkTheme } from '../themes/dark.ts';
import { lightTheme } from '../themes/light.ts';
import { HelpOverlay, type HelpOverlayProps } from './help-overlay.ts';

/** Create default help overlay props */
function defaultProps(overrides?: Partial<HelpOverlayProps>): HelpOverlayProps {
  return {
    theme: darkTheme,
    visible: true,
    ...overrides,
  };
}

describe('HelpOverlay', () => {
  describe('visibility', () => {
    test('returns empty array when not visible', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: false }));
      const lines = overlay.render(80);

      expect(lines).toHaveLength(0);
    });

    test('renders content when visible', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: true }));
      const lines = overlay.render(80);

      expect(lines.length).toBeGreaterThan(0);
    });

    test('isVisible() returns current state', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: false }));
      expect(overlay.isVisible()).toBe(false);

      overlay.show();
      expect(overlay.isVisible()).toBe(true);
    });

    test('show() makes overlay visible', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: false }));
      overlay.show();

      expect(overlay.isVisible()).toBe(true);
      expect(overlay.render(80).length).toBeGreaterThan(0);
    });

    test('hide() makes overlay invisible', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: true }));
      overlay.hide();

      expect(overlay.isVisible()).toBe(false);
      expect(overlay.render(80)).toHaveLength(0);
    });

    test('toggle() flips visibility', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: false }));

      overlay.toggle();
      expect(overlay.isVisible()).toBe(true);

      overlay.toggle();
      expect(overlay.isVisible()).toBe(false);
    });
  });

  describe('content', () => {
    test('contains all keybindings', () => {
      const overlay = new HelpOverlay(defaultProps());
      const lines = overlay.render(80);
      const content = lines.map(stripAnsi).join('\n');

      expect(content).toContain('j/k');
      expect(content).toContain('Navigate task list');
      expect(content).toContain('?');
      expect(content).toContain('Show/hide this help');
      expect(content).toContain('q');
      expect(content).toContain('Quit');
      expect(content).toContain('Esc');
      expect(content).toContain('Close overlay');
      expect(content).toContain('Ctrl+C');
    });

    test('contains Help title', () => {
      const overlay = new HelpOverlay(defaultProps());
      const lines = overlay.render(80);
      const content = lines.map(stripAnsi).join('\n');

      expect(content).toContain('Help');
    });

    test('contains close hint', () => {
      const overlay = new HelpOverlay(defaultProps());
      const lines = overlay.render(80);
      const content = lines.map(stripAnsi).join('\n');

      expect(content).toContain('Press ? or Esc to close');
    });

    test('has box borders', () => {
      const overlay = new HelpOverlay(defaultProps());
      const lines = overlay.render(80);
      const content = lines.map(stripAnsi).join('\n');

      expect(content).toContain('┌');
      expect(content).toContain('┐');
      expect(content).toContain('└');
      expect(content).toContain('┘');
      expect(content).toContain('│');
    });
  });

  describe('centering', () => {
    test('horizontally centers the box', () => {
      const overlay = new HelpOverlay(defaultProps());
      const width = 80;
      const lines = overlay.render(width);

      // Find a line with content (not padding)
      const boxLine = lines.find((l) => stripAnsi(l).includes('│'))!;
      const stripped = stripAnsi(boxLine);

      // Should have leading spaces for centering
      const leadingSpaces = stripped.match(/^(\s*)/)?.[1]?.length ?? 0;
      expect(leadingSpaces).toBeGreaterThan(0);

      // Box should not touch left edge
      expect(stripped.trimStart()).not.toBe(stripped);
    });

    test('vertically centers when height provided', () => {
      const overlay = new HelpOverlay(defaultProps());
      const width = 80;
      const height = 30;
      const lines = overlay.render(width, height);

      expect(lines).toHaveLength(height);

      // First few lines should be empty (vertical padding)
      let emptyCount = 0;
      for (const line of lines) {
        if (stripAnsi(line).trim() === '') {
          emptyCount++;
        } else {
          break;
        }
      }
      expect(emptyCount).toBeGreaterThan(0);
    });
  });

  describe('width constraints', () => {
    test('respects maximum width', () => {
      const overlay = new HelpOverlay(defaultProps());
      const lines = overlay.render(200);

      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(200);
      }
    });

    test('handles narrow width', () => {
      const overlay = new HelpOverlay(defaultProps());
      const width = 40;
      const lines = overlay.render(width);

      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(width);
      }
    });

    test('handles very narrow width gracefully', () => {
      const overlay = new HelpOverlay(defaultProps());
      const width = 25;
      const lines = overlay.render(width);

      // Should still render something
      expect(lines.length).toBeGreaterThan(0);

      // All lines must respect width constraint
      for (const line of lines) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(width);
      }
    });

    test('handles width < 4 without throwing', () => {
      const overlay = new HelpOverlay(defaultProps());

      // Width 3: should return blank lines, not throw
      const lines3 = overlay.render(3);
      expect(lines3.length).toBeGreaterThan(0);
      for (const line of lines3) {
        expect(visibleWidth(line)).toBeLessThanOrEqual(3);
      }

      // Width 0: edge case
      const lines0 = overlay.render(0);
      expect(lines0.length).toBeGreaterThan(0);
      for (const line of lines0) {
        expect(visibleWidth(line)).toBe(0);
      }

      // Width < 4 with height
      const linesH = overlay.render(2, 10);
      expect(linesH).toHaveLength(10);
      for (const line of linesH) {
        expect(visibleWidth(line)).toBe(2);
      }
    });
  });

  describe('input handling', () => {
    test('Escape key hides overlay', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: true }));

      overlay.handleInput('\x1b');

      expect(overlay.isVisible()).toBe(false);
    });

    test('? key hides overlay', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: true }));

      overlay.handleInput('?');

      expect(overlay.isVisible()).toBe(false);
    });

    test('calls onClose callback when dismissed', () => {
      let closeCalled = false;
      const overlay = new HelpOverlay(
        defaultProps({
          visible: true,
          onClose: () => {
            closeCalled = true;
          },
        })
      );

      overlay.handleInput('\x1b');

      expect(closeCalled).toBe(true);
    });

    test('? key opens overlay when hidden', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: false }));

      overlay.handleInput('?');

      expect(overlay.isVisible()).toBe(true);
    });

    test('? key does not call onClose when opening', () => {
      let closeCalled = false;
      const overlay = new HelpOverlay(
        defaultProps({
          visible: false,
          onClose: () => {
            closeCalled = true;
          },
        })
      );

      overlay.handleInput('?');

      expect(overlay.isVisible()).toBe(true);
      expect(closeCalled).toBe(false);
    });

    test('ignores non-? keys when not visible', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: false }));

      overlay.handleInput('j');
      expect(overlay.isVisible()).toBe(false);

      overlay.handleInput('\x1b');
      expect(overlay.isVisible()).toBe(false);
    });

    test('other keys do not close overlay', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: true }));

      overlay.handleInput('j');
      expect(overlay.isVisible()).toBe(true);

      overlay.handleInput('k');
      expect(overlay.isVisible()).toBe(true);

      overlay.handleInput('q');
      expect(overlay.isVisible()).toBe(true);
    });
  });

  describe('update()', () => {
    test('can change visibility', () => {
      const overlay = new HelpOverlay(defaultProps({ visible: false }));

      overlay.update({ visible: true });

      expect(overlay.isVisible()).toBe(true);
    });

    test('can change theme', () => {
      const overlay = new HelpOverlay(defaultProps({ theme: darkTheme }));

      overlay.update({ theme: lightTheme });
      const lines = overlay.render(80);

      // Should render without error
      expect(lines.length).toBeGreaterThan(0);
    });

    test('can change onClose callback', () => {
      let callCount = 0;
      const overlay = new HelpOverlay(
        defaultProps({
          visible: true,
          onClose: () => {
            callCount++;
          },
        })
      );

      let newCallCount = 0;
      overlay.update({
        onClose: () => {
          newCallCount++;
        },
      });

      overlay.handleInput('\x1b');

      expect(callCount).toBe(0);
      expect(newCallCount).toBe(1);
    });
  });

  describe('invalidate()', () => {
    test('does nothing (no-op)', () => {
      const overlay = new HelpOverlay(defaultProps());
      // Should not throw
      overlay.invalidate();
    });
  });

  describe('padded output', () => {
    test('lines are padded to full width', () => {
      const overlay = new HelpOverlay(defaultProps());
      const width = 80;
      const lines = overlay.render(width);

      for (const line of lines) {
        expect(visibleWidth(line)).toBe(width);
      }
    });

    test('lines with height are padded to full width', () => {
      const overlay = new HelpOverlay(defaultProps());
      const width = 80;
      const height = 20;
      const lines = overlay.render(width, height);

      // All lines (including vertical padding) should be padded to width
      for (const line of lines) {
        expect(visibleWidth(line)).toBe(width);
      }
    });
  });
});
