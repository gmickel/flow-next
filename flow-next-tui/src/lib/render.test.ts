import { describe, expect, test } from "bun:test";
import { padToWidth, stripAnsi, truncateToWidth, visibleWidth } from "./render";

// ANSI escape codes for testing
const RED = "\x1b[31m";
const GREEN = "\x1b[32m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

describe("visibleWidth", () => {
	test("plain text", () => {
		expect(visibleWidth("hello")).toBe(5);
		expect(visibleWidth("")).toBe(0);
		expect(visibleWidth("a b c")).toBe(5);
	});

	test("text with color codes", () => {
		expect(visibleWidth(`${RED}hello${RESET}`)).toBe(5);
		expect(visibleWidth(`${GREEN}world${RESET}`)).toBe(5);
	});

	test("text with nested styles", () => {
		expect(visibleWidth(`${BOLD}${RED}bold red${RESET}`)).toBe(8);
		expect(visibleWidth(`${RED}red ${GREEN}green${RESET}`)).toBe(9);
	});

	test("edge cases", () => {
		expect(visibleWidth("")).toBe(0);
		expect(visibleWidth(`${RESET}`)).toBe(0);
		expect(visibleWidth(`${RED}${RESET}`)).toBe(0);
	});
});

describe("stripAnsi", () => {
	test("plain text unchanged", () => {
		expect(stripAnsi("hello")).toBe("hello");
		expect(stripAnsi("")).toBe("");
	});

	test("removes color codes", () => {
		expect(stripAnsi(`${RED}hello${RESET}`)).toBe("hello");
		expect(stripAnsi(`${GREEN}world${RESET}`)).toBe("world");
	});

	test("removes nested styles", () => {
		expect(stripAnsi(`${BOLD}${RED}bold red${RESET}`)).toBe("bold red");
		expect(stripAnsi(`${RED}red ${GREEN}green${RESET}`)).toBe("red green");
	});

	test("removes cursor/SGR codes", () => {
		expect(stripAnsi("\x1b[2Kcleared")).toBe("cleared");
		expect(stripAnsi("\x1b[1Gmoved")).toBe("moved");
	});

	test("removes OSC 8 hyperlinks", () => {
		const link = "\x1b]8;;https://example.com\x07Click\x1b]8;;\x07";
		expect(stripAnsi(link)).toBe("Click");
	});

	test("edge cases", () => {
		expect(stripAnsi("")).toBe("");
		expect(stripAnsi(`${RESET}`)).toBe("");
		expect(stripAnsi(`${RED}${GREEN}${RESET}`)).toBe("");
	});
});

describe("padToWidth", () => {
	test("plain text", () => {
		expect(padToWidth("hi", 5)).toBe("hi   ");
		expect(padToWidth("hello", 5)).toBe("hello");
		expect(padToWidth("hello world", 5)).toBe("hello world");
	});

	test("text with color codes", () => {
		const colored = `${RED}hi${RESET}`;
		const padded = padToWidth(colored, 5);
		expect(visibleWidth(padded)).toBe(5);
		expect(padded).toBe(`${RED}hi${RESET}   `);
	});

	test("text with nested styles", () => {
		const styled = `${BOLD}${RED}hi${RESET}`;
		const padded = padToWidth(styled, 5);
		expect(visibleWidth(padded)).toBe(5);
	});

	test("edge cases", () => {
		expect(padToWidth("", 5)).toBe("     ");
		expect(padToWidth("hello", 5)).toBe("hello");
		expect(padToWidth("hello!", 5)).toBe("hello!");
		expect(padToWidth("", 0)).toBe("");
	});

	test("negative width treated as zero", () => {
		expect(padToWidth("hi", -5)).toBe("hi");
		expect(padToWidth("", -1)).toBe("");
	});
});

describe("truncateToWidth", () => {
	test("plain text no truncation", () => {
		expect(truncateToWidth("hello", 10)).toBe("hello");
		expect(truncateToWidth("hi", 2)).toBe("hi");
	});

	test("plain text truncation produces exact width", () => {
		// pi-tui adds ANSI reset before ellipsis to prevent style leaking
		const truncated = truncateToWidth("hello world", 8);
		// When truncation occurs, result should be exactly target width
		expect(visibleWidth(truncated)).toBe(8);
		// Should end with default ellipsis
		expect(truncated.endsWith("...")).toBe(true);
	});

	test("text with color codes truncates to exact width", () => {
		const colored = `${RED}hello world${RESET}`;
		const truncated = truncateToWidth(colored, 8);
		expect(visibleWidth(truncated)).toBe(8);
		expect(truncated.endsWith("...")).toBe(true);
	});

	test("preserves ANSI reset before ellipsis", () => {
		// pi-tui inserts reset before ellipsis to prevent style leaking
		const colored = `${RED}hello world${RESET}`;
		const truncated = truncateToWidth(colored, 8);
		// Should contain reset code somewhere before the ellipsis
		expect(truncated).toContain(RESET);
		// Ellipsis should appear after reset (no red style on dots)
		const resetIndex = truncated.lastIndexOf(RESET);
		const ellipsisIndex = truncated.indexOf("...");
		expect(resetIndex).toBeLessThan(ellipsisIndex);
	});

	test("text with nested styles truncates to exact width", () => {
		const styled = `${BOLD}${RED}hello world${RESET}`;
		const truncated = truncateToWidth(styled, 8);
		expect(visibleWidth(truncated)).toBe(8);
	});

	test("custom ellipsis respects width invariants", () => {
		// Test with single-char ellipsis
		const t1 = truncateToWidth("hello world", 7, "…");
		expect(visibleWidth(t1)).toBeLessThanOrEqual(7);
		expect(t1.endsWith("…")).toBe(true);

		// Test with multi-char ellipsis
		const t2 = truncateToWidth("hello world", 8, ">>");
		expect(visibleWidth(t2)).toBeLessThanOrEqual(8);
		expect(t2.endsWith(">>")).toBe(true);
	});

	test("edge cases", () => {
		expect(truncateToWidth("", 5)).toBe("");
		expect(truncateToWidth("hi", 10)).toBe("hi");
		// Very short widths - just verify within bounds
		const t3 = truncateToWidth("hello", 3);
		expect(visibleWidth(t3)).toBeLessThanOrEqual(3);
	});
});
