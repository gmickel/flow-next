import type { LogEntry } from './types';

/**
 * Tool icons for display - Unicode symbols for visual appeal
 * Use with width-based padding for alignment
 */
export const TOOL_ICONS = {
  Read: '▸', // file read (triangle pointer)
  Write: '◂', // file write (triangle pointer left)
  Glob: '◦', // pattern search (hollow bullet)
  Grep: '⌕', // content search (search icon) - falls back to /
  Edit: '✎', // edit operation (pencil)
  Bash: '$', // command execution (shell prompt - ASCII)
  Task: '◈', // agent task (diamond)
  WebFetch: '⬇', // web fetch (down arrow)
  WebSearch: '◎', // web search (bullseye)
  success: '✓', // success checkmark
  failure: '✗', // failure X
} as const;

/**
 * ASCII fallbacks for --no-emoji mode
 */
export const ASCII_ICONS = {
  Read: '>',
  Write: '<',
  Glob: '?',
  Grep: '/',
  Edit: '*',
  Bash: '$',
  Task: '@',
  WebFetch: 'v',
  WebSearch: '?',
  success: '+',
  failure: 'x',
} as const;

/**
 * Raw JSON line types from Claude --output-format stream-json
 *
 * Actual format has top-level types: "assistant", "user", "system", "result"
 * with nested message.content arrays containing blocks.
 */

interface ContentBlock {
  type: string;
  name?: string; // tool_use
  input?: unknown; // tool_use
  text?: string; // text block
  thinking?: string; // thinking block
  content?: unknown; // tool_result content
  is_error?: boolean; // tool_result error flag
}

interface MessageWrapper {
  content?: ContentBlock[];
}

interface StreamJsonLine {
  type: string;
  message?: MessageWrapper;
}

/**
 * Safely coerce a value to string (handles non-string content from runtime JSON)
 */
function coerceToString(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }
  if (value == null) {
    return '';
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/**
 * Get icon for a tool (or success/failure indicator)
 * @param tool Tool name or 'success'/'failure'
 * @param ascii Use ASCII fallbacks instead of unicode
 */
export function getIcon(tool: string, ascii = false): string {
  const icons = ascii ? ASCII_ICONS : TOOL_ICONS;
  if (tool in icons) {
    return icons[tool as keyof typeof icons];
  }
  // Default icon for unknown tools
  return ascii ? '@' : '◈';
}

/**
 * Get icon for a LogEntry (uses tool name or success/failure state)
 * @param entry LogEntry to get icon for
 * @param ascii Use ASCII fallbacks instead of unicode
 */
export function iconForEntry(
  entry: { type: string; tool?: string; success?: boolean },
  ascii = false
): string {
  // For tool entries, use tool name
  if (entry.type === 'tool' && entry.tool) {
    return getIcon(entry.tool, ascii);
  }
  // For response/error entries, use success state
  if (entry.success === false) {
    return getIcon('failure', ascii);
  }
  if (entry.success === true) {
    return getIcon('success', ascii);
  }
  // Default for text responses
  return ascii ? '@' : '◈';
}

/**
 * Parse a single JSON line from stream-json format
 * @param line Raw JSON string
 * @returns LogEntry array (may return multiple for assistant messages with multiple blocks)
 */
export function parseLine(line: string): LogEntry | null {
  const entries = parseLineMulti(line);
  return entries.length > 0 ? (entries[0] ?? null) : null;
}

/**
 * Parse a line returning all entries (assistant messages can have multiple tool_use blocks)
 */
export function parseLineMulti(line: string): LogEntry[] {
  const trimmed = line.trim();
  if (!trimmed) {
    return [];
  }

  let parsed: StreamJsonLine;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return [];
  }

  if (!parsed || typeof parsed !== 'object' || !('type' in parsed)) {
    return [];
  }

  const entries: LogEntry[] = [];
  const blocks = parsed.message?.content ?? [];

  switch (parsed.type) {
    case 'assistant': {
      // Extract tool_use and text blocks from assistant message
      for (const block of blocks) {
        if (block.type === 'tool_use') {
          const tool = typeof block.name === 'string' ? block.name : 'unknown';
          entries.push({
            type: 'tool',
            tool,
            content: formatToolInput(tool, block.input),
          });
        } else if (block.type === 'text' && block.text) {
          entries.push({
            type: 'response',
            content: coerceToString(block.text),
          });
        }
      }
      break;
    }

    case 'user': {
      // Extract tool_result blocks from user message
      for (const block of blocks) {
        if (block.type === 'tool_result') {
          const content = coerceToString(block.content);
          entries.push({
            type: 'response',
            content,
            success: !block.is_error,
          });
        }
      }
      break;
    }

    case 'result': {
      // Final result message
      const resultContent = (parsed as { result?: string }).result;
      if (resultContent) {
        entries.push({
          type: 'response',
          content: coerceToString(resultContent),
          success: true,
        });
      }
      break;
    }

    // Skip system messages - not useful for TUI display
  }

  return entries;
}

