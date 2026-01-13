import chalk from 'chalk';

import type { ColorPalette, Theme } from './index.ts';

import { bgColor, color } from './helpers.ts';

/**
 * Dark theme palette - 256 color values for terminal compatibility.
 * Inspired by modern terminal UIs with vibrant cyan accent.
 * Uses -1 for terminal default (transparent background).
 */
export const DARK: ColorPalette = {
  bg: -1, // terminal default (transparent)
  border: 240, // slightly brighter border for visibility
  text: 255, // pure white for max contrast
  dim: 245, // brighter dim for better readability
  accent: 50, // vibrant teal-cyan (pops more than 81)
  success: 78, // brighter green
  progress: 39, // vivid blue
  warning: 214, // bright orange-amber
  error: 196, // vivid red
  selectedBg: 238, // slightly lighter selection
};

export const darkTheme: Theme = {
  name: 'dark',
  palette: DARK,

  // Color functions
  text: color(DARK.text),
  dim: color(DARK.dim),
  accent: color(DARK.accent),
  success: color(DARK.success),
  progress: color(DARK.progress),
  warning: color(DARK.warning),
  error: color(DARK.error),
  border: color(DARK.border),

  // Background functions
  selectedBg: bgColor(DARK.selectedBg),

  // pi-tui SelectListTheme (used for TaskList)
  selectList: {
    selectedPrefix: (s) => chalk.ansi256(DARK.accent)(s),
    selectedText: (s) => chalk.bgAnsi256(DARK.selectedBg).ansi256(DARK.text)(s),
    description: (s) => chalk.ansi256(DARK.dim)(s),
    scrollInfo: (s) => chalk.ansi256(DARK.dim)(s),
    noMatch: (s) => chalk.ansi256(DARK.warning)(s),
  },

  // pi-tui MarkdownTheme (used for TaskDetail)
  markdown: {
    heading: (s) => chalk.bold.ansi256(DARK.accent)(s),
    link: (s) => chalk.ansi256(DARK.accent)(s),
    linkUrl: (s) => chalk.ansi256(DARK.dim)(s),
    code: (s) => chalk.ansi256(DARK.warning)(s),
    codeBlock: (s) => chalk.ansi256(DARK.text)(s),
    codeBlockBorder: (s) => chalk.ansi256(DARK.border)(s),
    quote: (s) => chalk.italic.ansi256(DARK.dim)(s),
    quoteBorder: (s) => chalk.ansi256(DARK.border)(s),
    hr: (s) => chalk.ansi256(DARK.border)(s),
    listBullet: (s) => chalk.ansi256(DARK.accent)(s),
    bold: (s) => chalk.bold.ansi256(DARK.text)(s),
    italic: (s) => chalk.italic.ansi256(DARK.text)(s),
    strikethrough: (s) => chalk.strikethrough.ansi256(DARK.dim)(s),
    underline: (s) => chalk.underline.ansi256(DARK.text)(s),
  },

  // pi-tui EditorTheme
  editor: {
    borderColor: (s) => chalk.ansi256(DARK.border)(s),
    selectList: {
      selectedPrefix: (s) => chalk.ansi256(DARK.accent)(s),
      selectedText: (s) =>
        chalk.bgAnsi256(DARK.selectedBg).ansi256(DARK.text)(s),
      description: (s) => chalk.ansi256(DARK.dim)(s),
      scrollInfo: (s) => chalk.ansi256(DARK.dim)(s),
      noMatch: (s) => chalk.ansi256(DARK.warning)(s),
    },
  },
};
