import { describe, expect, test } from "bun:test";
import {
	DARK,
	DARK_PALETTE,
	LIGHT,
	LIGHT_PALETTE,
	getTheme,
} from "../src/themes";

describe("themes", () => {
	test("getTheme returns dark theme by default", () => {
		const theme = getTheme();
		expect(theme.name).toBe("dark");
	});

	test("getTheme(true) returns light theme", () => {
		const theme = getTheme(true);
		expect(theme.name).toBe("light");
	});

	test("DARK and LIGHT aliases work", () => {
		expect(DARK.name).toBe("dark");
		expect(LIGHT.name).toBe("light");
	});

	test("dark palette matches spec", () => {
		expect(DARK_PALETTE.accent).toBe(81); // electric cyan
		expect(DARK_PALETTE.success).toBe(114); // muted green
		expect(DARK_PALETTE.progress).toBe(75); // bright blue
		expect(DARK_PALETTE.warning).toBe(221); // amber
		expect(DARK_PALETTE.error).toBe(203); // coral red
		expect(DARK_PALETTE.text).toBe(252);
		expect(DARK_PALETTE.dim).toBe(242);
		expect(DARK_PALETTE.border).toBe(239);
		expect(DARK_PALETTE.selectedBg).toBe(236);
		expect(DARK_PALETTE.bg).toBe(-1); // terminal default
	});

	test("light palette has valid values", () => {
		expect(LIGHT_PALETTE.bg).toBe(-1); // terminal default
		expect(typeof LIGHT_PALETTE.accent).toBe("number");
		expect(typeof LIGHT_PALETTE.text).toBe("number");
	});

	test("theme has color functions", () => {
		expect(typeof DARK.text).toBe("function");
		expect(typeof DARK.dim).toBe("function");
		expect(typeof DARK.accent).toBe("function");
		expect(typeof DARK.success).toBe("function");
		expect(typeof DARK.progress).toBe("function");
		expect(typeof DARK.warning).toBe("function");
		expect(typeof DARK.error).toBe("function");
		expect(typeof DARK.border).toBe("function");
		expect(typeof DARK.selectedBg).toBe("function");
	});

	test("color functions return strings", () => {
		expect(typeof DARK.text("test")).toBe("string");
		expect(typeof DARK.accent("test")).toBe("string");
	});

	test("theme has pi-tui compatible selectList theme", () => {
		expect(typeof DARK.selectList.selectedPrefix).toBe("function");
		expect(typeof DARK.selectList.selectedText).toBe("function");
		expect(typeof DARK.selectList.description).toBe("function");
		expect(typeof DARK.selectList.scrollInfo).toBe("function");
		expect(typeof DARK.selectList.noMatch).toBe("function");
	});

	test("theme has pi-tui compatible markdown theme", () => {
		expect(typeof DARK.markdown.heading).toBe("function");
		expect(typeof DARK.markdown.link).toBe("function");
		expect(typeof DARK.markdown.code).toBe("function");
		expect(typeof DARK.markdown.codeBlock).toBe("function");
		expect(typeof DARK.markdown.bold).toBe("function");
		expect(typeof DARK.markdown.italic).toBe("function");
	});

	test("theme has pi-tui compatible editor theme", () => {
		expect(typeof DARK.editor.borderColor).toBe("function");
		expect(DARK.editor.selectList).toBeDefined();
		expect(typeof DARK.editor.selectList.selectedPrefix).toBe("function");
	});
});
