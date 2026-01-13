/**
 * TaskList component for displaying task list with status icons and selection.
 * Implements j/k navigation, Enter to select, and background highlight for selected row.
 */

import chalk from 'chalk';
import type { Component } from '@mariozechner/pi-tui';
import { matchesKey, truncateToWidth } from '@mariozechner/pi-tui';

import { visibleWidth } from '../lib/render.ts';
import type { EpicTask } from '../lib/types.ts';
import type { Theme } from '../themes/index.ts';

/** Status icons for each task status */
export const STATUS_ICONS = {
  done: '●',
  in_progress: '◉',
  todo: '○',
  blocked: '⊘',
} as const;

/** ASCII fallback icons for --no-emoji mode */
export const ASCII_ICONS = {
  done: '[x]',
  in_progress: '[>]',
  todo: '[ ]',
  blocked: '[!]',
} as const;

export interface TaskListProps {
  tasks: EpicTask[];
  selectedIndex: number;
  onSelect: (task: EpicTask) => void;
  theme: Theme;
  /** Optional: callback when selection changes via navigation */
  onSelectionChange?: (task: EpicTask, index: number) => void;
  /** Optional: max visible items before scrolling (default: 10) */
  maxVisible?: number;
  /** Optional: use ASCII icons instead of Unicode (default: false) */
  useAscii?: boolean;
}

/**
 * TaskList component - renders a navigable list of tasks with status icons.
 * Features:
 * - Status icons: ● done, ◉ in_progress, ○ todo, ⊘ blocked
 * - j/k and arrow navigation
 * - Selected row background highlight
 * - Blocked tasks show dependency indicator
 * - Long titles truncated with ellipsis
 */
export class TaskList implements Component {
  private tasks: EpicTask[];
  private selectedIndex: number;
  private onSelectCb: (task: EpicTask) => void;
  private onSelectionChangeCb?: (task: EpicTask, index: number) => void;
  private theme: Theme;
  private maxVisible: number;
  private useAscii: boolean;

  constructor(props: TaskListProps) {
    this.tasks = props.tasks;
    // Clamp selectedIndex to valid range
    this.selectedIndex = this.clampIndex(props.selectedIndex, props.tasks.length);
    this.onSelectCb = props.onSelect;
    this.onSelectionChangeCb = props.onSelectionChange;
    this.theme = props.theme;
    // Ensure maxVisible is at least 1
    this.maxVisible = Math.max(1, props.maxVisible ?? 10);
    this.useAscii = props.useAscii ?? false;
  }

  /** Clamp index to valid range [0, length-1], or 0 if empty */
  private clampIndex(index: number, length: number): number {
    if (length === 0) return 0;
    return Math.max(0, Math.min(index, length - 1));
  }

  /** Update tasks list. Clamps selection and notifies if changed. */
  setTasks(tasks: EpicTask[]): void {
    const oldIndex = this.selectedIndex;
    this.tasks = tasks;
    // Clamp selection to valid range
    this.selectedIndex = this.clampIndex(this.selectedIndex, tasks.length);
    // Notify if selection changed due to clamping
    if (this.selectedIndex !== oldIndex) {
      this.notifySelectionChange();
    }
  }

  /** Get currently selected task */
  getSelectedTask(): EpicTask | undefined {
    return this.tasks[this.selectedIndex];
  }

  /** Get selected index */
  getSelectedIndex(): number {
    return this.selectedIndex;
  }

  /** Set selected index */
  setSelectedIndex(index: number): void {
    const newIndex = this.clampIndex(index, this.tasks.length);
    if (newIndex !== this.selectedIndex) {
      this.selectedIndex = newIndex;
      this.notifySelectionChange();
    }
  }

  /** Get status icon for a task */
  private getStatusIcon(task: EpicTask): string {
    const icons = this.useAscii ? ASCII_ICONS : STATUS_ICONS;
    return icons[task.status] ?? icons.todo;
  }

