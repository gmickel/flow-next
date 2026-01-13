/**
 * Header component with "Mission Control" aesthetic.
 * Prominent Ralph branding with status indicator, task context, and timer.
 */

import type { Component } from '@mariozechner/pi-tui';

import { truncateToWidth } from '@mariozechner/pi-tui';

import type { Epic, Task } from '../lib/types.ts';
import type { Theme } from '../themes/index.ts';

import { visibleWidth, padToWidth } from '../lib/render.ts';

/** Status indicators - pulsing dot for running state */
export const STATE_ICONS = {
  running: '●',
  idle: '○',
  complete: '✓',
} as const;

export const ASCII_STATE_ICONS = {
  running: '*',
  idle: 'o',
  complete: '+',
} as const;

export interface HeaderProps {
  state: 'running' | 'idle' | 'complete';
  task?: Task;
  epic?: Epic;
  iteration: number;
  taskProgress: { done: number; total: number };
  elapsed: number;
  theme: Theme;
  useAscii?: boolean;
}

/**
 * Format elapsed time as HH:MM:SS or MM:SS
 */
function formatTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hrs > 0) {
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Header component - Mission Control style with prominent branding.
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

  private getStateIcon(): string {
    return (this.useAscii ? ASCII_STATE_ICONS : STATE_ICONS)[this.state];
  }

  private getStateColor(): (s: string) => string {
    switch (this.state) {
      case 'running':
        return this.theme.success; // Green pulsing dot
      case 'complete':
        return this.theme.accent;
      default:
        return this.theme.dim;
    }
  }

  render(width: number): string[] {
    if (width < 20) return [padToWidth('', width)];

    const lines: string[] = [];
    const borderH = this.useAscii ? '-' : '─';
    const cornerTL = this.useAscii ? '+' : '╭';
    const cornerTR = this.useAscii ? '+' : '╮';
    const cornerBL = this.useAscii ? '+' : '╰';
    const cornerBR = this.useAscii ? '+' : '╯';
    const borderV = this.useAscii ? '|' : '│';

    // Top border with branding label
    const label = ' flow-next ';
    const labelWidth = visibleWidth(label);
    const borderWidth = width - 2;
    const leftBorderLen = Math.floor((borderWidth - labelWidth) / 2);
    const rightBorderLen = borderWidth - leftBorderLen - labelWidth;

    const topBorder =
      this.theme.border(cornerTL) +
      this.theme.border(borderH.repeat(Math.max(0, leftBorderLen))) +
      this.theme.accent(label) +
      this.theme.border(borderH.repeat(Math.max(0, rightBorderLen))) +
      this.theme.border(cornerTR);
    lines.push(topBorder);

    // Content row: status + info
    const icon = this.getStateIcon();
    const colorFn = this.getStateColor();
    const timer = formatTime(this.elapsed);
    const { done, total } = this.taskProgress;

    // Build segments
    const statusSeg =
      colorFn(icon) +
      ' ' +
      (this.state === 'running'
        ? this.theme.text('Running')
        : this.state === 'complete'
          ? this.theme.dim('Done')
          : this.theme.dim('Idle'));
    const iterSeg =
      this.theme.dim('Iter ') + this.theme.accent(`#${this.iteration}`);
    const progressSeg =
      this.theme.accent(`${done}`) +
      this.theme.dim('/') +
      this.theme.text(`${total}`);
    const timerSeg = this.theme.dim('⏱ ') + this.theme.text(timer);

    // Task info (if available)
    let taskSeg = '';
    if (this.task) {
      const taskId = this.task.id;
      taskSeg = this.theme.dim('Task: ') + this.theme.accent(taskId);
    } else if (this.epic) {
      taskSeg = this.theme.dim('Epic: ') + this.theme.accent(this.epic.id);
    }

    // Calculate content width (inside borders)
    const contentWidth = width - 4; // 2 for borders + 2 for padding

    // Build content: left-aligned status info, right-aligned timer
    const leftParts = [statusSeg, iterSeg, progressSeg];
    if (taskSeg) leftParts.push(taskSeg);
    const leftContent = leftParts.join(this.theme.border(' │ '));
    const leftRaw = `${icon} ${this.state === 'running' ? 'Running' : this.state === 'complete' ? 'Done' : 'Idle'} │ Iter #${this.iteration} │ ${done}/${total}${taskSeg ? ` │ Task: ${this.task?.id ?? this.epic?.id}` : ''}`;
    const leftWidth = visibleWidth(leftRaw);
    const timerRaw = `⏱ ${timer}`;
    const timerWidth = visibleWidth(timerRaw);

    const gapWidth = Math.max(1, contentWidth - leftWidth - timerWidth);
    const contentLine =
      ' ' + leftContent + ' '.repeat(gapWidth) + timerSeg + ' ';

    lines.push(
      this.theme.border(borderV) +
        truncateToWidth(contentLine, width - 2, '…') +
        this.theme.border(borderV)
    );

    // Bottom border
    const bottomBorder =
      this.theme.border(cornerBL) +
      this.theme.border(borderH.repeat(width - 2)) +
      this.theme.border(cornerBR);
    lines.push(bottomBorder);

    return lines;
  }

  handleInput(_data: string): void {}

  invalidate(): void {}
}
