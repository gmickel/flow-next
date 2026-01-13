/**
 * StatusBar component - segmented bottom bar with shortcuts and status.
 * Inspired by modern terminal UIs with distinct segments.
 */

import type { Component } from '@mariozechner/pi-tui';

import type { Theme } from '../themes/index.ts';

import {
  padToWidth,
  stripAnsi,
  truncateToWidth,
  visibleWidth,
} from '../lib/render.ts';

export interface StatusBarProps {
  runId?: string;
  errorCount?: number;
  theme: Theme;
}

/**
 * StatusBar component - segmented status bar.
 * Segments: shortcuts │ run info │ errors
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

  update(props: Partial<StatusBarProps>): void {
    if ('runId' in props) this.runId = props.runId;
    if ('errorCount' in props) this.errorCount = props.errorCount ?? 0;
    if ('theme' in props && props.theme) this.theme = props.theme;
  }

  render(width: number): string[] {
    if (width <= 0) return [''];

    const safeRunId = this.runId ? stripAnsi(this.runId) : undefined;
    const sep = this.theme.border(' │ ');
    const sepRaw = ' │ ';

    // Build segments
    const segments: { raw: string; colored: string }[] = [];

    // Segment 1: Shortcuts
    const shortcuts = 'q quit  j/k nav  ? help';
    segments.push({
      raw: shortcuts,
      colored: this.theme.dim(shortcuts),
    });

    // Segment 2: Run ID (if available)
    if (safeRunId) {
      segments.push({
        raw: safeRunId,
        colored: this.theme.accent(safeRunId),
      });
    }

    // Segment 3: Error count (if any)
    if (this.errorCount > 0) {
      const errText = `${this.errorCount} error${this.errorCount === 1 ? '' : 's'}`;
      segments.push({
        raw: errText,
        colored: this.theme.error(errText),
      });
    }

    // Calculate total raw width
    const totalRawWidth =
      segments.reduce((acc, s) => acc + visibleWidth(s.raw), 0) +
      (segments.length - 1) * visibleWidth(sepRaw);

    // Build the line
    let line: string;
    if (totalRawWidth <= width) {
      // All segments fit
      const gapWidth = Math.max(0, width - totalRawWidth);
      // Put gap between first segment and rest (push right content to far right)
      if (segments.length === 1) {
        line = segments[0]!.colored + ' '.repeat(gapWidth);
      } else {
        const firstSeg = segments[0]!;
        const restSegs = segments
          .slice(1)
          .map((s) => s.colored)
          .join(sep);
        const restRaw = segments
          .slice(1)
          .map((s) => s.raw)
          .join(sepRaw);
        const gapForRest = Math.max(
          0,
          width -
            visibleWidth(firstSeg.raw) -
            visibleWidth(restRaw) -
            (segments.length - 1) * visibleWidth(sepRaw)
        );
        line = firstSeg.colored + ' '.repeat(gapForRest) + restSegs;
      }
    } else {
      // Need to truncate - just show shortcuts
      line = truncateToWidth(segments[0]!.colored, width, '…');
    }

    return [padToWidth(line, width)];
  }

  handleInput(_data: string): void {}

  invalidate(): void {}
}
