/**
 * Header component with two-row layout for flow-next TUI.
 * Row 1: Status icon + branding (left), task ID + title (center-right), timer (far right)
 * Row 2: Iteration + progress (left), epic ID + title (right)
 */

import type { Component } from '@mariozechner/pi-tui';

import { truncateToWidth } from '@mariozechner/pi-tui';

import type { Epic, Task } from '../lib/types.ts';
import type { Theme } from '../themes/index.ts';

import { visibleWidth } from '../lib/render.ts';

/** Status icons for header state */
export const STATE_ICONS = {
  running: '▸',
  idle: '⏸',
  complete: '✓',
} as const;

/** ASCII fallback icons for --ascii mode (use when Unicode symbols not supported) */
export const ASCII_STATE_ICONS = {
  running: '>',
  idle: '|',
  complete: 'x',
} as const;

export interface HeaderProps {
  state: 'running' | 'idle' | 'complete';
  task?: Task;
  epic?: Epic;
  iteration: number;
  taskProgress: { done: number; total: number };
  elapsed: number; // seconds
  theme: Theme;
  /** Optional: use ASCII icons instead of Unicode (default: false) */
  useAscii?: boolean;
}

/**
 * Format elapsed seconds as MM:SS
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Header component - two-row header with status, task, timer, and epic info.
 */
export class Header implements Component {
  private state: HeaderProps['state'];
  private task: Task | undefined;
  private epic: Epic | undefined;
  private iteration: number;
  private taskProgress: { done: number; total: number };
  private elapsed: number;
  private theme: Theme;
  private useAscii: boolean;

  constructor(props: HeaderProps) {
    this.state = props.state;
    this.task = props.task;
    this.epic = props.epic;
    this.iteration = props.iteration;
    this.taskProgress = props.taskProgress;
    this.elapsed = props.elapsed;
    this.theme = props.theme;
    this.useAscii = props.useAscii ?? false;
  }

  /** Update header state */
  update(props: Partial<HeaderProps>): void {
    if (props.state !== undefined) this.state = props.state;
    if (props.task !== undefined) this.task = props.task;
    if (props.epic !== undefined) this.epic = props.epic;
    if (props.iteration !== undefined) this.iteration = props.iteration;
    if (props.taskProgress !== undefined)
      this.taskProgress = props.taskProgress;
    if (props.elapsed !== undefined) this.elapsed = props.elapsed;
    if (props.theme !== undefined) this.theme = props.theme;
    if (props.useAscii !== undefined) this.useAscii = props.useAscii;
  }

  /** Get status icon for current state */
  private getStateIcon(): string {
    const icons = this.useAscii ? ASCII_STATE_ICONS : STATE_ICONS;
    return icons[this.state];
  }

  /** Get status color function for current state */
  private getStateColor(): (s: string) => string {
    switch (this.state) {
      case 'running':
        return this.theme.progress;
      case 'complete':
        return this.theme.success;
      default:
        return this.theme.dim;
    }
  }

  render(width: number): string[] {
    const lines: string[] = [];

    // Row 1: Status icon + branding | task in brackets | timer
    const row1 = this.renderRow1(width);
    lines.push(row1);

    // Row 2: Iteration + progress | epic info
    const row2 = this.renderRow2(width);
    lines.push(row2);

    return lines;
  }

