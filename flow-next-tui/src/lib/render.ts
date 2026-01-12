/**
 * ANSI-aware rendering utilities for terminal width/padding/truncation.
 * Re-exports from pi-tui where available, implements missing utilities.
 */

import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";

// Re-export from pi-tui
export { truncateToWidth, visibleWidth };

// ANSI escape code patterns (matches SGR, cursor, and OSC sequences)
// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1b\[[0-9;]*[mGKHJ]|\x1b\]8;;[^\x07]*\x07/g;

/**
 * Strip all ANSI escape codes from text.
 */
export function stripAnsi(text: string): string {
	return text.replace(ANSI_REGEX, "");
}

/**
 * Pad text to exact visible width (handles ANSI codes).
 * Adds spaces to reach target width, does nothing if already at/over width.
 */
export function padToWidth(text: string, width: number): string {
	const currentWidth = visibleWidth(text);
	if (currentWidth >= width) {
		return text;
	}
	return text + " ".repeat(width - currentWidth);
}
