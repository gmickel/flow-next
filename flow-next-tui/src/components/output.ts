/**
 * OutputPanel component for streaming log output with auto-scroll.
 * Shows iteration log entries with tool icons and supports keyboard scrolling.
 */

import type { Component } from '@mariozechner/pi-tui';

import { matchesKey } from '@mariozechner/pi-tui';

import type { LogEntry } from '../lib/types.ts';
import type { Theme } from '../themes/index.ts';

import { iconForEntry } from '../lib/parser.ts';
import {
  visibleWidth,
  truncateToWidth,
  padToWidth,
  stripAnsi,
} from '../lib/render.ts';

/** Default buffer size */
const DEFAULT_MAX_BUFFER = 500;

export interface OutputPanelProps {
  /**
   * Buffer of log entries to display. Defaults to internal empty array.
   * Note: If passed, caller shares ownership - appendLine mutates it, clearBuffer clears in-place.
   */
  buffer?: LogEntry[];
  /** Current iteration number for header display. Defaults to 0. */
  iteration?: number;
  theme: Theme;
  maxBuffer?: number;
  /** Use ASCII icons instead of Unicode (default: false) */
  useAscii?: boolean;
}

/**
 * OutputPanel component - renders streaming log output.
 * Features:
 * - Bordered with "─Iteration N─" header
 * - Tool icons by type
 * - Auto-scroll to bottom (unless user scrolled up)
 * - 500 line buffer (configurable)
 * - j/k/arrow scrolling
 */
export class OutputPanel implements Component {
  private buffer: LogEntry[];
  private iteration: number;
  private theme: Theme;
  private maxBuffer: number;
  private useAscii: boolean;

  // Scroll state
  private scrollOffset = 0;
  private viewportHeight = 20;
  private autoScroll = true; // Auto-scroll enabled by default

  constructor(props: OutputPanelProps) {
    this.buffer = props.buffer ?? [];
    this.iteration = props.iteration ?? 0;
    this.theme = props.theme;
    this.maxBuffer = props.maxBuffer ?? DEFAULT_MAX_BUFFER;
    this.useAscii = props.useAscii ?? false;
  }

  /** Append a log entry to the buffer */
  appendLine(entry: LogEntry): void {
    // Capture wasAtBottom BEFORE mutating buffer (per spec: "Reset when at bottom")
    const wasAtBottom = this.scrollOffset >= this.getMaxScroll();

    this.buffer.push(entry);

    // Trim buffer if over limit
    if (this.buffer.length > this.maxBuffer) {
      const excess = this.buffer.length - this.maxBuffer;
      this.buffer.splice(0, excess);
      // Adjust scroll offset if we removed lines above viewport
      this.scrollOffset = Math.max(0, this.scrollOffset - excess);
    }

    // Auto-scroll to bottom if enabled OR user was at bottom before append
    if (this.autoScroll || wasAtBottom) {
      this.scrollToBottom();
    }
  }

  /** Set the current iteration number */
  setIteration(iteration: number): void {
    this.iteration = iteration;
  }

  /** Clear all buffer entries (clears in-place to preserve shared reference) */
  clearBuffer(): void {
    this.buffer.length = 0;
    this.scrollOffset = 0;
    this.autoScroll = true;
  }

  /**
   * Set viewport height for proper scroll bounds.
   * MUST be called before render() for correct scroll math.
   * @param height Total height in lines (including 2 lines for borders)
   */
  setViewportHeight(height: number): void {
    // Subtract 2 for top/bottom borders
    this.viewportHeight = Math.max(1, height - 2);
    // If auto-scroll is enabled, scroll to bottom after resize
    if (this.autoScroll) {
      this.scrollOffset = this.getMaxScroll();
    } else {
      this.clampScroll();
    }
  }

  /** Scroll to bottom and re-enable auto-scroll */
  scrollToBottom(): void {
    this.scrollOffset = this.getMaxScroll();
    this.autoScroll = true;
  }

  /** Get tool icon for a log entry (uses shared iconForEntry from parser) */
  private getToolIcon(entry: LogEntry): string {
    return iconForEntry(entry, this.useAscii);
  }

  /** Get color function for a log entry */
  private getEntryColor(entry: LogEntry): (s: string) => string {
    if (entry.success === true) {
      return this.theme.success;
    }
    if (entry.success === false) {
      return this.theme.error;
    }
    if (entry.type === 'error') {
      return this.theme.error;
    }
    return this.theme.text;
  }

  /**
   * Sanitize content for display.
   * Strips ANSI and replaces control chars (except newlines) with spaces.
   */
  private sanitize(text: string): string {
    // eslint-disable-next-line no-control-regex
    return stripAnsi(text).replace(/[\x00-\x09\x0B-\x1F\x7F]/g, ' ');
  }

