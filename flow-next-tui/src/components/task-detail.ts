/**
 * TaskDetail component with bordered panel and clean sections.
 * Shows task info, metadata, receipts, and markdown spec.
 */

import type { Component } from '@mariozechner/pi-tui';

import { matchesKey, Markdown } from '@mariozechner/pi-tui';

import type { ReceiptStatus } from '../lib/runs.ts';
import type { Task } from '../lib/types.ts';
import type { Theme } from '../themes/index.ts';

import {
  visibleWidth,
  truncateToWidth,
  stripAnsi,
  padToWidth,
} from '../lib/render.ts';
import { STATUS_ICONS, ASCII_ICONS } from './task-list.ts';

export interface TaskDetailProps {
  task: Task;
  spec: string;
  receipts?: ReceiptStatus;
  blockReason?: string;
  theme: Theme;
  useAscii?: boolean;
}

/**
 * TaskDetail component - renders full task info with markdown spec.
 * Features:
 * - Status icon + full title header
 * - Metadata line: ID, status
 * - Receipt indicators: "Plan ✓  Impl ✓" or "Plan ✗  Impl -"
 * - Markdown spec content
 * - Block reason display for blocked tasks
 * - j/k scrolling when content exceeds height
 */
export class TaskDetail implements Component {
  private task: Task;
  private spec: string;
  private receipts: ReceiptStatus;
  private blockReason: string | null;
  private theme: Theme;
  private useAscii: boolean;

  // Scroll state
  private scrollOffset = 0;
  private viewportHeight = 20; // Default viewport, updated by setViewportHeight
  private totalContentHeight = 0;

  // Markdown component (lazy-initialized)
  private markdown: Markdown | null = null;
  private lastWidth = 0;

  constructor(props: TaskDetailProps) {
    this.task = props.task;
    this.spec = props.spec;
    this.receipts = props.receipts ?? {};
    this.blockReason = props.blockReason ?? null;
    this.theme = props.theme;
    this.useAscii = props.useAscii ?? false;
  }

  /** Update task data */
  setTask(task: Task): void {
    this.task = task;
    this.scrollOffset = 0; // Reset scroll on task change
    this.invalidate();
  }

  /** Update spec content */
  setSpec(spec: string): void {
    this.spec = spec;
    this.markdown = null; // Force re-creation
    this.scrollOffset = 0; // Reset scroll on content change
    this.invalidate();
  }

  /** Update receipt status */
  setReceipts(receipts: ReceiptStatus): void {
    this.receipts = receipts;
    this.invalidate();
  }

  /** Update block reason */
  setBlockReason(reason: string | null): void {
    this.blockReason = reason;
    // clampScroll happens in render() after totalContentHeight is recomputed
    this.invalidate();
  }

  /** Set viewport height for proper scroll bounds */
  setViewportHeight(height: number): void {
    this.viewportHeight = Math.max(1, height);
    this.clampScroll();
  }

  /** Clamp scroll offset to valid range */
  private clampScroll(): void {
    this.scrollOffset = Math.max(
      0,
      Math.min(this.scrollOffset, this.getMaxScroll())
    );
  }

  /**
   * Sanitize a single-line field for display.
   * Strips ANSI and replaces control chars (newlines, tabs, etc) with spaces.
   */
  private sanitizeSingleLine(text: string): string {
    // Strip ANSI, then replace control chars with spaces
    // eslint-disable-next-line no-control-regex
    return stripAnsi(text).replace(/[\x00-\x1F\x7F]/g, ' ');
  }

  /**
   * Sanitize a multiline field for display.
   * Strips ANSI and control chars except newlines.
   */
  private sanitizeMultiLine(text: string): string {
    // Strip ANSI, then replace control chars except \n with spaces
    // eslint-disable-next-line no-control-regex
    return stripAnsi(text).replace(/[\x00-\x09\x0B-\x1F\x7F]/g, ' ');
  }

  /** Get status icon for the task */
  private getStatusIcon(): string {
    const icons = this.useAscii ? ASCII_ICONS : STATUS_ICONS;
    return icons[this.task.status] ?? icons.todo;
  }

