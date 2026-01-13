#!/usr/bin/env bun
/**
 * CLI entry point for flow-next-tui.
 * Parses arguments and starts the TUI.
 */
import { Command } from 'commander';

import { createApp } from './app.ts';

let pkg: { version: string } = { version: '0.0.0' };
try {
  pkg = await Bun.file(new URL('../package.json', import.meta.url)).json();
} catch {
  // Fallback version if package.json unreadable
}

const program = new Command();

program
  .name('flow-next-tui')
  .description('TUI for monitoring Flow-Next Ralph mode runs')
  .version(pkg.version, '-v, --version')
  .option('-l, --light', 'Use light theme')
  .option('--no-emoji', 'Use ASCII icons instead of unicode')
  .option('-r, --run <id>', 'Select specific run')
  .action(
    async (options: { light?: boolean; emoji: boolean; run?: string }) => {
      await createApp({
        light: options.light,
        noEmoji: options.emoji === false,
        run: options.run,
      });
    }
  );

try {
  await program.parseAsync();
} catch (err) {
  const msg = err instanceof Error ? err.message : String(err);
  console.error(`Error: ${msg}`);
  process.exit(1);
}