  /** Get status color function for a task */
  private getStatusColor(task: EpicTask): (s: string) => string {
    switch (task.status) {
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

  /** Get status color code (256-color) for a task */
  private getStatusColorCode(task: EpicTask): number {
    switch (task.status) {
      case 'done':
        return this.theme.palette.success;
      case 'in_progress':
        return this.theme.palette.progress;
      case 'blocked':
        return this.theme.palette.warning;
      default:
        return this.theme.palette.dim;
    }
  }

  /** Apply selected background to a line, padding to width */
  private applySelectedBg(line: string, width: number): string {
    const bgCode = this.theme.palette.selectedBg;
    // Validate bgCode: -1 means no bg, otherwise must be 0-255
    if (bgCode < 0 || bgCode > 255) {
      // Fall back to no background styling
      const paddingNeeded = Math.max(0, width - visibleWidth(line));
      return line + ' '.repeat(paddingNeeded);
    }
    const paddingNeeded = Math.max(0, width - visibleWidth(line));
    const padding = ' '.repeat(paddingNeeded);
    return chalk.bgAnsi256(bgCode)(line + padding);
  }

  /** Format dependency indicator for blocked tasks only */
  private formatDependency(task: EpicTask): string {
    // Defensive: handle missing/empty depends_on
    const deps = task.depends_on ?? [];
    // Only show dependency indicator for blocked tasks with deps
    if (task.status !== 'blocked' || deps.length === 0) return '';
    // Show first blocker in short form (just the task number part)
    const dep = deps[0];
    // Extract task number from "fn-N.M" -> "N.M"
    const short = dep?.replace(/^fn-/, '') ?? '';
    return ` → ${short}`;
  }

  render(width: number): string[] {
    if (this.tasks.length === 0) {
      const msg = truncateToWidth('  No tasks', width, '…');
      return [this.theme.dim(msg)];
    }

    const lines: string[] = [];
    // Safety helper: truncate any line that exceeds width (handles edge cases)
    const safePush = (line: string): void => {
      if (visibleWidth(line) > width) {
        lines.push(truncateToWidth(line, width, '…'));
      } else {
        lines.push(line);
      }
    };

    // Calculate visible range with scrolling
    const startIndex = Math.max(
      0,
      Math.min(
        this.selectedIndex - Math.floor(this.maxVisible / 2),
        this.tasks.length - this.maxVisible
      )
    );
    const endIndex = Math.min(startIndex + this.maxVisible, this.tasks.length);

    // Render visible tasks
    for (let i = startIndex; i < endIndex; i++) {
      const task = this.tasks[i];
      if (!task) continue;

      const isSelected = i === this.selectedIndex;
      const icon = this.getStatusIcon(task);

      // Get status colors early (needed for narrow-width branches too)
      const colorFn = this.getStatusColor(task);
      const bgCode = this.theme.palette.selectedBg;
      const validBg = bgCode >= 0 && bgCode <= 255;
      const statusFgCode = this.getStatusColorCode(task);

      // Format: "● fn-1.3 Add validation... → 1.2"
      // For very narrow widths, use progressive truncation to guarantee line fits

      // Calculate base widths
      const iconWidth = visibleWidth(icon);
      const depStr = this.formatDependency(task);
      const depWidth = depStr ? visibleWidth(depStr) : 0;

      // Minimum: just icon (edge case: width <= iconWidth)
      if (width <= iconWidth) {
        const truncatedIcon = truncateToWidth(icon, width, '');
        // Apply status color even at narrow widths
        if (isSelected && validBg) {
          safePush(chalk.bgAnsi256(bgCode).ansi256(statusFgCode)(truncatedIcon));
        } else {
          safePush(colorFn(truncatedIcon));
        }
        continue;
      }

      // Build progressively: icon + space
      const prefixWidth = iconWidth + 1;
      if (width <= prefixWidth) {
        // Apply status color even at narrow widths
        if (isSelected && validBg) {
          safePush(chalk.bgAnsi256(bgCode).ansi256(statusFgCode)(icon));
        } else {
          safePush(colorFn(icon));
        }
        continue;
      }

      // Drop dep if it leaves no room for id/title (need at least 1 char for id)
      const spaceForContent = width - prefixWidth;
      let actualDepStr = depStr;
      let actualDepWidth = depWidth;
      if (actualDepWidth >= spaceForContent) {
        actualDepStr = '';
        actualDepWidth = 0;
      }

      // icon + space + id (possibly truncated)
      const availableForId = spaceForContent - actualDepWidth - 1; // -1 for minimum title space
      let displayId: string;
      if (availableForId < task.id.length) {
        displayId = availableForId > 0 ? truncateToWidth(task.id, availableForId, '…') : '';
      } else {
        displayId = task.id;
      }
      const actualIdWidth = displayId ? visibleWidth(displayId) + 1 : 0;

      // Calculate available space for title
      const availableWidth = spaceForContent - actualIdWidth - actualDepWidth;
      const titleMaxWidth = Math.max(0, availableWidth);
      const truncatedTitle = titleMaxWidth > 0 ? truncateToWidth(task.title, titleMaxWidth, '…') : '';

      // Build the line content
      const idPart = displayId ? ` ${displayId}` : '';
      const titlePart = truncatedTitle ? ` ${truncatedTitle}` : '';

      if (isSelected) {
        // For selected rows: apply per-segment fg + selected bg to each segment.
        // NOTE: We don't use theme.selectList.selectedText because it's a single
        // transform that would lose per-segment status colors. Instead we apply
        // bg+fg directly per segment to preserve status icon coloring.
        const dimFgCode = this.theme.palette.dim;
        const textFgCode = this.theme.palette.text;

        // Build styled segments (with or without bg based on validation)
        let coloredIcon: string;
        let coloredId: string;
        let coloredTitle: string;
        let coloredDep: string;
        let padding: string;

        // Calculate padding needed
        const rawLine = `${icon}${idPart}${titlePart}${actualDepStr}`;
        const paddingNeeded = Math.max(0, width - visibleWidth(rawLine));

        if (validBg) {
          coloredIcon = chalk.bgAnsi256(bgCode).ansi256(statusFgCode)(icon);
          coloredId = displayId
            ? chalk.bgAnsi256(bgCode).ansi256(dimFgCode)(` ${displayId}`)
            : '';
          coloredTitle = truncatedTitle
            ? chalk.bgAnsi256(bgCode).ansi256(textFgCode)(` ${truncatedTitle}`)
            : '';
          coloredDep = actualDepStr ? chalk.bgAnsi256(bgCode).ansi256(statusFgCode)(actualDepStr) : '';
          padding = chalk.bgAnsi256(bgCode)(' '.repeat(paddingNeeded));
        } else {
          // No bg, just fg colors
          coloredIcon = chalk.ansi256(statusFgCode)(icon);
          coloredId = displayId ? chalk.ansi256(dimFgCode)(` ${displayId}`) : '';
          coloredTitle = truncatedTitle ? chalk.ansi256(textFgCode)(` ${truncatedTitle}`) : '';
          coloredDep = actualDepStr ? chalk.ansi256(statusFgCode)(actualDepStr) : '';
          padding = ' '.repeat(paddingNeeded);
        }

        safePush(`${coloredIcon}${coloredId}${coloredTitle}${coloredDep}${padding}`);
      } else {
        // For unselected rows: use per-segment colors
        const coloredIcon = colorFn(icon);
        const dimId = displayId ? this.theme.dim(` ${displayId}`) : '';
        const titleStr = truncatedTitle ? ` ${truncatedTitle}` : '';
        // Dep indicator uses same color as status (blocked => warning)
        const coloredDep = actualDepStr ? colorFn(actualDepStr) : '';
        safePush(`${coloredIcon}${dimId}${titleStr}${coloredDep}`);
      }
    }

    // Add scroll indicator if needed
    if (this.tasks.length > this.maxVisible) {
      const scrollText = `  (${this.selectedIndex + 1}/${this.tasks.length})`;
      const truncatedScroll = truncateToWidth(scrollText, width, '…');
      safePush(this.theme.dim(truncatedScroll));
    }

    return lines;
  }

  handleInput(data: string): void {
    // Early return when no tasks to prevent invalid index mutations
    if (this.tasks.length === 0) return;

    // j or down arrow - move down
    if (matchesKey(data, 'j') || matchesKey(data, 'down')) {
      this.selectedIndex =
        this.selectedIndex === this.tasks.length - 1 ? 0 : this.selectedIndex + 1;
      this.notifySelectionChange();
    }
    // k or up arrow - move up
    else if (matchesKey(data, 'k') || matchesKey(data, 'up')) {
      this.selectedIndex =
        this.selectedIndex === 0 ? this.tasks.length - 1 : this.selectedIndex - 1;
      this.notifySelectionChange();
    }
    // Enter - select task
    else if (matchesKey(data, 'enter')) {
      const task = this.tasks[this.selectedIndex];
      if (task) {
        this.onSelectCb(task);
      }
    }
  }

  private notifySelectionChange(): void {
    const task = this.tasks[this.selectedIndex];
    if (task && this.onSelectionChangeCb) {
      this.onSelectionChangeCb(task, this.selectedIndex);
    }
  }

  invalidate(): void {
    // No cached state to invalidate
  }
}
