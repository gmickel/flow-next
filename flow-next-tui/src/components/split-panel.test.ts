import type { Component } from '@mariozechner/pi-tui';

import { describe, expect, test } from 'bun:test';

import { visibleWidth } from '../lib/render.ts';
import { SplitPanel } from './split-panel.ts';

/** Simple mock component that renders fixed lines */
class MockComponent implements Component {
  lines: string[];
  inputReceived: string[] = [];

  constructor(lines: string[]) {
    this.lines = lines;
  }

  render(_width: number): string[] {
    return this.lines;
  }

  handleInput(data: string): void {
    this.inputReceived.push(data);
  }

  invalidate(): void {
    // No-op for testing
  }
}

/** Mock component that respects width */
class WidthAwareComponent implements Component {
  text: string;

  constructor(text: string) {
    this.text = text;
  }

  render(width: number): string[] {
    // Pad or truncate to exact width
    if (this.text.length >= width) {
      return [this.text.slice(0, width)];
    }
    return [this.text.padEnd(width)];
  }

  invalidate(): void {
    // No-op
  }
}

describe('SplitPanel', () => {
  test('renders two components side-by-side', () => {
    const left = new MockComponent(['LEFT']);
    const right = new MockComponent(['RIGHT']);
    const panel = new SplitPanel({ left, right });

    const lines = panel.render(20);

    expect(lines).toHaveLength(1);
    expect(lines[0]).toContain('LEFT');
    expect(lines[0]).toContain('│');
    expect(lines[0]).toContain('RIGHT');
  });

  test('ratio controls width split correctly', () => {
    const left = new WidthAwareComponent('L');
    const right = new WidthAwareComponent('R');

    // 50% split on 21 chars (20 content + 1 separator)
    const panel = new SplitPanel({ left, right, ratio: 0.5 });
    const lines = panel.render(21);

    expect(lines).toHaveLength(1);
    // 21 - 1 (sep) = 20, split 50/50 = 10 each
    const line = lines[0];
    expect(line).toBeDefined();
    const parts = line!.split('│');
    expect(parts[0]).toHaveLength(10);
    expect(parts[1]).toHaveLength(10);
  });

  test('separator visible between panels', () => {
    const left = new MockComponent(['A']);
    const right = new MockComponent(['B']);
    const panel = new SplitPanel({ left, right, separator: '║' });

    const lines = panel.render(20);

    expect(lines[0]).toContain('║');
  });

  test('shorter panel padded to match height', () => {
    const left = new MockComponent(['L1', 'L2', 'L3']);
    const right = new MockComponent(['R1']);
    const panel = new SplitPanel({ left, right });

    const lines = panel.render(20);

    expect(lines).toHaveLength(3);
    // All lines should have separator
    for (const line of lines) {
      expect(line).toContain('│');
    }
  });

  test('default ratio is 0.3', () => {
    const left = new WidthAwareComponent('L');
    const right = new WidthAwareComponent('R');
    const panel = new SplitPanel({ left, right });

    // 101 - 1 (sep) = 100, 0.3 ratio = 30 left, 70 right
    const lines = panel.render(101);
    const line = lines[0];
    expect(line).toBeDefined();
    const parts = line!.split('│');

    expect(parts[0]).toHaveLength(30);
    expect(parts[1]).toHaveLength(70);
  });

  test('default separator is │', () => {
    const left = new MockComponent(['A']);
    const right = new MockComponent(['B']);
    const panel = new SplitPanel({ left, right });

    const lines = panel.render(20);

    expect(lines[0]).toContain('│');
  });

  test('handles ANSI codes without breaking width', () => {
    const left = new MockComponent(['\x1b[31mRED\x1b[0m']);
    const right = new MockComponent(['PLAIN']);
    const panel = new SplitPanel({ left, right, ratio: 0.5 });

    // 21 - 1 = 20, 50% = 10 each
    const targetWidth = 21;
    const lines = panel.render(targetWidth);

    expect(lines).toHaveLength(1);
    const line = lines[0];
    expect(line).toBeDefined();

    // Verify ANSI sequence present
    expect(line).toContain('\x1b[31m');
    expect(line).toContain('RED');

    // Verify visible width matches target (ANSI codes don't affect it)
    expect(visibleWidth(line!)).toBe(targetWidth);

    // Verify left section is padded to correct visible width
    const sepIdx = line!.indexOf('│');
    const leftPart = line!.slice(0, sepIdx);
    expect(visibleWidth(leftPart)).toBe(10);
  });

  test('input forwarded to active child only (default left)', () => {
    const left = new MockComponent(['L']);
    const right = new MockComponent(['R']);
    const panel = new SplitPanel({ left, right });

    panel.handleInput('j');

    expect(left.inputReceived).toContain('j');
    expect(right.inputReceived).not.toContain('j');
  });

  test('input forwarded to right when active=right', () => {
    const left = new MockComponent(['L']);
    const right = new MockComponent(['R']);
    const panel = new SplitPanel({ left, right, active: 'right' });

    panel.handleInput('k');

    expect(left.inputReceived).not.toContain('k');
    expect(right.inputReceived).toContain('k');
  });

  test('setActive changes which child receives input', () => {
    const left = new MockComponent(['L']);
    const right = new MockComponent(['R']);
    const panel = new SplitPanel({ left, right });

    panel.handleInput('a');
    expect(left.inputReceived).toContain('a');
    expect(right.inputReceived).not.toContain('a');

    panel.setActive('right');
    panel.handleInput('b');
    expect(left.inputReceived).not.toContain('b');
    expect(right.inputReceived).toContain('b');
  });

  test('invalidate calls invalidate on children', () => {
    let leftInvalidated = false;
    let rightInvalidated = false;

    const left: Component = {
      render: () => ['L'],
      invalidate: () => {
        leftInvalidated = true;
      },
    };
    const right: Component = {
      render: () => ['R'],
      invalidate: () => {
        rightInvalidated = true;
      },
    };
    const panel = new SplitPanel({ left, right });

    panel.invalidate();

    expect(leftInvalidated).toBe(true);
    expect(rightInvalidated).toBe(true);
  });

  test('handles very small width gracefully', () => {
    const left = new MockComponent(['LEFT']);
    const right = new MockComponent(['RIGHT']);
    const panel = new SplitPanel({ left, right });

    // Width of 2 means leftWidth or rightWidth would be <= 0
    const lines = panel.render(2);

    // Should fall back to just left panel
    expect(lines).toHaveLength(1);
  });

  test('handles empty child output', () => {
    const left = new MockComponent([]);
    const right = new MockComponent(['R']);
    const panel = new SplitPanel({ left, right });

    const lines = panel.render(20);

    expect(lines).toHaveLength(1);
    expect(lines[0]).toContain('│');
    expect(lines[0]).toContain('R');
  });

  test('handles both children empty', () => {
    const left = new MockComponent([]);
    const right = new MockComponent([]);
    const panel = new SplitPanel({ left, right });

    const lines = panel.render(20);

    expect(lines).toHaveLength(0);
  });

  test('ratio of 0 triggers fallback to left panel only', () => {
    const left = new WidthAwareComponent('L');
    const right = new WidthAwareComponent('R');
    const panel = new SplitPanel({ left, right, ratio: 0 });

    const lines = panel.render(21);

    // 0 ratio means leftWidth = 0, which triggers fallback to left panel only
    expect(lines).toHaveLength(1);
    expect(lines[0]).not.toContain('│'); // No separator in fallback mode
  });

  test('ratio of 1 triggers fallback to left panel only', () => {
    const left = new WidthAwareComponent('L');
    const right = new WidthAwareComponent('R');
    const panel = new SplitPanel({ left, right, ratio: 1 });

    const lines = panel.render(21);

    // 1 ratio means rightWidth = 0, which triggers fallback to left panel only
    expect(lines).toHaveLength(1);
    expect(lines[0]).not.toContain('│'); // No separator in fallback mode
  });

  test('multi-char separator handled correctly', () => {
    const left = new WidthAwareComponent('L');
    const right = new WidthAwareComponent('R');
    const panel = new SplitPanel({ left, right, separator: ' | ', ratio: 0.5 });

    // 23 - 3 (sep) = 20, 50% = 10 each
    const lines = panel.render(23);
    const line = lines[0];
    expect(line).toBeDefined();

    expect(line).toContain(' | ');
    const parts = line!.split(' | ');
    expect(parts[0]).toHaveLength(10);
    expect(parts[1]).toHaveLength(10);
  });
});
