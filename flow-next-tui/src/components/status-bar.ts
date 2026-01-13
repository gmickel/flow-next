/**
 * StatusBar component - bottom bar with shortcuts and run info.
 * Single row: shortcuts on left, run ID + error count on right.
 */

import type { Component } from '@mariozechner/pi-tui';

import { truncateToWidth } from '@mariozechner/pi-tui';

import type { Theme } from '../themes/index.ts';

import { visibleWidth } from '../lib/render.ts';

/** Shortcut definitions for the status bar */
const SHORTCUTS = 'q quit  j/k nav  ? help';

export interface StatusBarProps {
  runId?: string;
  errorCount?: number;
  theme: Theme;
}

/**
 * StatusBar component - single-row bottom bar.
 * Left: keyboard shortcuts
 * Right: run ID + optional error count
 */
export class StatusBar implements Component {
  private runId: string | undefined;
  private errorCount: number;
  private theme: Theme;

  constructor(props: StatusBarProps) {
    this.runId = props.runId;
    this.errorCount = props.errorCount ?? 0;
    this.theme = props.theme;
  }

  /** Update status bar state */
  update(props: Partial<StatusBarProps>): void {
    if (props.runId !== undefined) this.runId = props.runId;
    if (props.errorCount !== undefined) this.errorCount = props.errorCount;
    if (props.theme !== undefined) this.theme = props.theme;
  }

  render(width: number): string[] {
    // Left side: shortcuts (dimmed)
    const shortcutsWidth = visibleWidth(SHORTCUTS);

    // Right side: run ID + error count
    let rightContent = '';
    if (this.runId) {
      rightContent = this.runId;
      if (this.errorCount > 0) {
        rightContent += ` (${this.errorCount} error${this.errorCount === 1 ? '' : 's'})`;
      }
    } else if (this.errorCount > 0) {
      rightContent = `${this.errorCount} error${this.errorCount === 1 ? '' : 's'}`;
    }
    const rightWidth = visibleWidth(rightContent);

    // Handle very narrow widths
    if (width <= 0) {
      return [''];
    }

    // Build the row
    const minWidth = shortcutsWidth + (rightWidth > 0 ? 2 + rightWidth : 0);

    if (width < shortcutsWidth) {
      // Too narrow for full shortcuts - truncate
      const truncatedShortcuts = truncateToWidth(SHORTCUTS, width, '…');
      return [this.theme.dim(truncatedShortcuts)];
    }

    if (width < minWidth && rightWidth > 0) {
      // Can fit shortcuts but not full right side
      const availableForRight = width - shortcutsWidth - 2;
      if (availableForRight <= 0) {
        // Just show shortcuts
        const gap = ' '.repeat(Math.max(0, width - shortcutsWidth));
        return [this.theme.dim(SHORTCUTS) + gap];
      }
      // Truncate right content
      const truncatedRight = truncateToWidth(rightContent, availableForRight, '…');
      const truncatedRightWidth = visibleWidth(truncatedRight);
      const gapWidth = Math.max(0, width - shortcutsWidth - truncatedRightWidth);
      const gap = ' '.repeat(gapWidth);

      let rightColored = truncatedRight;
      if (this.errorCount > 0) {
        rightColored = this.theme.error(truncatedRight);
      } else {
        rightColored = this.theme.dim(truncatedRight);
      }

      return [this.theme.dim(SHORTCUTS) + gap + rightColored];
    }

    // Full content fits
    const gapWidth = Math.max(0, width - shortcutsWidth - rightWidth);
    const gap = ' '.repeat(gapWidth);

    let rightColored = '';
    if (rightContent) {
      if (this.errorCount > 0) {
        // Color error part differently
        if (this.runId) {
          const errorPart = ` (${this.errorCount} error${this.errorCount === 1 ? '' : 's'})`;
          rightColored = this.theme.dim(this.runId) + this.theme.error(errorPart);
        } else {
          rightColored = this.theme.error(rightContent);
        }
      } else {
        rightColored = this.theme.dim(rightContent);
      }
    }

    return [this.theme.dim(SHORTCUTS) + gap + rightColored];
  }

  handleInput(_data: string): void {
    // StatusBar doesn't handle input
  }

  invalidate(): void {
    // No cached state to invalidate
  }
}
