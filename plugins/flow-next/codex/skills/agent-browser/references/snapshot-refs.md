# Snapshot and Refs

Compact element references that reduce context usage dramatically for AI agents.

## How Refs Work

Traditional approach:
```
Full DOM/HTML → AI parses → CSS selector → Action (~3000-5000 tokens)
```

agent-browser approach:
```
Compact snapshot → @refs assigned → Direct interaction (~200-400 tokens)
```

## The Snapshot Command

```bash
# Basic snapshot (shows page structure)
agent-browser snapshot

# Interactive snapshot (-i flag) - RECOMMENDED
agent-browser snapshot -i

# Include cursor-interactive elements (onclick, cursor:pointer)
agent-browser snapshot -i -C

# Scope to specific region
agent-browser snapshot -s "#main"

# Limit depth
agent-browser snapshot -d 3
```

### Snapshot Output Format

```
Page: Example Site - Home
URL: https://example.com

@e1 [header]
  @e2 [nav]
    @e3 [a] "Home"
    @e4 [a] "Products"
    @e5 [a] "About"
  @e6 [button] "Sign In"

@e7 [main]
  @e8 [h1] "Welcome"
  @e9 [form]
    @e10 [input type="email"] placeholder="Email"
    @e11 [input type="password"] placeholder="Password"
    @e12 [button type="submit"] "Log In"

@e13 [footer]
  @e14 [a] "Privacy Policy"
```

## Using Refs

Once you have refs, interact directly:

```bash
agent-browser click @e6              # Click "Sign In"
agent-browser fill @e10 "user@example.com"
agent-browser fill @e11 "password123"
agent-browser click @e12             # Submit form
```

## Ref Lifecycle

**IMPORTANT**: Refs are invalidated when the page changes!

```bash
agent-browser snapshot -i
# @e1 [button] "Next"

agent-browser click @e1              # Triggers page change

# MUST re-snapshot to get new refs!
agent-browser snapshot -i
# @e1 [h1] "Page 2"  ← Different element now!
```

### When to Re-Snapshot

Always re-snapshot after:
- Clicking links or buttons that navigate
- Form submissions
- Dynamic content loading (dropdowns, modals)
- Tab switches
- Frame switches

## Ref Notation

```
@e1 [tag type="value"] "text content" placeholder="hint"
│    │   │             │               │
│    │   │             │               └─ Additional attributes
│    │   │             └─ Visible text
│    │   └─ Key attributes shown
│    └─ HTML tag name
└─ Unique ref ID
```

### Common Patterns

```
@e1 [button] "Submit"                    # Button with text
@e2 [input type="email"]                 # Email input
@e3 [input type="password"]              # Password input
@e4 [a href="/page"] "Link Text"         # Anchor link
@e5 [select]                             # Dropdown
@e6 [textarea] placeholder="Message"     # Text area
@e7 [div class="modal"]                  # Container
@e8 [img alt="Logo"]                     # Image
@e9 [checkbox] checked                   # Checked checkbox
@e10 [radio] selected                    # Selected radio
```

## Best Practices

### 1. Always Snapshot Before Interacting

```bash
# CORRECT
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser click @e1

# WRONG
agent-browser open https://example.com
agent-browser click @e1  # Ref doesn't exist yet!
```

### 2. Snapshot Specific Regions

For complex pages, scope the snapshot:

```bash
agent-browser snapshot -s "#main"
agent-browser snapshot @e9  # Snapshot within element
```

### 3. Use Annotated Screenshots for Visual Elements

When elements are visual-only (icons, canvas, charts):

```bash
agent-browser screenshot --annotate
# Labels overlay on elements, refs cached for interaction
agent-browser click @e2
```

## Troubleshooting

### "Ref not found" Error
```bash
# Ref may have changed - re-snapshot
agent-browser snapshot -i
```

### Element Not Visible in Snapshot
```bash
# Scroll down to reveal
agent-browser scroll down 1000
agent-browser snapshot -i

# Wait for dynamic content
agent-browser wait 1000
agent-browser snapshot -i
```

### Too Many Elements
```bash
# Scope to container
agent-browser snapshot -s "#form-section"

# Or get text only
agent-browser get text @e5
```

### Cursor-Interactive Elements Missing
Some elements use `cursor: pointer` or `onclick` without semantic HTML:
```bash
# Use -C flag to include cursor-interactive elements
agent-browser snapshot -i -C
```
