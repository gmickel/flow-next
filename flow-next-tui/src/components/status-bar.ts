/**
 * StatusBar component - bottom bar with shortcuts and run info.
 * Single row: shortcuts on left, run ID + error count on right.
 */

import type { Component } from '@mariozechner/pi-tui';

import type { Theme } from '../themes/index.ts';

import {
  padToWidth,
  stripAnsi,
  truncateToWidth,
  visibleWidth,
} from '../lib/render.ts';

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

  /** Update status bar state (uses 'in' semantics to allow clearing) */
  update(props: Partial<StatusBarProps>): void {
    if ('runId' in props) this.runId = props.runId;
    if ('errorCount' in props) this.errorCount = props.errorCount ?? 0;
    if ('theme' in props && props.theme) this.theme = props.theme;
  }

  render(width: number): string[] {
    // Handle very narrow widths
    if (width <= 0) {
      return [''];
    }

    // Sanitize runId to prevent ANSI injection
    const safeRunId = this.runId ? stripAnsi(this.runId) : undefined;

    // Left side: shortcuts (dimmed)
    const shortcutsWidth = visibleWidth(SHORTCUTS);

    // Right side: run ID + error count
    let rightContent = '';
    if (safeRunId) {
      rightContent = safeRunId;
      if (this.errorCount > 0) {
        rightContent += ` (${this.errorCount} error${this.errorCount === 1 ? '' : 's'})`;
      }
    } else if (this.errorCount > 0) {
      rightContent = `${this.errorCount} error${this.errorCount === 1 ? '' : 's'}`;
    }
    const rightWidth = visibleWidth(rightContent);

    // Build the row
    const minWidth = shortcutsWidth + (rightWidth > 0 ? 2 + rightWidth : 0);
    let line: string;

    if (width < shortcutsWidth) {
      // Too narrow for full shortcuts - truncate
      const truncatedShortcuts = truncateToWidth(SHORTCUTS, width, '…');
      line = this.theme.dim(truncatedShortcuts);
    } else if (width < minWidth && rightWidth > 0) {
      // Can fit shortcuts but not full right side
      const availableForRight = width - shortcutsWidth - 2;
      if (availableForRight <= 0) {
        // Just show shortcuts
        const gap = ' '.repeat(Math.max(0, width - shortcutsWidth));
        line = this.theme.dim(SHORTCUTS) + gap;
      } else {
        // Truncate right content
        const truncatedRight = truncateToWidth(rightContent, availableForRight, '…');
        const truncatedRightWidth = visibleWidth(truncatedRight);
        const gapWidth = Math.max(0, width - shortcutsWidth - truncatedRightWidth);
        const gap = ' '.repeat(gapWidth);

        const rightColored =
          this.errorCount > 0
            ? this.theme.error(truncatedRight)
            : this.theme.dim(truncatedRight);

        line = this.theme.dim(SHORTCUTS) + gap + rightColored;
      }
    } else {
      // Full content fits
      const gapWidth = Math.max(0, width - shortcutsWidth - rightWidth);
      const gap = ' '.repeat(gapWidth);

      let rightColored = '';
      if (rightContent) {
        if (this.errorCount > 0) {
          // Color error part differently
          if (safeRunId) {
            const errorPart = ` (${this.errorCount} error${this.errorCount === 1 ? '' : 's'})`;
            rightColored = this.theme.dim(safeRunId) + this.theme.error(errorPart);
          } else {
            rightColored = this.theme.error(rightContent);
          }
        } else {
          rightColored = this.theme.dim(rightContent);
        }
      }

      line = this.theme.dim(SHORTCUTS) + gap + rightColored;
    }

    // Ensure full width (prevents stale chars on screen)
    return [padToWidth(line, width)];
  }

  handleInput(_data: string): void {
    // StatusBar doesn't handle input
  }

  invalidate(): void {
    // No cached state to invalidate
  }
}
