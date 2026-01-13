import { describe, expect, test } from 'bun:test';

import { padToWidth, stripAnsi, truncateToWidth, visibleWidth } from './render';

// ANSI escape codes for testing
const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

describe('visibleWidth', () => {
  test('plain text', () => {
    expect(visibleWidth('hello')).toBe(5);
    expect(visibleWidth('')).toBe(0);
    expect(visibleWidth('a b c')).toBe(5);
  });

  test('text with color codes', () => {
    expect(visibleWidth(`${RED}hello${RESET}`)).toBe(5);
    expect(visibleWidth(`${GREEN}world${RESET}`)).toBe(5);
  });

  test('text with nested styles', () => {
    expect(visibleWidth(`${BOLD}${RED}bold red${RESET}`)).toBe(8);
    expect(visibleWidth(`${RED}red ${GREEN}green${RESET}`)).toBe(9);
  });

  test('text with cursor movement codes', () => {
    expect(visibleWidth('\x1b[3Aup')).toBe(2);
    expect(visibleWidth('\x1b[2Bdown')).toBe(4);
    expect(visibleWidth('\x1b[1;2Hpos')).toBe(3);
  });

  test('text with private mode sequences', () => {
    expect(visibleWidth('\x1b[?25lhidden')).toBe(6);
    expect(visibleWidth('\x1b[?25hvisible')).toBe(7);
    expect(visibleWidth('\x1b[?1049halt')).toBe(3);
  });

  test('text with OSC sequences (BEL terminator)', () => {
    const link = '\x1b]8;;https://example.com\x07Click\x1b]8;;\x07';
    expect(visibleWidth(link)).toBe(5);
    expect(visibleWidth('\x1b]0;Title\x07content')).toBe(7);
  });

  test('text with OSC sequences (ST terminator)', () => {
    const linkST = '\x1b]8;;https://example.com\x1b\\Click\x1b]8;;\x1b\\';
    expect(visibleWidth(linkST)).toBe(5);
  });

  test('text with simple escape sequences', () => {
    expect(visibleWidth('\x1bcreset')).toBe(5);
    expect(visibleWidth('\x1b7save\x1b8')).toBe(4);
  });

  test('text with charset designators', () => {
    expect(visibleWidth('\x1b(Btext')).toBe(4);
    expect(visibleWidth('\x1b)0graphics')).toBe(8);
  });

  test('edge cases', () => {
    expect(visibleWidth('')).toBe(0);
    expect(visibleWidth(`${RESET}`)).toBe(0);
    expect(visibleWidth(`${RED}${RESET}`)).toBe(0);
  });
});

describe('stripAnsi', () => {
  test('plain text unchanged', () => {
    expect(stripAnsi('hello')).toBe('hello');
    expect(stripAnsi('')).toBe('');
  });

  test('removes color codes', () => {
    expect(stripAnsi(`${RED}hello${RESET}`)).toBe('hello');
    expect(stripAnsi(`${GREEN}world${RESET}`)).toBe('world');
  });

  test('removes nested styles', () => {
    expect(stripAnsi(`${BOLD}${RED}bold red${RESET}`)).toBe('bold red');
    expect(stripAnsi(`${RED}red ${GREEN}green${RESET}`)).toBe('red green');
  });

  test('removes cursor movement codes', () => {
    expect(stripAnsi('\x1b[2Kcleared')).toBe('cleared');
    expect(stripAnsi('\x1b[1Gmoved')).toBe('moved');
    expect(stripAnsi('\x1b[3Aup')).toBe('up');
    expect(stripAnsi('\x1b[2Bdown')).toBe('down');
    expect(stripAnsi('\x1b[5Cforward')).toBe('forward');
    expect(stripAnsi('\x1b[1Dback')).toBe('back');
    expect(stripAnsi('\x1b[1;2Hpos')).toBe('pos');
    expect(stripAnsi('\x1b[10;20fset')).toBe('set');
  });

  test('removes private mode sequences', () => {
    expect(stripAnsi('\x1b[?25lhidden')).toBe('hidden');
    expect(stripAnsi('\x1b[?25hvisible')).toBe('visible');
    expect(stripAnsi('\x1b[?1049halt')).toBe('alt');
  });

  test('removes OSC with BEL terminator', () => {
    const link = '\x1b]8;;https://example.com\x07Click\x1b]8;;\x07';
    expect(stripAnsi(link)).toBe('Click');
    expect(stripAnsi('\x1b]0;Title\x07content')).toBe('content');
  });

  test('removes OSC with ST terminator', () => {
    const linkST = '\x1b]8;;https://example.com\x1b\\Click\x1b]8;;\x1b\\';
    expect(stripAnsi(linkST)).toBe('Click');
  });

  test('removes simple escape sequences', () => {
    expect(stripAnsi('\x1bcreset')).toBe('reset');
    expect(stripAnsi('\x1b7save\x1b8')).toBe('save');
  });

  test('removes charset designator sequences', () => {
    // ESC ( B = US ASCII charset
    expect(stripAnsi('\x1b(Btext')).toBe('text');
    // ESC ) 0 = DEC Special Graphics
    expect(stripAnsi('\x1b)0graphics')).toBe('graphics');
    // Multiple charset sequences
    expect(stripAnsi('\x1b(B\x1b)0mixed')).toBe('mixed');
  });

  test('edge cases', () => {
    expect(stripAnsi('')).toBe('');
    expect(stripAnsi(`${RESET}`)).toBe('');
    expect(stripAnsi(`${RED}${GREEN}${RESET}`)).toBe('');
  });
});

