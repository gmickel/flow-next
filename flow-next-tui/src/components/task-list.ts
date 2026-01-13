/**
 * TaskList component with bordered panel header.
 * Clean task list with status icons and selection highlighting.
 */

import type { Component } from '@mariozechner/pi-tui';

import { matchesKey, truncateToWidth } from '@mariozechner/pi-tui';
import chalk from 'chalk';

import type { EpicTask } from '../lib/types.ts';
import type { Theme } from '../themes/index.ts';

import { visibleWidth, padToWidth } from '../lib/render.ts';

/** Status icons - using filled/hollow circles for clear visual hierarchy */
export const STATUS_ICONS = {
  done: '✓',
  in_progress: '▶',
  todo: '○',
  blocked: '⊘',
} as const;

/** ASCII fallback icons */
export const ASCII_ICONS = {
  done: '+',
  in_progress: '>',
  todo: '-',
  blocked: '!',
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
    this.selectedIndex = this.clampIndex(
      props.selectedIndex,
      props.tasks.length
    );
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
    const lines: string[] = [];
    const borderH = this.useAscii ? '-' : '─';
    const borderV = this.useAscii ? '|' : '│';
    const cornerTL = this.useAscii ? '+' : '┌';
    const cornerTR = this.useAscii ? '+' : '┐';

    // Panel header with "Tasks" label
    const label = ' Tasks ';
    const labelWidth = visibleWidth(label);
    const innerWidth = width - 2;
    const leftBorderLen = Math.max(
      0,
      Math.floor((innerWidth - labelWidth) / 2)
    );
    const rightBorderLen = Math.max(0, innerWidth - leftBorderLen - labelWidth);

    lines.push(
      this.theme.border(cornerTL) +
        this.theme.border(borderH.repeat(leftBorderLen)) +
        this.theme.accent(label) +
        this.theme.border(borderH.repeat(rightBorderLen)) +
        this.theme.border(cornerTR)
    );

    // Content area width
    const contentWidth = width - 4; // borders + padding

    if (this.tasks.length === 0) {
      const emptyMsg = padToWidth(' No tasks', contentWidth);
      lines.push(
        this.theme.border(borderV) +
          ' ' +
          this.theme.dim(emptyMsg) +
          ' ' +
          this.theme.border(borderV)
      );
      return lines;
    }

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
      const colorFn = this.getStatusColor(task);
      const bgCode = this.theme.palette.selectedBg;
      const validBg = bgCode >= 0 && bgCode <= 255;
      const statusFgCode = this.getStatusColorCode(task);

      // Format: "▶ fn-1.3 Task title..."
      const depStr = this.formatDependency(task);

      // Build task line content
      const idDisplay = task.id;
      const availableForTitle = Math.max(
        0,
        contentWidth -
          visibleWidth(icon) -
          visibleWidth(idDisplay) -
          visibleWidth(depStr) -
          3
      );
      const truncatedTitle = truncateToWidth(
        task.title,
        availableForTitle,
        '…'
      );

      if (isSelected) {
        // Selected row with background highlight
        const dimFgCode = this.theme.palette.dim;
        const textFgCode = this.theme.palette.text;

        let content: string;
        if (validBg) {
          content =
            chalk.bgAnsi256(bgCode).ansi256(statusFgCode)(icon) +
            chalk.bgAnsi256(bgCode).ansi256(dimFgCode)(` ${idDisplay} `) +
            chalk.bgAnsi256(bgCode).ansi256(textFgCode)(truncatedTitle) +
            (depStr
              ? chalk.bgAnsi256(bgCode).ansi256(statusFgCode)(depStr)
              : '');
        } else {
          content =
            chalk.ansi256(statusFgCode)(icon) +
            chalk.ansi256(dimFgCode)(` ${idDisplay} `) +
            chalk.ansi256(textFgCode)(truncatedTitle) +
            (depStr ? chalk.ansi256(statusFgCode)(depStr) : '');
        }

        const rawLen =
          visibleWidth(icon) +
          visibleWidth(idDisplay) +
          visibleWidth(truncatedTitle) +
          visibleWidth(depStr) +
          2;
        const paddingNeeded = Math.max(0, contentWidth - rawLen);
        const padding = validBg
          ? chalk.bgAnsi256(bgCode)(' '.repeat(paddingNeeded))
          : ' '.repeat(paddingNeeded);

        const fullContent = ' ' + content + padding + ' ';
        lines.push(
          this.theme.border(borderV) +
            truncateToWidth(fullContent, width - 2, '…') +
            this.theme.border(borderV)
        );
      } else {
        // Unselected row
        const content =
          colorFn(icon) +
          this.theme.dim(` ${idDisplay} `) +
          truncatedTitle +
          (depStr ? colorFn(depStr) : '');

        const rawLen =
          visibleWidth(icon) +
          visibleWidth(idDisplay) +
          visibleWidth(truncatedTitle) +
          visibleWidth(depStr) +
          2;
        const paddingNeeded = Math.max(0, contentWidth - rawLen);

        const fullContent = ' ' + content + ' '.repeat(paddingNeeded) + ' ';
        lines.push(
          this.theme.border(borderV) +
            truncateToWidth(fullContent, width - 2, '…') +
            this.theme.border(borderV)
        );
      }
    }

    // Scroll indicator at bottom
    if (this.tasks.length > this.maxVisible) {
      const scrollInfo = `${this.selectedIndex + 1}/${this.tasks.length}`;
      const scrollLine = padToWidth(
        this.theme.dim(` ↕ ${scrollInfo}`),
        contentWidth
      );
      lines.push(
        this.theme.border(borderV) +
          ' ' +
          scrollLine +
          ' ' +
          this.theme.border(borderV)
      );
    }

    return lines;
  }

  handleInput(data: string): void {
    // Early return when no tasks to prevent invalid index mutations
    if (this.tasks.length === 0) return;

    // j or down arrow - move down
    if (matchesKey(data, 'j') || matchesKey(data, 'down')) {
      this.selectedIndex =
        this.selectedIndex === this.tasks.length - 1
          ? 0
          : this.selectedIndex + 1;
      this.notifySelectionChange();
    }
    // k or up arrow - move up
    else if (matchesKey(data, 'k') || matchesKey(data, 'up')) {
      this.selectedIndex =
        this.selectedIndex === 0
          ? this.tasks.length - 1
          : this.selectedIndex - 1;
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
