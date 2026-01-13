/**
 * HelpOverlay component - modal overlay showing keybindings.
 * Triggered by ? key, dismissed by Esc or ?.
 */

import type { Component } from '@mariozechner/pi-tui';

import type { Theme } from '../themes/index.ts';

import { padToWidth, visibleWidth } from '../lib/render.ts';

/** Keybinding definitions displayed in help overlay */
const KEYBINDINGS: Array<{ key: string; desc: string }> = [
  { key: 'j/k', desc: 'Navigate task list' },
  { key: '?', desc: 'Show/hide this help' },
  { key: 'q', desc: 'Quit (detach if running)' },
  { key: 'Esc', desc: 'Close overlay' },
  { key: 'Ctrl+C', desc: 'Same as q' },
];

/** Minimum overlay width (includes border chars) */
const MIN_OVERLAY_WIDTH = 30;
/** Maximum overlay width */
const MAX_OVERLAY_WIDTH = 50;
/** Vertical padding inside box */
const VERTICAL_PADDING = 1;

export interface HelpOverlayProps {
  theme: Theme;
  visible?: boolean;
  /** Callback when overlay requests close (Esc or ?) */
  onClose?: () => void;
}

/**
 * HelpOverlay component - centered modal with keybindings list.
 */
export class HelpOverlay implements Component {
  private theme: Theme;
  private visible: boolean;
  private onClose: (() => void) | undefined;

  constructor(props: HelpOverlayProps) {
    this.theme = props.theme;
    this.visible = props.visible ?? false;
    this.onClose = props.onClose;
  }

  /** Update overlay state */
  update(props: Partial<HelpOverlayProps>): void {
    if (props.theme !== undefined) this.theme = props.theme;
    if (props.visible !== undefined) this.visible = props.visible;
    if (props.onClose !== undefined) this.onClose = props.onClose;
  }

  /** Check if overlay is currently visible */
  isVisible(): boolean {
    return this.visible;
  }

  /** Show the overlay */
  show(): void {
    this.visible = true;
  }

  /** Hide the overlay */
  hide(): void {
    this.visible = false;
  }

  /** Toggle visibility */
  toggle(): void {
    this.visible = !this.visible;
  }

  render(width: number, height?: number): string[] {
    if (!this.visible) {
      return [];
    }

    // Calculate overlay dimensions
    const overlayWidth = Math.min(
      MAX_OVERLAY_WIDTH,
      Math.max(MIN_OVERLAY_WIDTH, width - 4)
    );
    const innerWidth = overlayWidth - 4; // 2 border + 2 padding

    // Build content lines
    const contentLines: string[] = [];

    // Keybindings
    const keyColWidth = Math.max(...KEYBINDINGS.map((kb) => kb.key.length)) + 2;
    for (const kb of KEYBINDINGS) {
      const keyPart = kb.key.padEnd(keyColWidth);
      const line = `${this.theme.accent(keyPart)}${this.theme.text(kb.desc)}`;
      contentLines.push(line);
    }

    // Footer hint
    contentLines.push('');
    const hint = 'Press ? or Esc to close';
    contentLines.push(this.theme.dim(hint));

    // Build box
    const boxLines: string[] = [];

    // Title
    const title = ' Help ';
    const titleWidth = visibleWidth(title);
    const borderAfterTitle = overlayWidth - 3 - titleWidth; // 3 = "┌─" + "─┐" minus overlap
    const topBorder =
      this.theme.border('┌─') +
      this.theme.accent(title) +
      this.theme.border('─'.repeat(Math.max(0, borderAfterTitle)) + '┐');
    boxLines.push(topBorder);

    // Top padding
    for (let i = 0; i < VERTICAL_PADDING; i++) {
      boxLines.push(
        this.theme.border('│') +
          ' '.repeat(overlayWidth - 2) +
          this.theme.border('│')
      );
    }

    // Content lines
    for (const line of contentLines) {
      const lineWidth = visibleWidth(line);
      const paddingLeft = 2;
      const paddingRight = Math.max(0, innerWidth - lineWidth);
      const paddedLine =
        this.theme.border('│') +
        ' '.repeat(paddingLeft) +
        line +
        ' '.repeat(paddingRight) +
        this.theme.border('│');
      boxLines.push(paddedLine);
    }

    // Bottom padding
    for (let i = 0; i < VERTICAL_PADDING; i++) {
      boxLines.push(
        this.theme.border('│') +
          ' '.repeat(overlayWidth - 2) +
          this.theme.border('│')
      );
    }

    // Bottom border
    boxLines.push(
      this.theme.border('└' + '─'.repeat(overlayWidth - 2) + '┘')
    );

    // Center horizontally
    const leftPad = Math.max(0, Math.floor((width - overlayWidth) / 2));
    const centeredLines = boxLines.map((line) => ' '.repeat(leftPad) + line);

    // Center vertically if height provided
    if (height !== undefined) {
      const boxHeight = boxLines.length;
      const topPad = Math.max(0, Math.floor((height - boxHeight) / 2));
      const paddedLines: string[] = [];

      // Top vertical padding (empty lines)
      for (let i = 0; i < topPad; i++) {
        paddedLines.push('');
      }

      // Box content
      for (const line of centeredLines) {
        paddedLines.push(padToWidth(line, width));
      }

      // Bottom vertical padding
      const bottomPad = Math.max(0, height - topPad - boxHeight);
      for (let i = 0; i < bottomPad; i++) {
        paddedLines.push('');
      }

      return paddedLines;
    }

    return centeredLines.map((line) => padToWidth(line, width));
  }

  handleInput(data: string): void {
    if (!this.visible) {
      return;
    }

    // Close on Escape or ?
    if (data === '\x1b' || data === '?' || data === '\x1b[27~') {
      this.hide();
      this.onClose?.();
    }
  }

  invalidate(): void {
    // No cached state to invalidate
  }
}
