# SLS VSCode Extension -- Spec

Companion document to [SLS_PLANNING.md](SLS_PLANNING.md). Defines the user-facing extension that wraps the SLS framework in a purpose-built VSCode interface.

![UI Mockup](assets/SLS_UI_MOCKUP.png)

---

## Core Idea

A single VSCode Webview panel that replaces terminal-based Claude Code interaction for SLS projects. Two zones:

1. **Control Plane** (top) -- Skill buttons, current state indicator, and a chat interface that color-codes by active skill
2. **Archive Plane** (bottom) -- Pancake stack of archive entries, rich-collapsed, with epoch boundaries as dividers

The skill buttons (`Log`, `Task`, `Self-improve`, `End Epoch`) each start a new session pre-loaded with that skill's context. Clicking a button is equivalent to typing `/log`, `/task`, `/self-improve`, or `/update-and-archive` in a Claude Code terminal -- but with a visual identity (color, layout modifiers) that reflects the active skill.

---

## Layout

```
+---------------------------------------------+
| [Current State]  [Log] [Task] [SI] [End]    |
+---------------------------------------------+
|                                             |
|   Chat zone (border color = active skill)   |
|   - Messages render top-down                |
|   - Input box at bottom                     |
|   - Skill-specific chrome (phase indicator, |
|     todo progress, plan preview)            |
|                                             |
+---------------------------------------------+
|  > 2026-02-03 14:22  task  execution  #104  |
|  > 2026-02-03 12:01  build  T5:100 T6:91   |
|  > 2026-02-03 10:30  self-improve  P1-P4    |
|  =========== Epoch 7 ====================== |
|  > 2026-02-02 ...                           |
+---------------------------------------------+
```

### Control Plane Details

**Current State widget:** Small box showing `idle`, `task:execution`, `self-improve:discovery`, etc. Reads from `sbs_skill_status()` or the archive state. Updates on every archive entry.

**Skill buttons:** Four buttons with fixed colors:
| Button | Color | Skill | Claude Code equivalent |
|--------|-------|-------|-----------------------|
| Log | Green | `/log` | Quick issue capture |
| Task | Blue | `/task` | Structured task execution |
| Self-improve | Gold | `/self-improve` | Recursive self-improvement |
| End Epoch | Red | `/update-and-archive` | Epoch close |

Clicking a button:
1. Changes the chat zone border to match the button color
2. Starts a new Claude Code session with the skill's prompt pre-loaded
3. Streams output into the chat zone

**Chat zone:** The primary interaction surface. Functions like a Claude Code text box. Small modifiers per skill:
- **Task:** Phase indicator bar (alignment / planning / execution / finalization)
- **Self-improve:** Pillar progress (which pillars have findings)
- **Log:** Minimal -- just the input and confirmation
- **End Epoch:** Progress through substates (retrospective / readme / oracle / porcelain / upload)

### Archive Plane Details

**Rich collapsed rows:** Each row shows:
- Timestamp
- Trigger icon (build / skill / manual)
- Skill name + substate (if skill-triggered)
- Tags (compact badges)
- Quality score badges (T5, T6, etc.)

**Expand:** Click to reveal full notes, retrospective summary, epoch summary data.

**Epoch dividers:** Visual separators between epochs. Show epoch number and aggregate stats (entry count, date range).

---

## Architecture

### Connection to Claude

The extension must preserve:
- CLAUDE.md integration (project instructions)
- Local permission model (hook restrictions, sandbox)
- Free usage tier (no API billing)

This means the backend **must** be Claude Code, not the Anthropic API directly.

#### Option 1: Claude Code CLI (viable today)

```
Extension                    Claude Code CLI
   |                              |
   |-- spawn process ------------>|
   |   claude --print             |
   |   --session-id <id>          |
   |   --allowedTools [...]       |
   |                              |
   |<-- JSONL stream -------------|
   |   (messages, tool calls,     |
   |    tool results, todos)      |
   |                              |
   |-- stdin (user input) ------->|
   |                              |
```

- Shell to `claude` CLI with `--print` for structured JSONL output
- Parse the stream, render messages in the webview
- Pipe user input from the chat box to stdin
- Skill buttons compose the initial prompt (e.g., `/task #42`)

**Pros:** Works today. Preserves all Claude Code behavior.
**Cons:** Parsing JSONL output is fragile. AskUserQuestion interactions need custom rendering. No official contract on output format stability.

#### Option 2: Claude Code Extension API (ideal, not yet available)

```
Extension                    Claude Code Extension
   |                              |
   |-- vscode.commands ---------> |
   |   claude.startSession({      |
   |     prompt: "/task #42",     |
   |     onMessage: callback      |
   |   })                         |
   |                              |
   |<-- structured callbacks -----|
   |   onMessage, onQuestion,     |
   |   onTodoUpdate, onComplete   |
   |                              |
```

