/**
 * SplitPanel component for horizontal layout.
 * pi-tui only has vertical Container, so we build horizontal split ourselves.
 */

import type { Component } from "@mariozechner/pi-tui";
import { padToWidth, visibleWidth } from "../lib/render.ts";

export interface SplitPanelProps {
	left: Component;
	right: Component;
	ratio?: number; // default 0.3 (30% left)
	separator?: string; // default '│'
}

/**
 * Horizontal split panel - renders two components side-by-side.
 */
export class SplitPanel implements Component {
	left: Component;
	right: Component;
	ratio: number;
	separator: string;

	constructor(props: SplitPanelProps) {
		this.left = props.left;
		this.right = props.right;
		this.ratio = props.ratio ?? 0.3;
		this.separator = props.separator ?? "│";
	}

	render(width: number): string[] {
		const sepWidth = visibleWidth(this.separator);
		const leftWidth = Math.floor((width - sepWidth) * this.ratio);
		const rightWidth = width - leftWidth - sepWidth;

		// Handle edge cases where width is too small
		if (leftWidth <= 0 || rightWidth <= 0) {
			// Fall back to just rendering left panel full width
			return this.left.render(width);
		}

		const leftLines = this.left.render(leftWidth);
		const rightLines = this.right.render(rightWidth);
		const maxHeight = Math.max(leftLines.length, rightLines.length);

		const result: string[] = [];
		for (let i = 0; i < maxHeight; i++) {
			const l = padToWidth(leftLines[i] ?? "", leftWidth);
			const r = rightLines[i] ?? "";
			result.push(l + this.separator + r);
		}
		return result;
	}

	handleInput(data: string): void {
		// Forward input to both children - let the focused one handle it
		// In practice, parent component should manage focus and call handleInput
		// on the appropriate child directly. This is a fallback.
		this.left.handleInput?.(data);
		this.right.handleInput?.(data);
	}

	invalidate(): void {
		this.left.invalidate();
		this.right.invalidate();
	}
}
