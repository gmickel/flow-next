import chalk from 'chalk';

/**
 * Create a foreground color function from 256-color code.
 * -1 means transparent/no color.
 */
export const color =
  (code: number) =>
  (s: string): string =>
    code === -1 ? s : chalk.ansi256(code)(s);

/**
 * Create a background color function from 256-color code.
 * -1 means transparent/no background.
 */
export const bgColor =
  (code: number) =>
  (s: string): string =>
    code === -1 ? s : chalk.bgAnsi256(code)(s);
