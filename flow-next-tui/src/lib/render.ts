/**
 * ANSI-aware rendering utilities for terminal width/padding/truncation.
 * Re-exports from pi-tui where available, implements missing utilities.
 */

import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";

// Re-export from pi-tui
export { truncateToWidth, visibleWidth };

/**
 * Comprehensive ANSI escape sequence regex.
 * Matches:
 * - CSI sequences: \x1b[ followed by params and final byte (covers SGR, cursor, etc)
 * - OSC sequences: \x1b] followed by data and terminator (BEL \x07 or ST \x1b\\)
 * - Simple escape sequences: \x1b followed by single char (like \x1bc for reset)
 */
// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-_a-z]/g;

/**
 * Strip ANSI escape codes from text.
 * Handles CSI sequences (colors, cursor), OSC sequences (hyperlinks, titles),
 * and simple escape sequences.
 */
export function stripAnsi(text: string): string {
	return text.replace(ANSI_REGEX, "");
}

const RESET = "\x1b[0m";

/**
 * Pad text to exact visible width (handles ANSI codes).
 * Adds spaces to reach target width, returns unchanged if already at/over width.
 * Negative width treated as 0.
 *
 * Automatically adds ANSI reset before padding to prevent style leakage.
 */
export function padToWidth(text: string, width: number): string {
	const targetWidth = Math.max(0, width);
	const currentWidth = visibleWidth(text);
	if (currentWidth >= targetWidth) {
		return text;
	}
	const padding = " ".repeat(targetWidth - currentWidth);
	// Add reset before padding to prevent style leaking into spaces
	return text + RESET + padding;
}
