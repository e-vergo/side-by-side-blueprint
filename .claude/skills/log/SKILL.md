---
name: log
description: Quick capture of issues and ideas to GitHub
version: 1.0.0
---

# /log - Quick Issue Capture

Rapidly capture bugs, features, and ideas as GitHub issues without breaking flow.

---

## Invocation

| Pattern | Behavior |
|---------|----------|
| `/log` | Fully interactive - prompts for all fields |
| `/log <text>` | Parse text, infer type from keywords, confirm/fill gaps |
| `/log --bug\|--feature\|--idea <text>` | Explicit type, text becomes title |
| `/log --bug --body "details" <title>` | Explicit everything, create immediately |

---

## Parsing Rules

### Type Inference from Keywords

When type is not explicit, scan the input for these keywords:

| Type | Keywords |
|------|----------|
| **bug** | "bug", "fix", "broken", "error", "issue", "crash", "fail", "wrong", "doesn't work" |
| **feature** | "add", "implement", "feature", "new", "support", "enable", "create", "make" |
| **idea** | "idea", "maybe", "consider", "could", "should", "what if", "wonder", "might" |

**Priority:** If multiple types match, use the first keyword found (left-to-right scan).

**Default:** If no keywords match, ask the user.

### Title Extraction

- If `--body` provided: remaining text after flags is the title
- Otherwise: entire text (after type flag if present) is the title
- If text is long (>80 chars): first sentence or clause becomes title, rest becomes body

---

## Workflow

1. **Parse input** for title, body, and type flags
2. **Infer type** from keywords if not explicit
3. **If type unclear:** Ask user with options:
   - [B] Bug - Something is broken
   - [F] Feature - New functionality
   - [I] Idea - Something to consider
4. **If title missing:** Ask "What would you like to log?"
5. **Create issue** via `sbs_issue_create` MCP tool:
   - `title`: The issue title
   - `body`: Optional description (empty string if none)
   - `label`: One of "bug", "feature", "idea"
6. **On success:**
   - Archive with `issue_refs` populated
   - Report issue number and URL to user
7. **On failure:**
   - Report error to user
   - Do NOT archive failed attempts

---

## Archive Protocol

This is an **atomic skill** - single archive upload on success, no global_state tracking.

**Archive command:**
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --issue-refs <number>
```

**Archive entry fields:**
- `trigger`: "skill"
- `issue_refs`: `[<new_issue_number>]`
- No `global_state` (atomic operation)

---

## Examples

### Fully Interactive

```
User: /log

Claude: What would you like to log?

User: The sidebar doesn't highlight the active section

Claude: I'll categorize this as a **bug** (detected "doesn't"). Create this issue?
  Title: The sidebar doesn't highlight the active section
  Type: Bug

User: yes

Claude: Created issue #42: "The sidebar doesn't highlight the active section"
        https://github.com/e-vergo/Side-By-Side-Blueprint/issues/42
```

### Inferred Type

```
User: /log fix the graph layout when cycles present

Claude: Creating bug issue (detected "fix"):
  Title: Fix the graph layout when cycles present

Created issue #43: https://github.com/...
```

### Explicit Type

```
User: /log --feature add dark mode toggle to paper view

Claude: Created feature issue #44: "Add dark mode toggle to paper view"
        https://github.com/...
```

### Full Specification

```
User: /log --idea --body "Could show node metadata on hover instead of requiring click" tooltips for graph nodes

Claude: Created idea issue #45: "Tooltips for graph nodes"
        https://github.com/...
```

---

## Error Handling

| Error | Response |
|-------|----------|
| MCP tool fails | Report error message to user, do not archive |
| `gh` not authenticated | Instruct: "Run `gh auth login` to authenticate with GitHub" |
| Empty title after parsing | Ask user for title |
| Network error | Report and suggest retry |

---

## Labels

The skill uses these GitHub labels (should exist in repo):

- `bug` - Something isn't working
- `feature` - New feature or request
- `idea` - Idea or suggestion for consideration
- `ai-authored` - **Always applied** to indicate AI authorship

If a type label doesn't exist, the issue will still be created but without that label.

---

## AI Attribution

**All issues created by this skill are transparently marked as AI-authored:**

1. **Label:** `ai-authored` label is always added (purple badge)
2. **Footer:** Attribution footer appended to body:
   ```
   ---
   🤖 Created with [Claude Code](https://claude.ai/code)
   ```

This ensures clear provenance and transparency for all AI-generated content.
