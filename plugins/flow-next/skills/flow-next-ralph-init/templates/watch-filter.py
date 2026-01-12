#!/usr/bin/env python3
"""
Watch filter for Ralph - parses Claude's stream-json output and shows key events.

Reads JSON lines from stdin, outputs formatted tool calls in TUI style.

Usage:
    watch-filter.py           # Show tool calls only
    watch-filter.py --verbose # Show tool calls + thinking + text responses
"""

import argparse
import json
import os
import sys

# ANSI color codes (match ralph.sh TUI)
if sys.stdout.isatty() and not os.environ.get("NO_COLOR"):
    C_RESET = '\033[0m'
    C_DIM = '\033[2m'
    C_CYAN = '\033[36m'
else:
    C_RESET = C_DIM = C_CYAN = ''

# TUI indentation (3 spaces to match ralph.sh)
INDENT = "   "

# Tool icons
ICONS = {
    "Bash": "🔧",
    "Edit": "📝",
    "Write": "📄",
    "Read": "📖",
    "Grep": "🔍",
    "Glob": "📁",
    "Task": "🤖",
    "WebFetch": "🌐",
    "WebSearch": "🔎",
    "TodoWrite": "📋",
    "AskUserQuestion": "❓",
    "Skill": "⚡",
}

def truncate(s, max_len=60):
    s = s.replace("\n", " ").strip()
    if len(s) > max_len:
        return s[:max_len-3] + "..."
    return s

def format_tool_use(tool_name, tool_input):
    """Format a tool use event for TUI display."""
    icon = ICONS.get(tool_name, "🔹")

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        if desc:
            return f"{icon} Bash: {truncate(desc)}"
        return f"{icon} Bash: {truncate(cmd, 60)}"

    elif tool_name == "Edit":
        path = tool_input.get("file_path", "")
        return f"{icon} Edit: {path.split('/')[-1] if path else 'unknown'}"

    elif tool_name == "Write":
        path = tool_input.get("file_path", "")
        return f"{icon} Write: {path.split('/')[-1] if path else 'unknown'}"

    elif tool_name == "Read":
        path = tool_input.get("file_path", "")
        return f"{icon} Read: {path.split('/')[-1] if path else 'unknown'}"

    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        return f"{icon} Grep: {truncate(pattern, 40)}"

    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        return f"{icon} Glob: {pattern}"

    elif tool_name == "Task":
        desc = tool_input.get("description", "")
        agent = tool_input.get("subagent_type", "")
        return f"{icon} Task ({agent}): {truncate(desc, 50)}"

    elif tool_name == "Skill":
        skill = tool_input.get("skill", "")
        return f"{icon} Skill: {skill}"

    elif tool_name == "TodoWrite":
        todos = tool_input.get("todos", [])
        in_progress = [t for t in todos if t.get("status") == "in_progress"]
        if in_progress:
            return f"{icon} Todo: {truncate(in_progress[0].get('content', ''))}"
        return f"{icon} Todo: {len(todos)} items"

    else:
        return f"{icon} {tool_name}"

def format_tool_result(result):
    """Format a tool result (errors only)."""
    if isinstance(result, dict):
        if result.get("is_error"):
            error = result.get("error", result.get("content", ""))
            return f"{INDENT}{C_DIM}❌ {truncate(str(error), 60)}{C_RESET}"
    elif isinstance(result, str):
        lower = result.lower()
        if "error" in lower or "failed" in lower:
            return f"{INDENT}{C_DIM}⚠️  {truncate(result, 60)}{C_RESET}"
    return None

def main():
    parser = argparse.ArgumentParser(description='Filter Claude stream-json output')
    parser.add_argument('--verbose', action='store_true',
                        help='Show text and thinking in addition to tool calls')
    args = parser.parse_args()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        # Tool use events
        if event_type == "assistant":
            message = event.get("message", {})
            content = message.get("content", [])

            for block in content:
                block_type = block.get("type", "")

                if block_type == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    formatted = format_tool_use(tool_name, tool_input)
                    print(f"{INDENT}{C_DIM}{formatted}{C_RESET}", flush=True)

                elif args.verbose and block_type == "text":
                    text = block.get("text", "")
                    if text.strip():
                        # Show model response
                        print(f"{INDENT}{C_CYAN}💬 {text}{C_RESET}", flush=True)

                elif args.verbose and block_type == "thinking":
                    thinking = block.get("thinking", "")
                    if thinking.strip():
                        # Show thinking (truncated)
                        print(f"{INDENT}{C_DIM}🧠 {truncate(thinking, 100)}{C_RESET}", flush=True)

        # Tool results (show errors only)
        elif event_type == "user":
            message = event.get("message", {})
            content = message.get("content", [])

            for block in content:
                if block.get("type") == "tool_result":
                    result = block.get("content", "")
                    # Handle both string and object content types
                    if not isinstance(result, (str, dict)):
                        result = str(result)
                    formatted = format_tool_result(result)
                    if formatted:
                        print(formatted, flush=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except BrokenPipeError:
        sys.exit(0)
