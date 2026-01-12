import type {
	EditorTheme,
	MarkdownTheme,
	SelectListTheme,
} from "@mariozechner/pi-tui";

/**
 * 256-color palette definition.
 * Uses -1 for terminal default (transparent background).
 */
export interface ColorPalette {
	bg: number;
	border: number;
	text: number;
	dim: number;
	accent: number;
	success: number;
	progress: number;
	warning: number;
	error: number;
	selectedBg: number;
}

/** Color function type - applies color to a string */
export type ColorFn = (s: string) => string;

/**
 * Complete theme with color functions and pi-tui compatible theme objects.
 */
export interface Theme {
	name: string;
	palette: ColorPalette;

	// Color functions
	text: ColorFn;
	dim: ColorFn;
	accent: ColorFn;
	success: ColorFn;
	progress: ColorFn;
	warning: ColorFn;
	error: ColorFn;
	border: ColorFn;

	// Background functions
	selectedBg: ColorFn;

	// pi-tui compatible themes
	selectList: SelectListTheme;
	markdown: MarkdownTheme;
	editor: EditorTheme;
}

// Re-export themes
export { DARK_PALETTE, darkTheme } from "./dark.ts";
export { LIGHT_PALETTE, lightTheme } from "./light.ts";

// Re-export pi-tui theme types for convenience
export type { EditorTheme, MarkdownTheme, SelectListTheme };

// Import for getTheme
import { darkTheme } from "./dark.ts";
import { lightTheme } from "./light.ts";

/**
 * Get theme by preference.
 * @param isLight - If true, returns light theme; otherwise dark theme (default).
 */
export function getTheme(isLight = false): Theme {
	return isLight ? lightTheme : darkTheme;
}

// Convenience aliases
export const DARK = darkTheme;
export const LIGHT = lightTheme;
