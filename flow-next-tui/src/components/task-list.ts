/**
 * TaskList component for displaying task list with status icons and selection.
 * Implements j/k navigation, Enter to select, and background highlight for selected row.
 */

import type { Component } from '@mariozechner/pi-tui';
import { matchesKey, truncateToWidth } from '@mariozechner/pi-tui';

import { padToWidth, visibleWidth } from '../lib/render.ts';
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
    this.selectedIndex = props.selectedIndex;
    this.onSelectCb = props.onSelect;
    this.onSelectionChangeCb = props.onSelectionChange;
    this.theme = props.theme;
    this.maxVisible = props.maxVisible ?? 10;
    this.useAscii = props.useAscii ?? false;
  }

  /** Update tasks list */
  setTasks(tasks: EpicTask[]): void {
    this.tasks = tasks;
    // Clamp selection to valid range
    if (this.selectedIndex >= tasks.length) {
      this.selectedIndex = Math.max(0, tasks.length - 1);
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
    const newIndex = Math.max(0, Math.min(index, this.tasks.length - 1));
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

  /** Format dependency indicator for blocked tasks only */
  private formatDependency(task: EpicTask): string {
    // Only show dependency indicator for blocked tasks
    if (task.status !== 'blocked' || task.depends_on.length === 0) return '';
    // Show first blocker in short form (just the task number part)
    const dep = task.depends_on[0];
    // Extract task number from "fn-N.M" -> "N.M"
    const short = dep?.replace(/^fn-/, '') ?? '';
    return ` → ${short}`;
  }

  render(width: number): string[] {
    if (this.tasks.length === 0) {
      return [this.theme.dim('  No tasks')];
    }

    const lines: string[] = [];

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

      // Format: "● fn-1.3 Add validation..."
      const iconWidth = this.useAscii ? 3 : 1;
      const prefix = colorFn(icon) + ' ';
      const prefixWidth = iconWidth + 1;

      // Render full task id (fn-1.3)
      const idStr = this.theme.dim(task.id) + ' ';
      const idWidth = task.id.length + 1;

      // Calculate space for title
      const depStr = this.formatDependency(task);
      const depWidth = visibleWidth(depStr);
      const titleMaxWidth = Math.max(10, width - prefixWidth - idWidth - depWidth - 2);

      // Truncate title
      const truncatedTitle = truncateToWidth(task.title, titleMaxWidth, '…');

      // Build the line
      let line = prefix + idStr + truncatedTitle;
      if (depStr) {
        line += this.theme.warning(depStr);
      }

      // Apply background highlight for selected row
      if (isSelected) {
        // Pad to full width before applying background
        const padded = padToWidth(line, width);
        lines.push(this.theme.selectedBg(padded));
      } else {
        lines.push(line);
      }
    }

    // Add scroll indicator if needed
    if (this.tasks.length > this.maxVisible) {
      const scrollInfo = this.theme.dim(
        `  (${this.selectedIndex + 1}/${this.tasks.length})`
      );
      lines.push(scrollInfo);
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
