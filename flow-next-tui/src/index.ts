#!/usr/bin/env bun
/**
 * CLI entry point for flow-next-tui.
 * Parses arguments and starts the TUI.
 */
import { Command } from 'commander';
import { createApp } from './app.ts';

const pkg = await Bun.file(new URL('../package.json', import.meta.url)).json();

const program = new Command();

program
  .name('flow-next-tui')
  .description('TUI for monitoring Flow-Next Ralph mode runs')
  .version(pkg.version)
  .option('-l, --light', 'Use light theme')
  .option('--no-emoji', 'Use ASCII icons instead of unicode')
  .option('-r, --run <id>', 'Select specific run')
  .action(async (options: { light?: boolean; emoji: boolean; run?: string }) => {
    await createApp({
      light: options.light,
      noEmoji: !options.emoji,
      run: options.run,
    });
  });

// Handle signals before parsing (in case parsing hangs)
process.on('SIGINT', () => process.exit(0));
process.on('SIGTERM', () => process.exit(0));

await program.parseAsync();