  /**
   * Row 1: [icon] flow-next ... 「task-id title」 MM:SS
   */
  private renderRow1(width: number): string {
    const icon = this.getStateIcon();
    const colorFn = this.getStateColor();
    const timer = formatTime(this.elapsed);
    const timerWidth = visibleWidth(timer);

    // Handle very narrow widths: just show truncated timer
    if (width <= timerWidth) {
      return truncateToWidth(this.theme.dim(timer), width, '');
    }

    // Left side: icon + branding
    const leftContent = `${icon} flow-next`;
    const leftWidth = visibleWidth(leftContent);
    const coloredLeft = colorFn(icon) + ' ' + this.theme.accent('flow-next');

    // Minimum: left + space + timer
    const minWidth = leftWidth + 1 + timerWidth;
    if (width < minWidth) {
      // Truncate left to fit with timer
      const availableForLeft = width - timerWidth - 1;
      if (availableForLeft <= 0) {
        return truncateToWidth(this.theme.dim(timer), width, '');
      }
      const truncatedColoredLeft =
        truncateToWidth(colorFn(icon), visibleWidth(icon), '') +
        ' ' +
        truncateToWidth(
          this.theme.accent('flow-next'),
          availableForLeft - visibleWidth(icon) - 1,
          '…'
        );
      return truncatedColoredLeft + ' ' + this.theme.dim(timer);
    }

    // Task info in brackets (if task exists and fits)
    let taskPart = '';
    let taskPartColored = '';
    if (this.task) {
      const taskId = this.task.id;
      const taskTitle = this.task.title;
      // Available = width - left - gap(1) - timer - space before timer
      // Brackets take 2 chars, need at least 3 for content
      const availableForTask = width - leftWidth - timerWidth - 2; // 2 = gaps

      if (availableForTask > 4) {
        // Enough room for brackets (2) + some content (2+)
        const fullTask = `${taskId} ${taskTitle}`;
        const innerWidth = availableForTask - 2; // subtract brackets
        const truncatedTask = truncateToWidth(fullTask, innerWidth, '…');
        taskPart = `「${truncatedTask}」`;
        taskPartColored =
          this.theme.dim('「') + truncatedTask + this.theme.dim('」');
      }
    }

    // Calculate spacing
    const taskWidth = visibleWidth(taskPart);
    const rightPartWidth = taskWidth + (taskWidth > 0 ? 1 : 0) + timerWidth;
    const gapWidth = Math.max(0, width - leftWidth - rightPartWidth);

    // Build row
    const gap = ' '.repeat(gapWidth);
    const coloredTimer = this.theme.dim(timer);

    let row: string;
    if (taskPartColored) {
      row = coloredLeft + gap + taskPartColored + ' ' + coloredTimer;
    } else {
      row = coloredLeft + gap + coloredTimer;
    }

    // Hard clamp to width
    return truncateToWidth(row, width, '');
  }

  /**
   * Row 2: Iter #N · X/Y tasks ... epic-id title
   */
  private renderRow2(width: number): string {
    const { done, total } = this.taskProgress;

    // Left side: iteration and progress
    const iterPart = `Iter #${this.iteration}`;
    const progressPart = `${done}/${total} tasks`;
    const leftContent = `${iterPart} · ${progressPart}`;
    const leftWidth = visibleWidth(leftContent);

    // Handle very narrow widths: truncate left content
    if (width < leftWidth) {
      // Rebuild with colors, truncated
      const truncatedIter = truncateToWidth(iterPart, width, '…');
      if (visibleWidth(truncatedIter) >= width) {
        return this.theme.dim(truncatedIter);
      }
      const remaining = width - visibleWidth(truncatedIter) - 3; // " · "
      if (remaining <= 0) {
        return this.theme.dim(truncatedIter);
      }
      return (
        this.theme.dim(truncatedIter) +
        this.theme.dim(' · ') +
        this.theme.accent(truncateToWidth(progressPart, remaining, '…'))
      );
    }

    const coloredLeft =
      this.theme.dim(iterPart) +
      this.theme.dim(' · ') +
      this.theme.accent(progressPart);

    // Right side: epic info (if epic exists and fits)
    let epicPart = '';
    let epicPartColored = '';
    if (this.epic) {
      const epicId = this.epic.id;
      const epicTitle = this.epic.title;
      // Available = width - left - gap(1)
      const availableForEpic = width - leftWidth - 1;

      if (availableForEpic > 5) {
        const fullEpic = `${epicId} ${epicTitle}`;
        epicPart = truncateToWidth(fullEpic, availableForEpic, '…');
        epicPartColored = this.theme.dim(epicPart);
      }
    }

    // Calculate spacing
    const epicWidth = visibleWidth(epicPart);
    const gapWidth = Math.max(0, width - leftWidth - epicWidth);
    const gap = ' '.repeat(gapWidth);

    let row: string;
    if (epicPartColored) {
      row = coloredLeft + gap + epicPartColored;
    } else {
      row = coloredLeft + gap;
    }

    // Hard clamp to width
    return truncateToWidth(row, width, '');
  }

  handleInput(_data: string): void {
    // Header doesn't handle input
  }

  invalidate(): void {
    // No cached state to invalidate
  }
}
