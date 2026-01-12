/**
 * ANSI-aware rendering utilities for terminal width/padding/truncation.
 * Re-exports from pi-tui where available, implements missing utilities.
 */

import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";

// Re-export from pi-tui
export { truncateToWidth, visibleWidth };

/**
 * ANSI escape code patterns matching pi-tui's internal stripping for consistency.
 * Matches what visibleWidth() ignores:
 * - SGR codes: \x1b[...m (colors, styles)
 * - Cursor codes: \x1b[...G/K/H/J (position, clear)
 * - OSC 8 hyperlinks: \x1b]8;;...\x07
 *
 * Note: This intentionally matches pi-tui's scope, not all possible ANSI codes,
 * to ensure stripAnsi() and visibleWidth() are consistent.
 */
// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1b\[[0-9;]*[mGKHJ]|\x1b\]8;;[^\x07]*\x07/g;

/**
 * Strip ANSI escape codes from text.
 * Strips the same codes that visibleWidth() ignores (SGR, cursor, OSC 8).
 */
export function stripAnsi(text: string): string {
	return text.replace(ANSI_REGEX, "");
}

/**
 * Pad text to exact visible width (handles ANSI codes).
 * Adds spaces to reach target width, returns unchanged if already at/over width.
 * Negative width treated as 0.
 */
export function padToWidth(text: string, width: number): string {
	const targetWidth = Math.max(0, width);
	const currentWidth = visibleWidth(text);
	if (currentWidth >= targetWidth) {
		return text;
	}
	return text + " ".repeat(targetWidth - currentWidth);
}
