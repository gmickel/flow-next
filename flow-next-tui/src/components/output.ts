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

  /** Get color function for a log entry icon */
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
    // Tool entries use accent color for their icons
    if (entry.type === 'tool') {
      return this.theme.accent;
    }
    return this.theme.dim;
  }

  /**
   * Sanitize content for display.
   * Strips ANSI and replaces control chars (except newlines) with spaces.
   */
  private sanitize(text: string): string {
    // eslint-disable-next-line no-control-regex
    return stripAnsi(text).replace(/[\x00-\x09\x0B-\x1F\x7F]/g, ' ');
  }

  /** Render the bordered header with "Output" label and iteration */
  private renderHeader(width: number): string {
    const borderH = this.useAscii ? '-' : '─';
    const cornerTL = this.useAscii ? '+' : '┌';
    const cornerTR = this.useAscii ? '+' : '┐';
    const innerWidth = width - 2;

    if (innerWidth <= 0) {
      return this.theme.border(cornerTL) + this.theme.border(cornerTR);
    }

    // Left label: "Output"
    const leftLabel = ' Output ';
    // Right label: iteration number
    const rightLabel = ` #${this.iteration} `;

    const leftLabelWidth = visibleWidth(leftLabel);
    const rightLabelWidth = visibleWidth(rightLabel);
    const middleBorderLen = Math.max(
      0,
      innerWidth - leftLabelWidth - rightLabelWidth
    );

    return (
      this.theme.border(cornerTL) +
      this.theme.accent(leftLabel) +
      this.theme.border(borderH.repeat(middleBorderLen)) +
      this.theme.dim(rightLabel) +
      this.theme.border(cornerTR)
    );
  }

  /** Render the bottom border */
  private renderFooter(width: number): string {
    const borderH = this.useAscii ? '-' : '─';
    const cornerBL = this.useAscii ? '+' : '└';
    const cornerBR = this.useAscii ? '+' : '┘';

    return (
      this.theme.border(cornerBL) +
      this.theme.border(borderH.repeat(width - 2)) +
      this.theme.border(cornerBR)
    );
  }

  /** Fixed icon column width (icon + padding to this width + 1 space) */
  private static readonly ICON_COL_WIDTH = 2;

  /**
   * Format a single log entry as a line.
   * - Icon padded to fixed column width for alignment
   * - Filters noise (JSON-only responses, empty content)
   * - Content fills to available width
   */
  private formatEntry(entry: LogEntry, contentWidth: number): string {
    const icon = this.getToolIcon(entry);
    const colorFn = this.getEntryColor(entry);

    // Pad icon to fixed column width for alignment
    const iconWidth = visibleWidth(icon);
    const iconPadding = ' '.repeat(
      Math.max(0, OutputPanel.ICON_COL_WIDTH - iconWidth)
    );
    const prefix = colorFn(icon) + iconPadding + ' ';
    const prefixWidth = OutputPanel.ICON_COL_WIDTH + 1; // icon col + 1 space

    // Available width for content
    const availableWidth = contentWidth - prefixWidth;

    if (availableWidth <= 0) {
      return colorFn(icon);
    }

    // Sanitize and get display content
    const sanitized = this.sanitize(entry.content);
    let displayContent = this.getDisplayContent(entry, sanitized);

    // Truncate to fill available width (not before)
    if (visibleWidth(displayContent) > availableWidth) {
      displayContent = truncateToWidth(displayContent, availableWidth, '…');
    }

    return `${prefix}${displayContent}`;
  }

  /**
   * Get meaningful display content for an entry.
   * Filters noise like raw JSON, empty content, etc.
   * Applies color to tool names and content.
   */
  private getDisplayContent(entry: LogEntry, sanitized: string): string {
    const firstLine = sanitized.split('\n')[0]?.trim() ?? '';

    // Skip noise patterns
    if (this.isNoiseContent(firstLine)) {
      // For tool results, show a cleaner summary
      if (entry.type === 'response' && entry.success !== undefined) {
        return entry.success
          ? this.theme.success('OK')
          : this.theme.error('Failed');
      }
      return this.theme.dim('…');
    }

    // For tool entries, colorize the tool name
    if (entry.type === 'tool' && entry.tool) {
      const colonIndex = firstLine.indexOf(':');
      if (colonIndex > 0) {
        const toolName = firstLine.slice(0, colonIndex + 1);
        const rest = firstLine.slice(colonIndex + 1);
        return this.theme.accent(toolName) + this.theme.text(rest);
      }
    }

    // For responses, color based on type
    if (entry.type === 'response') {
      if (entry.success === false) {
        return this.theme.error(firstLine);
      }
      if (entry.success === true) {
        return this.theme.dim(firstLine);
      }
      // Text responses (Claude thinking/speaking) - use progress blue
      return this.theme.progress(firstLine);
    }

    return firstLine;
  }

  /**
   * Check if content is "noise" that should be filtered/simplified.
   */
  private isNoiseContent(content: string): boolean {
    if (!content) return true;

    // Pure JSON object/array starts (not useful as single line)
    if (
      content === '{' ||
      content === '[' ||
      content === '}' ||
      content === ']'
    ) {
      return true;
    }

    // Just whitespace or brackets
    if (/^[\s\[\]\{\}]+$/.test(content)) {
      return true;
    }

    return false;
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