/**
 * Format tool input for display
 */
function formatToolInput(tool: string, input: unknown): string {
  if (!input || typeof input !== 'object') {
    return tool;
  }

  const obj = input as Record<string, unknown>;

  // Helper to safely get string value with key aliases
  const getString = (...keys: string[]): string | undefined => {
    for (const key of keys) {
      const val = obj[key];
      if (typeof val === 'string') return val;
    }
    return undefined;
  };

  // Extract meaningful info per tool type (with common aliases)
  switch (tool) {
    case 'Read':
    case 'Write':
    case 'Edit': {
      const filePath = getString('file_path', 'path', 'file');
      return filePath ? `${tool}: ${filePath}` : tool;
    }

    case 'Glob':
    case 'Grep': {
      const pattern = getString('pattern', 'glob', 'query', 'regex');
      return pattern ? `${tool}: ${pattern}` : tool;
    }

    case 'Bash': {
      const command = getString('command', 'cmd');
      // Don't pre-truncate - let output panel truncate based on width
      return command ? `${tool}: ${command}` : tool;
    }

    case 'Task': {
      const description = getString('description', 'prompt', 'task');
      return description ? `${tool}: ${description}` : tool;
    }

    case 'WebFetch':
    case 'WebSearch': {
      const url = getString('url', 'uri');
      const query = getString('query', 'q', 'search');
      return url ? `${tool}: ${url}` : query ? `${tool}: ${query}` : tool;
    }

    default: {
      // Fallback: show first string value from input
      // Don't pre-truncate - let output panel handle based on width
      for (const key of Object.keys(obj)) {
        const val = obj[key];
        if (typeof val === 'string' && val.length > 0) {
          return `${tool}: ${val}`;
        }
      }
      return tool;
    }
  }
}

/**
 * Parse multiple lines at once
 * @param lines Array of JSON strings
 * @returns Array of valid LogEntry objects (invalid lines filtered out)
 */
export function parseLines(lines: string[]): LogEntry[] {
  const entries: LogEntry[] = [];
  for (const line of lines) {
    entries.push(...parseLineMulti(line));
  }
  return entries;
}

/**
 * Parse a chunk of text containing multiple newline-separated JSON lines
 * @param chunk Raw text chunk (may contain partial lines)
 * @returns Object with parsed entries and any remaining partial line
 */
export function parseChunk(chunk: string): {
  entries: LogEntry[];
  remainder: string;
} {
  const lines = chunk.split('\n');
  const entries: LogEntry[] = [];

  // Last line may be incomplete - preserve it as remainder
  let remainder = lines.pop() ?? '';

  for (const line of lines) {
    entries.push(...parseLineMulti(line));
  }

  // Try parsing remainder - if valid JSON, it's complete (no trailing newline)
  if (remainder) {
    const lastEntries = parseLineMulti(remainder);
    if (lastEntries.length > 0) {
      entries.push(...lastEntries);
      remainder = '';
    }
  }

  return { entries, remainder };
}