  /** Get status color function */
  private getStatusColor(): (s: string) => string {
    switch (this.task.status) {
      case 'done':
        return this.theme.success;
      case 'in_progress':
        return this.theme.progress;
      case 'blocked':
        return this.theme.warning;
      default:
        return this.theme.dim;
    }
  }

  /** Format receipt indicators */
  private formatReceipts(): string {
    const check = this.useAscii ? 'Y' : '✓';
    const cross = this.useAscii ? 'N' : '✗';
    const dash = '-';

    const planStatus =
      this.receipts.plan === true
        ? this.theme.success(check)
        : this.receipts.plan === false
          ? this.theme.error(cross)
          : this.theme.dim(dash);

    const implStatus =
      this.receipts.impl === true
        ? this.theme.success(check)
        : this.receipts.impl === false
          ? this.theme.error(cross)
          : this.theme.dim(dash);

    return `Plan ${planStatus}  Impl ${implStatus}`;
  }

  /** Render header section (icon, title, metadata, receipts) */
  private renderHeader(width: number): string[] {
    const lines: string[] = [];
    const colorFn = this.getStatusColor();
    const icon = this.getStatusIcon();
    const contentWidth = width - 2; // for internal padding

    // Sanitize task-provided strings
    const safeTitle = this.sanitizeSingleLine(this.task.title);
    const safeId = this.sanitizeSingleLine(this.task.id);

    // Line 1: Status icon + task ID
    const idLine = colorFn(icon) + ' ' + this.theme.accent(safeId);
    lines.push(truncateToWidth(idLine, contentWidth, '…'));

    // Line 2: Full title
    lines.push(truncateToWidth(this.theme.text(safeTitle), contentWidth, '…'));

    // Line 3: Empty separator
    lines.push('');

    // Line 4: Status badge + receipts inline
    const statusText = this.task.status.replace('_', ' ');
    const statusBadge = this.theme.dim('Status: ') + colorFn(statusText);
    const receipts = this.formatReceipts();
    const metaLine = statusBadge + this.theme.dim('  │  ') + receipts;
    lines.push(truncateToWidth(metaLine, contentWidth, '…'));

    // Block reason (if blocked)
    if (this.blockReason && this.task.status === 'blocked') {
      lines.push('');
      const blockHeader = this.theme.warning(
        this.useAscii ? '[!] Blocked' : '⊘ Blocked'
      );
      lines.push(blockHeader);
      const sanitizedReason = this.sanitizeMultiLine(this.blockReason.trim());
      const reasonLines = this.wrapText(sanitizedReason, contentWidth - 2);
      for (const line of reasonLines) {
        lines.push(this.theme.dim('  ' + line));
      }
    }

    // Separator before spec
    lines.push('');
    const sepChar = this.useAscii ? '-' : '─';
    lines.push(this.theme.border(sepChar.repeat(Math.min(20, contentWidth))));
    lines.push('');

    return lines;
  }

  /** Simple text wrapping */
  private wrapText(text: string, maxWidth: number): string[] {
    if (maxWidth <= 0) return [text];
    const words = text.split(/\s+/);
    const lines: string[] = [];
    let currentLine = '';

    for (const word of words) {
      if (currentLine === '') {
        currentLine = word;
      } else if (visibleWidth(currentLine + ' ' + word) <= maxWidth) {
        currentLine += ' ' + word;
      } else {
        lines.push(currentLine);
        currentLine = word;
      }
    }
    if (currentLine) {
      lines.push(currentLine);
    }
    return lines.length > 0 ? lines : [''];
  }

  /** Get or create Markdown component with sanitized spec */
  private getMarkdown(width: number, sanitizedSpec: string): Markdown {
    if (!this.markdown || this.lastWidth !== width) {
      this.markdown = new Markdown(
        sanitizedSpec, // Use sanitized spec directly
        0, // paddingX - no padding, we handle truncation
        0, // paddingY
        this.theme.markdown
      );
      this.lastWidth = width;
    }
    return this.markdown;
  }

