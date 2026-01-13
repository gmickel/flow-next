import { describe, expect, test } from 'bun:test';

import { DARK, LIGHT, darkTheme, getTheme, lightTheme } from '../src/themes';

describe('themes', () => {
  test('getTheme returns dark theme by default', () => {
    const theme = getTheme();
    expect(theme.name).toBe('dark');
  });

  test('getTheme(true) returns light theme', () => {
    const theme = getTheme(true);
    expect(theme.name).toBe('light');
  });

  test('DARK and LIGHT are palette objects', () => {
    // Per spec, DARK/LIGHT are ColorPalette (not Theme)
    expect(typeof DARK.accent).toBe('number');
    expect(typeof LIGHT.accent).toBe('number');
    // They should NOT have theme methods
    expect((DARK as unknown as Record<string, unknown>).name).toBeUndefined();
    expect((LIGHT as unknown as Record<string, unknown>).name).toBeUndefined();
  });

  test('darkTheme and lightTheme are theme objects', () => {
    expect(darkTheme.name).toBe('dark');
    expect(lightTheme.name).toBe('light');
  });

  test('DARK palette matches spec values', () => {
    expect(DARK.accent).toBe(50); // vibrant teal-cyan
    expect(DARK.success).toBe(78); // brighter green
    expect(DARK.progress).toBe(39); // vivid blue
    expect(DARK.warning).toBe(214); // bright orange-amber
    expect(DARK.error).toBe(196); // vivid red
    expect(DARK.text).toBe(255); // pure white
    expect(DARK.dim).toBe(245); // brighter dim
    expect(DARK.border).toBe(240);
    expect(DARK.selectedBg).toBe(238);
    expect(DARK.bg).toBe(-1); // terminal default
  });

  test('LIGHT palette has valid values', () => {
    expect(LIGHT.bg).toBe(-1); // terminal default
    expect(typeof LIGHT.accent).toBe('number');
    expect(typeof LIGHT.text).toBe('number');
    expect(typeof LIGHT.error).toBe('number');
  });

  test('darkTheme has color functions', () => {
    expect(typeof darkTheme.text).toBe('function');
    expect(typeof darkTheme.dim).toBe('function');
    expect(typeof darkTheme.accent).toBe('function');
    expect(typeof darkTheme.success).toBe('function');
    expect(typeof darkTheme.progress).toBe('function');
    expect(typeof darkTheme.warning).toBe('function');
    expect(typeof darkTheme.error).toBe('function');
    expect(typeof darkTheme.border).toBe('function');
    expect(typeof darkTheme.selectedBg).toBe('function');
  });

  test('lightTheme has color functions', () => {
    expect(typeof lightTheme.text).toBe('function');
    expect(typeof lightTheme.dim).toBe('function');
    expect(typeof lightTheme.accent).toBe('function');
    expect(typeof lightTheme.success).toBe('function');
    expect(typeof lightTheme.progress).toBe('function');
    expect(typeof lightTheme.warning).toBe('function');
    expect(typeof lightTheme.error).toBe('function');
    expect(typeof lightTheme.border).toBe('function');
    expect(typeof lightTheme.selectedBg).toBe('function');
  });

  test('color functions return strings', () => {
    expect(typeof darkTheme.text('test')).toBe('string');
    expect(typeof darkTheme.accent('test')).toBe('string');
    expect(typeof lightTheme.text('test')).toBe('string');
    expect(typeof lightTheme.accent('test')).toBe('string');
  });

  test('darkTheme has pi-tui compatible selectList theme', () => {
    expect(typeof darkTheme.selectList.selectedPrefix).toBe('function');
    expect(typeof darkTheme.selectList.selectedText).toBe('function');
    expect(typeof darkTheme.selectList.description).toBe('function');
    expect(typeof darkTheme.selectList.scrollInfo).toBe('function');
    expect(typeof darkTheme.selectList.noMatch).toBe('function');
  });

  test('lightTheme has pi-tui compatible selectList theme', () => {
    expect(typeof lightTheme.selectList.selectedPrefix).toBe('function');
    expect(typeof lightTheme.selectList.selectedText).toBe('function');
    expect(typeof lightTheme.selectList.description).toBe('function');
    expect(typeof lightTheme.selectList.scrollInfo).toBe('function');
    expect(typeof lightTheme.selectList.noMatch).toBe('function');
  });

  test('darkTheme has pi-tui compatible markdown theme', () => {
    expect(typeof darkTheme.markdown.heading).toBe('function');
    expect(typeof darkTheme.markdown.link).toBe('function');
    expect(typeof darkTheme.markdown.code).toBe('function');
    expect(typeof darkTheme.markdown.codeBlock).toBe('function');
    expect(typeof darkTheme.markdown.bold).toBe('function');
    expect(typeof darkTheme.markdown.italic).toBe('function');
  });

  test('lightTheme has pi-tui compatible markdown theme', () => {
    expect(typeof lightTheme.markdown.heading).toBe('function');
    expect(typeof lightTheme.markdown.link).toBe('function');
    expect(typeof lightTheme.markdown.code).toBe('function');
    expect(typeof lightTheme.markdown.codeBlock).toBe('function');
    expect(typeof lightTheme.markdown.bold).toBe('function');
    expect(typeof lightTheme.markdown.italic).toBe('function');
  });

  test('darkTheme has pi-tui compatible editor theme', () => {
    expect(typeof darkTheme.editor.borderColor).toBe('function');
    expect(darkTheme.editor.selectList).toBeDefined();
    expect(typeof darkTheme.editor.selectList.selectedPrefix).toBe('function');
  });

  test('lightTheme has pi-tui compatible editor theme', () => {
    expect(typeof lightTheme.editor.borderColor).toBe('function');
    expect(lightTheme.editor.selectList).toBeDefined();
    expect(typeof lightTheme.editor.selectList.selectedPrefix).toBe('function');
  });
});