  /** Render the bordered header */
  private renderHeader(width: number): string {
    const borderChar = this.useAscii ? '-' : '─';
    const topLeft = this.useAscii ? '+' : '┌';
    const topRight = this.useAscii ? '+' : '┐';
    const innerWidth = width - 2; // Account for corners

    // Handle very narrow widths - minimal header
    if (innerWidth <= 0) {
      return this.theme.border(topLeft) + this.theme.border(topRight);
    }

    // Build label, truncate if needed
    let label = ` Iteration ${this.iteration} `;
    let labelWidth = visibleWidth(label);

    if (labelWidth > innerWidth) {
      // Truncate label to fit
      label = truncateToWidth(label, innerWidth, '…');
      labelWidth = visibleWidth(label);
    }

    // Calculate left/right padding
    const leftPad = Math.max(0, Math.floor((innerWidth - labelWidth) / 2));
    const rightPad = Math.max(0, innerWidth - labelWidth - leftPad);

    return (
      this.theme.border(topLeft) +
      this.theme.border(borderChar.repeat(leftPad)) +
      this.theme.accent(label) +
      this.theme.border(borderChar.repeat(rightPad)) +
      this.theme.border(topRight)
    );
  }

  /** Render the bottom border */
  private renderFooter(width: number): string {
    const borderChar = this.useAscii ? '-' : '─';
    const bottomLeft = this.useAscii ? '+' : '└';
    const bottomRight = this.useAscii ? '+' : '┘';

    return (
      this.theme.border(bottomLeft) +
      this.theme.border(borderChar.repeat(width - 2)) +
      this.theme.border(bottomRight)
    );
  }

  /**
   * Format a single log entry as a line.
   * Note: Only renders first line of content - multiline entries are summarized.
   * This is intentional for the output panel which shows one line per LogEntry.
   */
  private formatEntry(entry: LogEntry, contentWidth: number): string {
    const icon = this.getToolIcon(entry);
    const colorFn = this.getEntryColor(entry);
    const iconColored = colorFn(icon);
    const iconWidth = visibleWidth(icon);

    // Available width for content (icon + space + content)
    const availableWidth = contentWidth - iconWidth - 1;

    // Guard against very narrow widths - just show icon
    if (availableWidth <= 0) {
      return iconColored;
    }

    // Sanitize and take first line only for display
    const sanitized = this.sanitize(entry.content);
    const firstLine = sanitized.split('\n')[0] ?? '';

    if (visibleWidth(firstLine) > availableWidth) {
      return `${iconColored} ${truncateToWidth(firstLine, availableWidth, '…')}`;
    }
    return `${iconColored} ${firstLine}`;
  }

  /** Get max scroll offset */
  private getMaxScroll(): number {
    return Math.max(0, this.buffer.length - this.viewportHeight);
  }

  /** Clamp scroll offset to valid range */
  private clampScroll(): void {
    this.scrollOffset = Math.max(
      0,
      Math.min(this.scrollOffset, this.getMaxScroll())
    );
  }

  render(width: number): string[] {
    if (width <= 2) return [];

    const lines: string[] = [];
    const borderChar = this.useAscii ? '|' : '│';

    // Header
    lines.push(this.renderHeader(width));

    // Content area width (inside borders)
    const contentWidth = width - 2;

    // Clamp scroll before rendering
    this.clampScroll();

    // Get visible portion of buffer
    const visibleEntries = this.buffer.slice(
      this.scrollOffset,
      this.scrollOffset + this.viewportHeight
    );

    // Render each visible entry
    for (const entry of visibleEntries) {
      const formatted = this.formatEntry(entry, contentWidth);
      const padded = padToWidth(formatted, contentWidth);
      lines.push(
        this.theme.border(borderChar) + padded + this.theme.border(borderChar)
      );
    }

    // Fill remaining viewport with empty lines
    const emptyLinesNeeded = this.viewportHeight - visibleEntries.length;
    const emptyLine =
      this.theme.border(borderChar) +
      ' '.repeat(contentWidth) +
      this.theme.border(borderChar);
    for (let i = 0; i < emptyLinesNeeded; i++) {
      lines.push(emptyLine);
    }

    // Footer
    lines.push(this.renderFooter(width));

    return lines;
  }

  handleInput(data: string): void {
    const maxScroll = this.getMaxScroll();
    const prevOffset = this.scrollOffset;

    // End (G - check uppercase first)
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

    // Detect if user scrolled up manually (disable auto-scroll)
    if (this.scrollOffset < prevOffset) {
      this.autoScroll = false;
    }
    // Re-enable auto-scroll if user scrolled to bottom
    if (this.scrollOffset >= maxScroll) {
      this.autoScroll = true;
    }
  }

  /** Check if auto-scroll is currently enabled */
  isAutoScrollEnabled(): boolean {
    return this.autoScroll;
  }

  /** Get current scroll offset */
  getScrollOffset(): number {
    return this.scrollOffset;
  }

  /** Get buffer length */
  getBufferLength(): number {
    return this.buffer.length;
  }

  invalidate(): void {
    // No cached state to invalidate
  }
}