  render(width: number): string[] {
    if (width <= 4) return [];

    const borderH = this.useAscii ? '-' : '─';
    const borderV = this.useAscii ? '|' : '│';
    const cornerTL = this.useAscii ? '+' : '┌';
    const cornerTR = this.useAscii ? '+' : '┐';

    const allLines: string[] = [];

    // Panel header with "Details" label
    const label = ' Details ';
    const labelWidth = visibleWidth(label);
    const innerWidth = width - 2;
    const leftBorderLen = Math.max(
      0,
      Math.floor((innerWidth - labelWidth) / 2)
    );
    const rightBorderLen = Math.max(0, innerWidth - leftBorderLen - labelWidth);

    allLines.push(
      this.theme.border(cornerTL) +
        this.theme.border(borderH.repeat(leftBorderLen)) +
        this.theme.accent(label) +
        this.theme.border(borderH.repeat(rightBorderLen)) +
        this.theme.border(cornerTR)
    );

    // Content width (inside borders + padding)
    const contentWidth = width - 4;

    // Render header (task info)
    const headerLines = this.renderHeader(contentWidth);

    // Render markdown spec
    const sanitizedSpec = this.sanitizeMultiLine(this.spec);
    let specLines: string[] = [];
    if (sanitizedSpec.trim()) {
      const md = this.getMarkdown(contentWidth, sanitizedSpec);
      specLines = md.render(contentWidth);
    }

    // Combine content
    const contentLines = [...headerLines, ...specLines];
    this.totalContentHeight = contentLines.length;
    this.clampScroll();

    // Apply scrolling
    const visibleContent = contentLines.slice(this.scrollOffset);

    // Wrap each line with borders
    for (const line of visibleContent) {
      const paddedLine = padToWidth(line, contentWidth);
      allLines.push(
        this.theme.border(borderV) +
          ' ' +
          truncateToWidth(paddedLine, contentWidth, '…') +
          ' ' +
          this.theme.border(borderV)
      );
    }

    return allLines;
  }

  handleInput(data: string): void {
    const maxScroll = this.getMaxScroll();

    // End (G - check uppercase first before lowercase g)
    if (data === 'G' || matchesKey(data, 'shift+g')) {
      this.scrollOffset = maxScroll;
    }
    // Home (g - lowercase only)
    else if (data === 'g') {
      this.scrollOffset = 0;
    }
    // j or down arrow - scroll down
    else if (matchesKey(data, 'j') || matchesKey(data, 'down')) {
      if (this.scrollOffset < maxScroll) {
        this.scrollOffset++;
      }
    }
    // k or up arrow - scroll up
    else if (matchesKey(data, 'k') || matchesKey(data, 'up')) {
      if (this.scrollOffset > 0) {
        this.scrollOffset--;
      }
    }
    // Page down (space or ctrl+d)
    else if (data === ' ' || data === '\x04') {
      const pageSize = Math.max(1, this.viewportHeight - 2);
      this.scrollOffset = Math.min(this.scrollOffset + pageSize, maxScroll);
    }
    // Page up (ctrl+u)
    else if (data === '\x15') {
      const pageSize = Math.max(1, this.viewportHeight - 2);
      this.scrollOffset = Math.max(0, this.scrollOffset - pageSize);
    }
  }

  /** Reset scroll position */
  resetScroll(): void {
    this.scrollOffset = 0;
  }

  /** Get current scroll offset */
  getScrollOffset(): number {
    return this.scrollOffset;
  }

  /** Get total content height */
  getTotalHeight(): number {
    return this.totalContentHeight;
  }

  /** Get current viewport height */
  getViewportHeight(): number {
    return this.viewportHeight;
  }

  /** Get max scroll offset */
  getMaxScroll(): number {
    return Math.max(0, this.totalContentHeight - this.viewportHeight);
  }

  invalidate(): void {
    if (this.markdown) {
      this.markdown.invalidate();
    }
  }
}
