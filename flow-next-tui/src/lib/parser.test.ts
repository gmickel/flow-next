import { describe, test, expect } from 'bun:test';

import {
  parseLine,
  parseLineMulti,
  parseLines,
  parseChunk,
  getIcon,
  iconForEntry,
  TOOL_ICONS,
  ASCII_ICONS,
} from './parser';

/**
 * Helper to create Claude stream-json format for tool_use
 */
function makeToolUse(name: string, input?: Record<string, unknown>): string {
  return JSON.stringify({
    type: 'assistant',
    message: {
      content: [{ type: 'tool_use', name, input: input ?? {} }],
    },
  });
}

/**
 * Helper to create Claude stream-json format for tool_result
 */
function makeToolResult(content: string, isError = false): string {
  return JSON.stringify({
    type: 'user',
    message: {
      content: [{ type: 'tool_result', content, is_error: isError }],
    },
  });
}

/**
 * Helper to create Claude stream-json format for text
 */
function makeText(text: string): string {
  return JSON.stringify({
    type: 'assistant',
    message: {
      content: [{ type: 'text', text }],
    },
  });
}

describe('parser', () => {
  describe('getIcon', () => {
    test('returns Unicode icons by default', () => {
      expect(getIcon('Read')).toBe('▸');
      expect(getIcon('Write')).toBe('◂');
      expect(getIcon('Bash')).toBe('$');
      expect(getIcon('Task')).toBe('◈');
      expect(getIcon('success')).toBe('✓');
      expect(getIcon('failure')).toBe('✗');
    });

    test('returns ASCII icons when ascii=true', () => {
      expect(getIcon('Read', true)).toBe('>');
      expect(getIcon('Write', true)).toBe('<');
      expect(getIcon('Bash', true)).toBe('$');
      expect(getIcon('Task', true)).toBe('@');
      expect(getIcon('success', true)).toBe('+');
      expect(getIcon('failure', true)).toBe('x');
    });

    test('returns default icon for unknown tools', () => {
      expect(getIcon('UnknownTool')).toBe('◈');
      expect(getIcon('UnknownTool', true)).toBe('@');
    });
  });

  describe('iconForEntry', () => {
    test('returns tool icon for tool entries', () => {
      const entry = { type: 'tool', tool: 'Read', content: 'Read: /a.ts' };
      expect(iconForEntry(entry)).toBe('▸');
      expect(iconForEntry(entry, true)).toBe('>');
    });

    test('returns Bash icon for Bash tool', () => {
      const entry = { type: 'tool', tool: 'Bash', content: 'Bash: npm test' };
      expect(iconForEntry(entry)).toBe('$');
      expect(iconForEntry(entry, true)).toBe('$');
    });

    test('returns success icon for successful responses', () => {
      const entry = { type: 'response', content: 'ok', success: true };
      expect(iconForEntry(entry)).toBe('✓');
      expect(iconForEntry(entry, true)).toBe('+');
    });

    test('returns failure icon for failed responses', () => {
      const entry = { type: 'response', content: 'error', success: false };
      expect(iconForEntry(entry)).toBe('✗');
      expect(iconForEntry(entry, true)).toBe('x');
    });

    test('returns default icon for text responses', () => {
      const entry = { type: 'response', content: 'text' };
      expect(iconForEntry(entry)).toBe('◈');
      expect(iconForEntry(entry, true)).toBe('@');
    });

    test('returns failure icon for error entries', () => {
      const entry = { type: 'error', content: 'error', success: false };
      expect(iconForEntry(entry)).toBe('✗');
      expect(iconForEntry(entry, true)).toBe('x');
    });
  });

  describe('parseLine', () => {
    test('parses tool_use with Read tool', () => {
      const line = makeToolUse('Read', { file_path: '/path/to/file.ts' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'Read',
        content: 'Read: /path/to/file.ts',
      });
    });

    test('parses tool_use with Bash tool', () => {
      const line = makeToolUse('Bash', { command: 'npm test' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'Bash',
        content: 'Bash: npm test',
      });
    });

    test('preserves full Bash commands (truncation done by output panel)', () => {
      const longCommand =
        'npm run build && npm test && npm run lint && npm run format --check';
      const line = makeToolUse('Bash', { command: longCommand });

      const result = parseLine(line);

      // No pre-truncation - full command preserved
      expect(result?.content).toBe(`Bash: ${longCommand}`);
    });

    test('parses tool_use with Glob tool', () => {
      const line = makeToolUse('Glob', { pattern: '**/*.ts' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'Glob',
        content: 'Glob: **/*.ts',
      });
    });

    test('parses tool_use without input', () => {
      const line = makeToolUse('SomeTool');

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'SomeTool',
        content: 'SomeTool',
      });
    });

    test('parses tool_result with content', () => {
      const line = makeToolResult('File contents here...');

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'response',
        content: 'File contents here...',
        success: true,
      });
    });

    test('parses tool_result with error', () => {
      const line = makeToolResult('File not found', true);

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'response',
        content: 'File not found',
        success: false,
      });
    });

    test('parses text message', () => {
      const line = makeText('Thinking about the problem...');

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'response',
        content: 'Thinking about the problem...',
      });
    });

    test('returns null for empty line', () => {
      expect(parseLine('')).toBeNull();
      expect(parseLine('   ')).toBeNull();
      expect(parseLine('\n')).toBeNull();
    });

    test('returns null for malformed JSON', () => {
      expect(parseLine('not json')).toBeNull();
      expect(parseLine('{incomplete')).toBeNull();
      expect(parseLine('{"type":')).toBeNull();
    });

    test('returns null for invalid structure', () => {
      expect(parseLine('{}')).toBeNull();
      expect(parseLine('{"foo": "bar"}')).toBeNull();
      expect(parseLine('"string"')).toBeNull();
      expect(parseLine('123')).toBeNull();
    });

    test('returns null for system type (skipped)', () => {
      const line = JSON.stringify({
        type: 'system',
        message: { content: [{ type: 'text', text: 'system prompt' }] },
      });

      expect(parseLine(line)).toBeNull();
    });

    test('handles WebFetch tool', () => {
      const line = makeToolUse('WebFetch', { url: 'https://example.com' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'WebFetch',
        content: 'WebFetch: https://example.com',
      });
    });

    test('handles WebSearch tool', () => {
      const line = makeToolUse('WebSearch', { query: 'typescript generics' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'WebSearch',
        content: 'WebSearch: typescript generics',
      });
    });

    test('handles Task tool', () => {
      const line = makeToolUse('Task', { description: 'Explore codebase' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'Task',
        content: 'Task: Explore codebase',
      });
    });

    test('handles key aliases for Read (path instead of file_path)', () => {
      const line = makeToolUse('Read', { path: '/alt/path.ts' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'Read',
        content: 'Read: /alt/path.ts',
      });
    });

    test('handles key aliases for Grep (glob instead of pattern)', () => {
      const line = makeToolUse('Grep', { glob: '*.md' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'Grep',
        content: 'Grep: *.md',
      });
    });

    test('shows first string value for unknown tools', () => {
      const line = makeToolUse('CustomTool', { arg1: 'some value' });

      const result = parseLine(line);

      expect(result).toEqual({
        type: 'tool',
        tool: 'CustomTool',
        content: 'CustomTool: some value',
      });
    });

    test('preserves full fallback values (truncation done by output panel)', () => {
      const longValue = 'x'.repeat(60);
      const line = makeToolUse('CustomTool', { arg1: longValue });

      const result = parseLine(line);

      // No pre-truncation
      expect(result?.content).toBe(`CustomTool: ${longValue}`);
    });

    test('parseLineMulti returns all entries from assistant with multiple blocks', () => {
      const line = JSON.stringify({
        type: 'assistant',
        message: {
          content: [
            { type: 'tool_use', name: 'Read', input: { file_path: '/a.ts' } },
            { type: 'tool_use', name: 'Glob', input: { pattern: '*.md' } },
          ],
        },
      });

      const result = parseLineMulti(line);

      expect(result).toHaveLength(2);
      expect(result[0]!.tool).toBe('Read');
      expect(result[1]!.tool).toBe('Glob');
    });
  });

  describe('parseLines', () => {
    test('parses multiple valid lines', () => {
      const lines = [
        makeToolUse('Read', { file_path: '/a.ts' }),
        makeToolResult('file content'),
        makeText('done'),
      ];

      const result = parseLines(lines);

      expect(result).toHaveLength(3);
      expect(result[0]!.type).toBe('tool');
      expect(result[1]!.type).toBe('response');
      expect(result[2]!.type).toBe('response');
    });

    test('filters out invalid lines', () => {
      const lines = [
        makeToolUse('Read', { file_path: '/a.ts' }),
        'invalid json',
        '',
        makeText('valid'),
      ];

      const result = parseLines(lines);

      expect(result).toHaveLength(2);
    });

    test('returns empty array for empty input', () => {
      expect(parseLines([])).toEqual([]);
    });
  });

  describe('parseChunk', () => {
    test('parses complete chunk', () => {
      const chunk = [makeText('line 1'), makeText('line 2'), ''].join('\n');

      const result = parseChunk(chunk);

      expect(result.entries).toHaveLength(2);
      expect(result.remainder).toBe('');
    });

    test('preserves incomplete line as remainder', () => {
      const chunk = [makeText('complete'), '{"type": "ass'].join('\n');

      const result = parseChunk(chunk);

      expect(result.entries).toHaveLength(1);
      expect(result.remainder).toBe('{"type": "ass');
    });

    test('handles chunk with only incomplete line', () => {
      const chunk = '{"type": "partial';

      const result = parseChunk(chunk);

      expect(result.entries).toHaveLength(0);
      expect(result.remainder).toBe('{"type": "partial');
    });

    test('handles empty chunk', () => {
      const result = parseChunk('');

      expect(result.entries).toHaveLength(0);
      expect(result.remainder).toBe('');
    });

    test('handles chunk with single complete line', () => {
      const chunk = makeText('only') + '\n';

      const result = parseChunk(chunk);

      expect(result.entries).toHaveLength(1);
      expect(result.remainder).toBe('');
    });

    test('parses complete last line without trailing newline', () => {
      // JSON without trailing newline (e.g., at end of file)
      const chunk = makeText('final');

      const result = parseChunk(chunk);

      expect(result.entries).toHaveLength(1);
      expect(result.entries[0]!.content).toBe('final');
      expect(result.remainder).toBe('');
    });

    test('parses multiple lines where last has no trailing newline', () => {
      const chunk = [
        makeText('first'),
        makeText('last'), // no \n after
      ].join('\n');

      const result = parseChunk(chunk);

      expect(result.entries).toHaveLength(2);
      expect(result.entries[0]!.content).toBe('first');
      expect(result.entries[1]!.content).toBe('last');
      expect(result.remainder).toBe('');
    });
  });

  describe('icon constants', () => {
    test('TOOL_ICONS has all expected keys', () => {
      const expectedKeys = [
        'Read',
        'Write',
        'Glob',
        'Grep',
        'Edit',
        'Bash',
        'Task',
        'WebFetch',
        'WebSearch',
        'success',
        'failure',
      ];

      for (const key of expectedKeys) {
        expect(key in TOOL_ICONS).toBe(true);
      }
    });

    test('ASCII_ICONS has matching keys to TOOL_ICONS', () => {
      const toolKeys = Object.keys(TOOL_ICONS);
      const asciiKeys = Object.keys(ASCII_ICONS);

      expect(asciiKeys).toEqual(toolKeys);
    });
  });
});
