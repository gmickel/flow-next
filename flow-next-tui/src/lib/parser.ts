import type { LogEntry } from './types';

/**
 * Tool icons for display
 */
export const TOOL_ICONS = {
  Read: '→',
  Write: '→',
  Glob: '→',
  Grep: '→',
  Edit: '→',
  Bash: '⚡',
  Task: '◆',
  WebFetch: '◆',
  WebSearch: '◆',
  success: '✓',
  failure: '✗',
} as const;

/**
 * ASCII fallbacks for --no-emoji mode
 */
export const ASCII_ICONS = {
  Read: '>',
  Write: '>',
  Glob: '>',
  Grep: '>',
  Edit: '>',
  Bash: '!',
  Task: '*',
  WebFetch: '*',
  WebSearch: '*',
  success: '+',
  failure: 'x',
} as const;

/**
 * Raw JSON line types from Claude --watch stream-json output
 */
interface ToolCallLine {
  type: 'tool_call';
  tool: string;
  input?: unknown;
}

interface ToolResultLine {
  type: 'tool_result';
  content?: string;
  error?: string;
}

interface TextLine {
  type: 'text';
  content?: string;
}

interface ErrorLine {
  type: 'error';
  message?: string;
}

type StreamJsonLine = ToolCallLine | ToolResultLine | TextLine | ErrorLine;

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
  return ascii ? '*' : '◆';
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
  // Default for text responses (distinct from file ops which use →)
  return ascii ? '*' : '◆';
}

/**
 * Parse a single JSON line from stream-json format
 * @param line Raw JSON string
 * @returns LogEntry or null if parse fails or line is invalid
 */
export function parseLine(line: string): LogEntry | null {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }

  let parsed: StreamJsonLine;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    // Malformed JSON - skip gracefully
    return null;
  }

  // Validate structure
  if (!parsed || typeof parsed !== 'object' || !('type' in parsed)) {
    return null;
  }

  switch (parsed.type) {
    case 'tool_call': {
      // Safely extract tool name (handle non-string values from malformed JSON)
      const rawTool = typeof parsed.tool === 'string' ? parsed.tool.trim() : '';
      const tool = rawTool || 'unknown';
      return {
        type: 'tool',
        tool,
        content: formatToolInput(tool, parsed.input),
      };
    }

    case 'tool_result': {
      // Coerce content/error to string (runtime JSON may not be string)
      const content =
        coerceToString(parsed.content) || coerceToString(parsed.error);
      return {
        type: 'response',
        content,
        success: parsed.error == null,
      };
    }

    case 'text':
      return {
        type: 'response',
        content: coerceToString(parsed.content),
      };

    case 'error':
      return {
        type: 'error',
        content: coerceToString(parsed.message) || 'Unknown error',
        success: false,
      };

    default:
      // Unknown type - skip
      return null;
  }
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
      if (command) {
        return command.length > 60
          ? `${tool}: ${command.slice(0, 57)}...`
          : `${tool}: ${command}`;
      }
      return tool;
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
      // Fallback: show first string value from input (generic preview)
      for (const key of Object.keys(obj)) {
        const val = obj[key];
        if (typeof val === 'string' && val.length > 0) {
          const preview = val.length > 50 ? val.slice(0, 47) + '...' : val;
          return `${tool}: ${preview}`;
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
    const entry = parseLine(line);
    if (entry) {
      entries.push(entry);
    }
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
    const entry = parseLine(line);
    if (entry) {
      entries.push(entry);
    }
  }

  // Try parsing remainder - if valid JSON, it's complete (no trailing newline)
  if (remainder) {
    const lastEntry = parseLine(remainder);
    if (lastEntry) {
      entries.push(lastEntry);
      remainder = '';
    }
  }

  return { entries, remainder };
}
