import chalk from 'chalk';

import type { ColorPalette, Theme } from './index.ts';

import { bgColor, color } from './helpers.ts';

/**
 * Light theme palette - 256 color values for terminal compatibility.
 * Uses -1 for terminal default (transparent background).
 */
export const LIGHT: ColorPalette = {
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

export const lightTheme: Theme = {
  name: 'light',
  palette: LIGHT,

  // Color functions
  text: color(LIGHT.text),
  dim: color(LIGHT.dim),
  accent: color(LIGHT.accent),
  success: color(LIGHT.success),
  progress: color(LIGHT.progress),
  warning: color(LIGHT.warning),
  error: color(LIGHT.error),
  border: color(LIGHT.border),

  // Background functions
  selectedBg: bgColor(LIGHT.selectedBg),

  // pi-tui SelectListTheme (used for TaskList)
  selectList: {
    selectedPrefix: (s) => chalk.ansi256(LIGHT.accent)(s),
    selectedText: (s) =>
      chalk.bgAnsi256(LIGHT.selectedBg).ansi256(LIGHT.text)(s),
    description: (s) => chalk.ansi256(LIGHT.dim)(s),
    scrollInfo: (s) => chalk.ansi256(LIGHT.dim)(s),
    noMatch: (s) => chalk.ansi256(LIGHT.warning)(s),
  },

  // pi-tui MarkdownTheme (used for TaskDetail)
  markdown: {
    heading: (s) => chalk.bold.ansi256(LIGHT.accent)(s),
    link: (s) => chalk.ansi256(LIGHT.accent)(s),
    linkUrl: (s) => chalk.ansi256(LIGHT.dim)(s),
    code: (s) => chalk.ansi256(LIGHT.warning)(s),
    codeBlock: (s) => chalk.ansi256(LIGHT.text)(s),
    codeBlockBorder: (s) => chalk.ansi256(LIGHT.border)(s),
    quote: (s) => chalk.italic.ansi256(LIGHT.dim)(s),
    quoteBorder: (s) => chalk.ansi256(LIGHT.border)(s),
    hr: (s) => chalk.ansi256(LIGHT.border)(s),
    listBullet: (s) => chalk.ansi256(LIGHT.accent)(s),
    bold: (s) => chalk.bold.ansi256(LIGHT.text)(s),
    italic: (s) => chalk.italic.ansi256(LIGHT.text)(s),
    strikethrough: (s) => chalk.strikethrough.ansi256(LIGHT.dim)(s),
    underline: (s) => chalk.underline.ansi256(LIGHT.text)(s),
  },

  // pi-tui EditorTheme
  editor: {
    borderColor: (s) => chalk.ansi256(LIGHT.border)(s),
    selectList: {
      selectedPrefix: (s) => chalk.ansi256(LIGHT.accent)(s),
      selectedText: (s) =>
        chalk.bgAnsi256(LIGHT.selectedBg).ansi256(LIGHT.text)(s),
      description: (s) => chalk.ansi256(LIGHT.dim)(s),
      scrollInfo: (s) => chalk.ansi256(LIGHT.dim)(s),
      noMatch: (s) => chalk.ansi256(LIGHT.warning)(s),
    },
  },
};
