import chalk from "chalk";
import type { ColorPalette, Theme } from "./index.ts";

/**
 * Light theme - 256 color palette for terminal compatibility.
 * Uses terminal default background for transparency support.
 */
export const LIGHT_PALETTE: ColorPalette = {
	bg: -1, // terminal default (transparent)
	border: 250,
	text: 235,
	dim: 245,
	accent: 32, // blue
	success: 34, // green
	progress: 27, // bright blue
	warning: 136, // orange/brown
	error: 160, // red
	selectedBg: 254,
};

// Color helper functions using 256-color ANSI
const c = (code: number) => (s: string) =>
	code === -1 ? s : chalk.ansi256(code)(s);
const bg = (code: number) => (s: string) =>
	code === -1 ? s : chalk.bgAnsi256(code)(s);

export const lightTheme: Theme = {
	name: "light",
	palette: LIGHT_PALETTE,

	// Color functions
	text: c(LIGHT_PALETTE.text),
	dim: c(LIGHT_PALETTE.dim),
	accent: c(LIGHT_PALETTE.accent),
	success: c(LIGHT_PALETTE.success),
	progress: c(LIGHT_PALETTE.progress),
	warning: c(LIGHT_PALETTE.warning),
	error: c(LIGHT_PALETTE.error),
	border: c(LIGHT_PALETTE.border),

	// Background functions
	selectedBg: bg(LIGHT_PALETTE.selectedBg),

	// pi-tui SelectListTheme (used for TaskList)
	selectList: {
		selectedPrefix: (s) => chalk.ansi256(LIGHT_PALETTE.accent)(s),
		selectedText: (s) =>
			chalk.bgAnsi256(LIGHT_PALETTE.selectedBg).ansi256(LIGHT_PALETTE.text)(s),
		description: (s) => chalk.ansi256(LIGHT_PALETTE.dim)(s),
		scrollInfo: (s) => chalk.ansi256(LIGHT_PALETTE.dim)(s),
		noMatch: (s) => chalk.ansi256(LIGHT_PALETTE.warning)(s),
	},

	// pi-tui MarkdownTheme (used for TaskDetail)
	markdown: {
		heading: (s) => chalk.bold.ansi256(LIGHT_PALETTE.accent)(s),
		link: (s) => chalk.ansi256(LIGHT_PALETTE.accent)(s),
		linkUrl: (s) => chalk.ansi256(LIGHT_PALETTE.dim)(s),
		code: (s) => chalk.ansi256(LIGHT_PALETTE.warning)(s),
		codeBlock: (s) => chalk.ansi256(LIGHT_PALETTE.text)(s),
		codeBlockBorder: (s) => chalk.ansi256(LIGHT_PALETTE.border)(s),
		quote: (s) => chalk.italic.ansi256(LIGHT_PALETTE.dim)(s),
		quoteBorder: (s) => chalk.ansi256(LIGHT_PALETTE.border)(s),
		hr: (s) => chalk.ansi256(LIGHT_PALETTE.border)(s),
		listBullet: (s) => chalk.ansi256(LIGHT_PALETTE.accent)(s),
		bold: (s) => chalk.bold.ansi256(LIGHT_PALETTE.text)(s),
		italic: (s) => chalk.italic.ansi256(LIGHT_PALETTE.text)(s),
		strikethrough: (s) => chalk.strikethrough.ansi256(LIGHT_PALETTE.dim)(s),
		underline: (s) => chalk.underline.ansi256(LIGHT_PALETTE.text)(s),
	},

	// pi-tui EditorTheme
	editor: {
		borderColor: (s) => chalk.ansi256(LIGHT_PALETTE.border)(s),
		selectList: {
			selectedPrefix: (s) => chalk.ansi256(LIGHT_PALETTE.accent)(s),
			selectedText: (s) =>
				chalk.bgAnsi256(LIGHT_PALETTE.selectedBg).ansi256(LIGHT_PALETTE.text)(
					s,
				),
			description: (s) => chalk.ansi256(LIGHT_PALETTE.dim)(s),
			scrollInfo: (s) => chalk.ansi256(LIGHT_PALETTE.dim)(s),
			noMatch: (s) => chalk.ansi256(LIGHT_PALETTE.warning)(s),
		},
	},
};