- Extension-to-extension communication via VSCode command palette
- Structured callbacks for messages, questions, todos, completion
- Full control over rendering without parsing raw output

**Pros:** Clean API, stable contract, proper event model.
**Cons:** Does not exist. Would require Anthropic to expose a programmatic interface from the Claude Code VSCode extension.

#### Option 3: Agent SDK (fallback)

- Full control but loses CLAUDE.md, permissions, and free tier
- Only viable if the extension reimplements CLAUDE.md loading and tool permission
- Not recommended unless Options 1/2 are blocked

### Recommended Path

**Ship with Option 1**, design the internal API as if Option 2 exists (clean message/event abstractions). When Claude Code exposes an extension API, swap the backend without touching the UI layer.

```
┌─────────────────────┐
│   Webview UI Layer   │  React or vanilla -- renders messages, buttons, archive
├─────────────────────┤
│   Session Abstraction│  startSession(), sendInput(), onMessage(), onComplete()
├─────────────────────┤
│   CLI Backend        │  Spawns claude process, parses JSONL, emits events
│   (swap to ext API)  │
└─────────────────────┘
```

---

## Data Flow

### Read Path (no Claude Code dependency)

The archive plane is purely read-only and needs no Claude Code connection:

```
Extension --> MCP Server --> Archive files (JSON)
          |
          +--> sbs_archive_state()
          +--> sbs_search_entries()
          +--> sbs_epoch_summary()
          +--> sbs_skill_status()
```

The extension can call MCP tools directly (they're just Python functions) or read the archive index JSON file at `dev/storage/archive/index.json`.

### Write Path (requires Claude Code)

All mutations flow through Claude Code sessions:
- Skill start/transition/end
- File edits
- Git operations
- Archive uploads

The extension never writes directly -- it starts a Claude Code session and lets the agent handle state management.

---

## Skill-Specific UI Modifiers

Each skill gets small layout additions in the chat zone. These are progressive enhancements, not separate views.

### `/task`
- **Phase bar:** Five-segment indicator (alignment / planning / execution / finalization / archive)
- **Issue badge:** If started with `#N`, show issue title and link
- **Todo list:** Mirror the TodoWrite state as a sidebar checklist

### `/self-improve`
- **Pillar badges:** Four indicators for each analysis pillar, lighting up as findings are produced
- **Finding cards:** Collapsible cards for each finding with severity/confidence

### `/log`
- **Minimal:** Just the input and a confirmation card with the created issue link

### `/update-and-archive`
- **Substate progress:** Five-step indicator (retrospective / readme / oracle / porcelain / upload)
- **Repo status grid:** Small grid showing porcelain state per repo (clean/dirty/ahead)

---

## Extension Structure

```
sls-vscode/
  package.json          # Extension manifest, contributes webview
  src/
    extension.ts        # Activation, webview provider registration
    backend/
      session.ts        # Session abstraction (start, input, events)
      cli-backend.ts    # Claude Code CLI implementation
      types.ts          # Message, ToolCall, Question, Todo types
    ui/
      index.html        # Webview entry point
      app.ts            # Main UI controller
      components/
        control-bar.ts  # Skill buttons + state indicator
        chat-zone.ts    # Message rendering + input
        archive-list.ts # Pancake stack of entries
        skill-chrome/   # Per-skill UI modifiers
          task.ts
          self-improve.ts
          log.ts
          update-archive.ts
    data/
      archive-reader.ts # Read archive index/entries directly
      mcp-client.ts     # Call MCP tools for live state
```

---

## Relationship to SLS

This extension IS the SLS user interface for VSCode users. The SLS framework (archive, skills, MCP, CLI) provides the backend; this extension provides the frontend.

```
SLS Framework          SLS Extension
  Archive     <------>   Archive Plane (read)
  Skills      <------>   Skill Buttons (trigger)
  MCP Server  <------>   State Queries (poll)
  CLI         <------>   (fallback for non-VSCode)
  Claude Code <------>   Chat Zone (sessions)
```

Non-VSCode users interact through the terminal + CLI. VSCode users get the same capabilities with a richer interface. The framework is UI-agnostic; the extension is one possible frontend.

---

## Open Questions

1. **MCP tool access from extension:** Call Python MCP tools directly via child process, or run MCP server as a sidecar and use JSON-RPC?
2. **Session persistence:** When VSCode restarts, should the archive plane restore immediately (yes, from files) and should incomplete sessions resume (depends on Claude Code session persistence)?
3. **Multi-workspace:** One extension instance per VSCode window, each with its own SLS project? Or a single instance managing multiple projects?
4. **Notification model:** Should archive entries from background builds (e.g., CI) trigger VSCode notifications? Desktop notifications for epoch completion?
5. **Claude Code output contract:** The JSONL format from `claude --print` is undocumented. Need to audit current output format and determine how stable it is. Alternatively, monitor the Claude Code extension's planned API roadmap.
