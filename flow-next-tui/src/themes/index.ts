import type {
  EditorTheme,
  MarkdownTheme,
  SelectListTheme,
} from '@mariozechner/pi-tui';

import { DARK, darkTheme } from './dark.ts';
import { LIGHT, lightTheme } from './light.ts';

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

// Re-export pi-tui theme types for convenience
export type { EditorTheme, MarkdownTheme, SelectListTheme };

// Re-export palettes (DARK/LIGHT are ColorPalette objects per spec)
export { DARK, LIGHT };

// Re-export theme objects
export { darkTheme, lightTheme };

/**
 * Get theme by preference.
 * @param isLight - If true, returns light theme; otherwise dark theme (default).
 */
export function getTheme(isLight = false): Theme {
  return isLight ? lightTheme : darkTheme;
}
