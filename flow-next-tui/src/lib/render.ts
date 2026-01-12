/**
 * ANSI-aware rendering utilities for terminal width/padding/truncation.
 * Re-exports from pi-tui where available, implements missing utilities.
 */

import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";

// Re-export from pi-tui
export { truncateToWidth, visibleWidth };

/**
 * Regex for common ANSI escape codes:
 * - SGR codes: \x1b[...m (colors, styles)
 * - Cursor codes: \x1b[...G/K/H/J (position, clear)
 * - OSC 8 hyperlinks: \x1b]8;;...\x07
 *
 * Note: This covers common terminal codes but not all ANSI sequences.
 * For comprehensive stripping, consider a dedicated library like strip-ansi.
 */
// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1b\[[0-9;]*[mGKHJ]|\x1b\]8;;[^\x07]*\x07/g;

/**
 * Strip common ANSI escape codes from text (SGR, cursor, OSC 8 hyperlinks).
 * Does not strip all possible ANSI sequences - covers typical terminal output.
 */
export function stripAnsi(text: string): string {
	return text.replace(ANSI_REGEX, "");
}

/**
 * Pad text to exact visible width (handles ANSI codes).
 * Adds spaces to reach target width, returns unchanged if already at/over width.
 * Negative width treated as 0.
 *
 * Note: Does not add ANSI reset before padding. If text ends with active styles,
 * the caller is responsible for adding reset codes before calling this function.
 */
export function padToWidth(text: string, width: number): string {
	const targetWidth = Math.max(0, width);
	const currentWidth = visibleWidth(text);
	if (currentWidth >= targetWidth) {
		return text;
	}
	return text + " ".repeat(targetWidth - currentWidth);
}
