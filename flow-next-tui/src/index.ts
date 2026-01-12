#!/usr/bin/env bun
import { Command } from "commander";
import { TUI } from "@mariozechner/pi-tui";

const program = new Command();

program
	.name("flow-next-tui")
	.description("TUI for monitoring Flow-Next Ralph mode runs")
	.version("0.1.0")
	.option("-l, --light", "Use light theme")
	.option("--no-emoji", "Use ASCII-only icons")
	.argument("[run]", "Run directory to monitor")
	.action(async (run, options) => {
		console.log("flow-next-tui starting...");
		console.log("Run:", run ?? "auto-detect");
		console.log("Options:", options);

		// Placeholder - will initialize TUI in later tasks
		console.log("TUI available:", typeof TUI);
	});

program.parse();
