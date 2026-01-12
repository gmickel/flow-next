import chalk from "chalk";
import type { ColorPalette, Theme } from "./index.ts";

/**
 * Dark theme - 256 color palette for terminal compatibility.
 * Uses terminal default background for transparency support.
 */
export const DARK_PALETTE: ColorPalette = {
	bg: -1, // terminal default (transparent)
	border: 239,
	text: 252,
	dim: 242,
	accent: 81, // electric cyan
	success: 114, // muted green
	progress: 75, // bright blue
	warning: 221, // amber
	error: 203, // coral red
	selectedBg: 236,
};

// Color helper functions using 256-color ANSI
const c = (code: number) => (s: string) =>
	code === -1 ? s : chalk.ansi256(code)(s);
const bg = (code: number) => (s: string) =>
	code === -1 ? s : chalk.bgAnsi256(code)(s);

export const darkTheme: Theme = {
	name: "dark",
	palette: DARK_PALETTE,

	// Color functions
	text: c(DARK_PALETTE.text),
	dim: c(DARK_PALETTE.dim),
	accent: c(DARK_PALETTE.accent),
	success: c(DARK_PALETTE.success),
	progress: c(DARK_PALETTE.progress),
	warning: c(DARK_PALETTE.warning),
	error: c(DARK_PALETTE.error),
	border: c(DARK_PALETTE.border),

	// Background functions
	selectedBg: bg(DARK_PALETTE.selectedBg),

	// pi-tui SelectListTheme (used for TaskList)
	selectList: {
		selectedPrefix: (s) => chalk.ansi256(DARK_PALETTE.accent)(s),
		selectedText: (s) =>
			chalk.bgAnsi256(DARK_PALETTE.selectedBg).ansi256(DARK_PALETTE.text)(s),
		description: (s) => chalk.ansi256(DARK_PALETTE.dim)(s),
		scrollInfo: (s) => chalk.ansi256(DARK_PALETTE.dim)(s),
		noMatch: (s) => chalk.ansi256(DARK_PALETTE.warning)(s),
	},

	// pi-tui MarkdownTheme (used for TaskDetail)
	markdown: {
		heading: (s) => chalk.bold.ansi256(DARK_PALETTE.accent)(s),
		link: (s) => chalk.ansi256(DARK_PALETTE.accent)(s),
		linkUrl: (s) => chalk.ansi256(DARK_PALETTE.dim)(s),
		code: (s) => chalk.ansi256(DARK_PALETTE.warning)(s),
		codeBlock: (s) => chalk.ansi256(DARK_PALETTE.text)(s),
		codeBlockBorder: (s) => chalk.ansi256(DARK_PALETTE.border)(s),
		quote: (s) => chalk.italic.ansi256(DARK_PALETTE.dim)(s),
		quoteBorder: (s) => chalk.ansi256(DARK_PALETTE.border)(s),
		hr: (s) => chalk.ansi256(DARK_PALETTE.border)(s),
		listBullet: (s) => chalk.ansi256(DARK_PALETTE.accent)(s),
		bold: (s) => chalk.bold.ansi256(DARK_PALETTE.text)(s),
		italic: (s) => chalk.italic.ansi256(DARK_PALETTE.text)(s),
		strikethrough: (s) => chalk.strikethrough.ansi256(DARK_PALETTE.dim)(s),
		underline: (s) => chalk.underline.ansi256(DARK_PALETTE.text)(s),
	},

	// pi-tui EditorTheme
	editor: {
		borderColor: (s) => chalk.ansi256(DARK_PALETTE.border)(s),
		selectList: {
			selectedPrefix: (s) => chalk.ansi256(DARK_PALETTE.accent)(s),
			selectedText: (s) =>
				chalk.bgAnsi256(DARK_PALETTE.selectedBg).ansi256(DARK_PALETTE.text)(s),
			description: (s) => chalk.ansi256(DARK_PALETTE.dim)(s),
			scrollInfo: (s) => chalk.ansi256(DARK_PALETTE.dim)(s),
			noMatch: (s) => chalk.ansi256(DARK_PALETTE.warning)(s),
		},
	},
};