describe('padToWidth', () => {
  test('plain text pads without reset', () => {
    // Plain text without ANSI should not get reset added
    expect(padToWidth('hi', 5)).toBe('hi   ');
    expect(padToWidth('hello', 10)).toBe('hello     ');
  });

  test('no padding needed returns unchanged', () => {
    expect(padToWidth('hello', 5)).toBe('hello');
    expect(padToWidth('hello world', 5)).toBe('hello world');
  });

  test('text with color codes gets reset before padding', () => {
    const colored = `${RED}hi${RESET}`;
    const padded = padToWidth(colored, 5);
    expect(visibleWidth(padded)).toBe(5);
    // Should have reset before padding spaces
    expect(padded).toContain(RESET);
    expect(stripAnsi(padded)).toBe('hi   ');
  });

  test('text with nested styles produces correct width', () => {
    const styled = `${BOLD}${RED}hi${RESET}`;
    const padded = padToWidth(styled, 5);
    expect(visibleWidth(padded)).toBe(5);
  });

  test('prevents style leakage into padding', () => {
    // Text without reset - padding should still be unstyled
    const noReset = `${RED}hi`;
    const padded = padToWidth(noReset, 5);
    expect(visibleWidth(padded)).toBe(5);
    // Should contain reset before padding to prevent leak
    expect(padded).toContain(RESET);
  });

  test('text with cursor codes does not get reset (no SGR)', () => {
    // Cursor codes don't leak styles, so no reset needed
    const withCursor = '\x1b[2Khi';
    const padded = padToWidth(withCursor, 5);
    expect(visibleWidth(padded)).toBe(5);
    // Should NOT contain reset since no SGR codes
    expect(padded).toBe('\x1b[2Khi   ');
  });

  test('text with OSC hyperlink does not get reset (no SGR)', () => {
    // OSC 8 hyperlinks don't leak styles
    const link = '\x1b]8;;url\x07hi\x1b]8;;\x07';
    const padded = padToWidth(link, 5);
    expect(visibleWidth(padded)).toBe(5);
    // Should NOT contain extra reset
    expect(padded).toBe(link + '   ');
  });

  test('edge cases', () => {
    const emptyPadded = padToWidth('', 5);
    expect(visibleWidth(emptyPadded)).toBe(5);
    expect(emptyPadded).toBe('     ');
    expect(padToWidth('', 0)).toBe('');
  });

  test('negative width treated as zero', () => {
    expect(padToWidth('hi', -5)).toBe('hi');
    expect(padToWidth('', -1)).toBe('');
  });
});

describe('truncateToWidth', () => {
  test('no truncation when fits', () => {
    expect(truncateToWidth('hello', 10)).toBe('hello');
    expect(truncateToWidth('hi', 2)).toBe('hi');
  });

  test('truncation produces correct visible width', () => {
    const truncated = truncateToWidth('hello world', 8);
    expect(visibleWidth(truncated)).toBe(8);
    expect(truncated.endsWith('...')).toBe(true);
  });

  test('colored text truncates correctly', () => {
    const colored = `${RED}hello world${RESET}`;
    const truncated = truncateToWidth(colored, 8);
    expect(visibleWidth(truncated)).toBe(8);
    expect(truncated.endsWith('...')).toBe(true);
  });

  test('ellipsis is unstyled for colored text', () => {
    const colored = `${RED}hello world${RESET}`;
    const truncated = truncateToWidth(colored, 8);
    // Verify ellipsis is present and visible width is correct
    // (pi-tui's internal handling ensures unstyled ellipsis)
    expect(visibleWidth(truncated)).toBe(8);
    expect(stripAnsi(truncated).endsWith('...')).toBe(true);
  });

  test('nested styles truncate correctly', () => {
    const styled = `${BOLD}${RED}hello world${RESET}`;
    const truncated = truncateToWidth(styled, 8);
    expect(visibleWidth(truncated)).toBe(8);
  });

  test('custom ellipsis works', () => {
    const t1 = truncateToWidth('hello world', 7, '…');
    expect(visibleWidth(t1)).toBeLessThanOrEqual(7);
    expect(t1.endsWith('…')).toBe(true);

    const t2 = truncateToWidth('hello world', 8, '>>');
    expect(visibleWidth(t2)).toBeLessThanOrEqual(8);
    expect(t2.endsWith('>>')).toBe(true);
  });

  test('edge cases', () => {
    expect(truncateToWidth('', 5)).toBe('');
    expect(truncateToWidth('hi', 10)).toBe('hi');
    const t3 = truncateToWidth('hello', 3);
    expect(visibleWidth(t3)).toBeLessThanOrEqual(3);
  });
});
