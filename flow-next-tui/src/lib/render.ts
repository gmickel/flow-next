/**
 * Terminal escape-aware rendering utilities for width/padding/truncation.
 *
 * Re-exports truncateToWidth from pi-tui.
 * Implements visibleWidth (wraps pi-tui with comprehensive stripping),
 * stripAnsi, and padToWidth locally.
 *
 * stripAnsi removes all terminal escape sequences, not just ANSI SGR styling:
 * CSI sequences, OSC sequences, charset designators, and simple escapes.
 */

import {
  truncateToWidth,
  visibleWidth as piTuiVisibleWidth,
} from '@mariozechner/pi-tui';

// Re-export truncateToWidth from pi-tui
export { truncateToWidth };

/**
 * Comprehensive ANSI escape sequence regex.
 * Matches:
 * - CSI sequences: \x1b[ followed by params and final byte (covers SGR, cursor, etc)
 * - OSC sequences: \x1b] followed by data and terminator (BEL \x07 or ST \x1b\\)
 * - Simple escape sequences: \x1b followed by single char (ESC7, ESC8, ESCc, etc)
 * - Charset designators: \x1b( or \x1b) followed by charset (B, 0, etc)
 */
// eslint-disable-next-line no-control-regex
const ANSI_REGEX =
  /\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Z0-9]|\x1b[0-9A-Za-z@-_]/g;

/**
 * Strip ANSI escape codes from text.
 * Handles CSI sequences (colors, cursor, private mode), OSC sequences
 * (hyperlinks, titles), charset designators, and simple escape sequences.
 */
export function stripAnsi(text: string): string {
  return text.replace(ANSI_REGEX, '');
}

const RESET = '\x1b[0m';
// Detect if text contains SGR sequences (CSI ending with 'm') that could leak styles
// eslint-disable-next-line no-control-regex
const HAS_SGR_REGEX = /\x1b\[[0-9;]*m/;

/**
 * Get the visible width of a string in terminal columns.
 * Strips all ANSI codes before measuring to ensure accurate width calculation.
 * Handles wide characters and emoji via pi-tui's width calculation.
 */
export function visibleWidth(text: string): number {
  // Strip all ANSI codes first to ensure accurate measurement
  const stripped = stripAnsi(text);
  return piTuiVisibleWidth(stripped);
}

/**
 * Pad text to exact visible width (handles ANSI codes).
 * Adds spaces to reach target width, returns unchanged if already at/over width.
 * Negative width treated as 0.
 *
 * If text contains SGR style codes (colors, bold, etc), adds reset before padding
 * to prevent style leakage. Non-SGR ANSI codes (cursor, OSC) don't trigger reset.
 * Plain text without ANSI is padded directly without modification.
 */
export function padToWidth(text: string, width: number): string {
  const targetWidth = Math.max(0, width);
  const currentWidth = visibleWidth(text);
  if (currentWidth >= targetWidth) {
    return text;
  }
  const padding = ' '.repeat(targetWidth - currentWidth);
  // Only add reset if text contains SGR codes that could leak styles
  if (HAS_SGR_REGEX.test(text)) {
    return text + RESET + padding;
  }
  return text + padding;
}
