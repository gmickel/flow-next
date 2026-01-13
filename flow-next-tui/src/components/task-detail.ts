/**
 * TaskDetail component for displaying full task info with markdown rendering.
 * Shows task header, metadata, receipt status, and markdown spec with scrolling.
 */

import { matchesKey, Markdown, truncateToWidth } from '@mariozechner/pi-tui';
import type { Component } from '@mariozechner/pi-tui';

import { visibleWidth } from '../lib/render.ts';
import type { Task } from '../lib/types.ts';
import type { Theme } from '../themes/index.ts';

import { STATUS_ICONS, ASCII_ICONS } from './task-list.ts';

/** Receipt status for plan/impl reviews */
export interface ReceiptStatus {
  plan?: boolean;
  impl?: boolean;
}

export interface TaskDetailProps {
  task: Task;
  spec: string; // markdown content
  receipts?: ReceiptStatus;
  blockReason?: string;
  theme: Theme;
  /** Use ASCII icons instead of Unicode (default: false) */
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
    this.clampScroll();
    this.invalidate();
  }

  /** Set viewport height for proper scroll bounds */
  setViewportHeight(height: number): void {
    this.viewportHeight = Math.max(1, height);
    this.clampScroll();
  }

  /** Clamp scroll offset to valid range */
  private clampScroll(): void {
    this.scrollOffset = Math.max(0, Math.min(this.scrollOffset, this.getMaxScroll()));
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

    // Line 1: Status icon + full title
    const titleLine = `${colorFn(icon)} ${this.task.title}`;
    if (visibleWidth(titleLine) > width) {
      lines.push(truncateToWidth(titleLine, width, '…'));
    } else {
      lines.push(titleLine);
    }

    // Line 2: Metadata (ID, status)
    const statusText = this.task.status.replace('_', ' '); // in_progress -> in progress
    const metaLine = `${this.theme.dim('ID:')} ${this.task.id}  ${this.theme.dim('Status:')} ${colorFn(statusText)}`;
    if (visibleWidth(metaLine) > width) {
      lines.push(truncateToWidth(metaLine, width, '…'));
    } else {
      lines.push(metaLine);
    }

    // Line 3: Receipt status
    lines.push(this.formatReceipts());

    // Line 4: Empty separator
    lines.push('');

    // Block reason (if blocked)
    if (this.blockReason && this.task.status === 'blocked') {
      const blockHeader = this.theme.warning(
        this.useAscii ? '[!] Blocked:' : '⊘ Blocked:'
      );
      lines.push(blockHeader);
      // Wrap block reason to width
      const reasonLines = this.wrapText(this.blockReason.trim(), width - 2);
      for (const line of reasonLines) {
        lines.push(`  ${line}`);
      }
      lines.push('');
    }

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

  /** Get or create Markdown component */
  private getMarkdown(width: number): Markdown {
    if (!this.markdown || this.lastWidth !== width) {
      this.markdown = new Markdown(
        this.spec,
        1, // paddingX
        0, // paddingY
        this.theme.markdown
      );
      this.lastWidth = width;
    }
    return this.markdown;
  }

  render(width: number): string[] {
    // Handle edge case of very narrow width
    if (width <= 0) return [];

    const allLines: string[] = [];

    // Render header
    const headerLines = this.renderHeader(width);
    allLines.push(...headerLines);

    // Render markdown spec
    if (this.spec.trim()) {
      const md = this.getMarkdown(width);
      const mdLines = md.render(width);
      allLines.push(...mdLines);
    }

    // Store total content height
    this.totalContentHeight = allLines.length;

    // Apply scrolling
    const visibleLines = allLines.slice(this.scrollOffset);

    // Pad lines to width for consistent display
    return visibleLines.map((line) => {
      const w = visibleWidth(line);
      if (w > width) {
        return truncateToWidth(line, width, '…');
      }
      return line;
    });
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
