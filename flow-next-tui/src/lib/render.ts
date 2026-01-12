/**
 * ANSI-aware rendering utilities for terminal width/padding/truncation.
 * Re-exports truncateToWidth from pi-tui, implements others locally for
 * comprehensive ANSI handling.
 */

import {
	truncateToWidth,
	visibleWidth as piTuiVisibleWidth,
} from "@mariozechner/pi-tui";

// Re-export truncateToWidth from pi-tui
export { truncateToWidth };

/**
 * Comprehensive ANSI escape sequence regex.
 * Matches:
 * - CSI sequences: \x1b[ followed by params and final byte (covers SGR, cursor, etc)
 * - OSC sequences: \x1b] followed by data and terminator (BEL \x07 or ST \x1b\\)
 * - Simple escape sequences: \x1b followed by single char (ESC7, ESC8, ESCc, etc)
 */
// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[0-9A-Za-z@-_]/g;

/**
 * Strip ANSI escape codes from text.
 * Handles CSI sequences (colors, cursor, private mode), OSC sequences
 * (hyperlinks, titles), and simple escape sequences.
 */
export function stripAnsi(text: string): string {
	return text.replace(ANSI_REGEX, "");
}

const RESET = "\x1b[0m";
// Check if text contains any ANSI escape sequences
// eslint-disable-next-line no-control-regex
const HAS_ANSI_REGEX = /\x1b/;

/**
 * Get the visible width of a string in terminal columns.
 * Strips ANSI codes before measuring. Handles wide characters and emoji.
 */
export function visibleWidth(text: string): number {
	// Strip all ANSI codes first, then measure
	const stripped = stripAnsi(text);
	return piTuiVisibleWidth(stripped);
}

/**
 * Pad text to exact visible width (handles ANSI codes).
 * Adds spaces to reach target width, returns unchanged if already at/over width.
 * Negative width treated as 0.
 *
 * If text contains ANSI codes, adds reset before padding to prevent style leakage.
 * Plain text without ANSI is padded directly without modification.
 */
export function padToWidth(text: string, width: number): string {
	const targetWidth = Math.max(0, width);
	const currentWidth = visibleWidth(text);
	if (currentWidth >= targetWidth) {
		return text;
	}
	const padding = " ".repeat(targetWidth - currentWidth);
	// Only add reset if text contains ANSI codes to prevent style leak
	if (HAS_ANSI_REGEX.test(text)) {
		return text + RESET + padding;
	}
	return text + padding;
}
