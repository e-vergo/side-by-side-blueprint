---
name: log
description: Quick capture of issues and ideas to GitHub with enriched labels
version: 2.0.0
---

# /log - Quick Issue Capture

Rapidly capture bugs, features, and ideas as GitHub issues without breaking flow. Applies multi-dimensional labels from the project taxonomy for rich categorization.

---

## Invocation

| Pattern | Behavior |
|---------|----------|
| `/log` | Fully interactive - prompts for all fields |
| `/log <text>` | Parse text, infer type from keywords, confirm/fill gaps |
| `/log --bug\|--feature\|--idea <text>` | Explicit type, text becomes title |
| `/log --bug --body "details" <title>` | Explicit everything, create immediately |
| `/log --area sbs <text>` | Explicit area, infer type from text |
| `/log --area devtools --feature <text>` | Explicit area and type |

---

## Labels

**Available labels:** Read `dev/storage/taxonomy.yaml` for the full label list, counts, and dimensions. The taxonomy is the source of truth -- do not hardcode label counts or enumerate all labels here.

Each issue receives labels from multiple dimensions:

**Always applied:**
- `origin:agent` -- all `/log` issues are agent-filed

**Required (one each):**
- **Type** -- a subtype from the `type` dimension (e.g., bug:visual, feature:new)
- **Area** -- an area label from `area_sbs`, `area_devtools`, or `area_lean` dimensions

**Conditional (applied when keywords strongly signal):**
- **Impact** -- from the `impact` dimension
- **Friction** -- from the `friction` dimension
- **Scope** -- from the `scope` dimension

Multiple labels per dimension are allowed when the issue genuinely spans categories.

---

## Parsing Rules

### Type Inference from Keywords

**Note:** Label names in the tables below must match `dev/storage/taxonomy.yaml`. If the taxonomy changes (labels renamed, added, or removed), update these tables to match.

When type is not explicit, scan the input for these keywords:

| Subtype | Keywords |
|---------|----------|
| bug:visual | "visual", "display", "render", "layout", "CSS", "style", "looks wrong", "misaligned", "ugly", "broken layout" |
| bug:functional | "bug", "broken", "error", "crash", "fail", "wrong", "doesn't work", "incorrect" |
| bug:build | "build fail", "lake error", "compile error", "lakefile", "build broken" |
| bug:regression | "regression", "worked before", "broke", "used to work", "was working" |
| bug:data | "ledger", "data wrong", "manifest", "archive corrupt", "missing data" |
| feature:new | "add", "implement", "new", "create", "support", "enable", "introduce" |
| feature:enhancement | "improve", "enhance", "better", "upgrade", "optimize", "refine" |
| feature:integration | "integrate", "connect", "bridge", "combine", "link" |
| idea:exploration | "idea", "explore", "what if", "wonder", "might", "consider" |
| idea:design | "design", "mockup", "wireframe", "UX", "layout concept" |
| idea:architecture | "architecture", "restructure", "rethink", "redesign system" |
| behavior | "personality", "tone", "communication", "workflow rule", "meta-cognitive", "how claude", "claude should" |
| housekeeping:docs | "document", "readme", "docs", "documentation" |
| housekeeping:cleanup | "cleanup", "refactor", "tidy", "organize", "dead code" |
| housekeeping:tooling | "tooling", "script", "cli command", "maintenance" |
| housekeeping:debt | "debt", "tech debt", "shortcut", "hack", "workaround" |
| housekeeping:migration | "migrate", "migration", "schema", "format change" |
| investigation | "investigate", "debug", "figure out", "understand", "look into", "root cause", "profile" |

**Priority:** If multiple subtypes match, prefer the most specific match. For example, "build broken" matches `bug:build` over `bug:functional` even though "broken" appears in both.

**Default:** If no keywords match, ask the user with options:
- [B] Bug (visual / functional / build / regression / data)
- [F] Feature (new / enhancement / integration)
- [I] Idea (exploration / design / architecture)
- [V] Behavior (personality, workflow rules)
- [H] Housekeeping (docs / cleanup / tooling / debt / migration)
- [X] Investigation (debugging, root cause)

### Area Inference from Keywords

When area is not explicit, scan the input for these keywords:

| Area | Keywords |
|------|----------|
| area:sbs:graph | "graph", "dep graph", "dependency graph", "node", "edge", "layout" |
| area:sbs:dashboard | "dashboard", "stats panel", "key theorems", "project notes" |
| area:sbs:paper | "paper", "ar5iv", "verification badge" |
| area:sbs:pdf | "pdf", "tectonic", "pdflatex" |
| area:sbs:sidebar | "sidebar", "navigation", "chapter panel" |
| area:sbs:modal | "modal", "popup", "detail view" |
| area:sbs:theme | "theme", "dark mode", "light mode", "toggle theme" |
| area:sbs:css | "css", "stylesheet", "variable", "common.css" |
| area:sbs:js | "javascript", "js", "plastex.js", "verso-code.js", "tippy" |
| area:sbs:blueprint | "blueprint attribute", "@[blueprint]", "metadata field" |
| area:sbs:color-model | "status color", "color model", "notReady", "fullyProven" |
| area:sbs:tooltips | "tooltip", "hover", "tippy", "type signature popup" |
| area:sbs:latex | "latex", "plastex", "inputleanmodule", "tex" |
| area:sbs:highlighting | "highlighting", "syntax", "rainbow bracket", "subverso" |
| area:sbs:chapter | "chapter", "side-by-side", "proof toggle" |
| area:sbs:ci | "ci", "github action", "deployment", "ci/cd" |
| area:devtools:archive | "archive", "entry", "epoch", "upload" |
| area:devtools:cli | "cli", "sbs command", "subcommand" |
| area:devtools:mcp | "mcp", "mcp tool", "mcp server" |
| area:devtools:validators | "validator", "T1", "T2", "T5", "T6", "quality score" |
| area:devtools:oracle | "oracle", "concept index", "knowledge base" |
| area:devtools:skills | "skill", "skill definition", "SKILL.md" |
| area:devtools:tagging | "tag", "auto-tag", "tagging rule" |
| area:devtools:gates | "gate", "gate failure", "threshold" |
| area:devtools:session-data | "session", "jsonl", "session data", "extraction" |
| area:devtools:quality-ledger | "quality ledger", "score ledger", "staleness" |
| area:devtools:compliance | "compliance", "compliance ledger", "page criteria" |
| area:devtools:capture | "screenshot", "capture", "playwright" |
| area:devtools:porcelain | "porcelain", "git push", "submodule commit" |
| area:devtools:state-machine | "state machine", "global_state", "skill state", "handoff" |
| area:devtools:self-improve | "self-improve", "self-improvement", "introspect", "pillar", "finding" |
| area:devtools:question-analysis | "question analysis", "AskUserQuestion" |
| area:devtools:test-suite | "test", "pytest", "evergreen", "test tier" |
| area:lean:architect | "LeanArchitect", "lean architect", "blueprint attribute" |
| area:lean:dress | "Dress", "artifact generation", "dressed" |
| area:lean:runway | "Runway", "site generation", "runway.json" |
| area:lean:verso | "Verso", "genre", "SBSBlueprint" |
| area:lean:subverso | "SubVerso", "syntax highlighting" |
| area:lean:lakefile | "lakefile", "lake", "lake build", "lake update" |
| area:lean:manifest | "manifest", "manifest.json" |
| area:lean:dressed-artifacts | "dressed artifact", "decl.html", "decl.json" |

**Priority:** If multiple areas match, include all matching areas as labels (multi-label is encouraged for cross-cutting issues).

**Default:** If no area keywords match, omit area labels rather than guessing.

### Conditional Inference (applied when keywords strongly signal)

**Impact:**

| Label | Keywords |
|-------|----------|
| impact:visual | "visual", "looks", "appearance", "display" |
| impact:functional | "behavior", "logic", "output", "result" |
| impact:performance | "slow", "fast", "performance", "speed", "timeout" |
| impact:dx | "developer experience", "ergonomic", "convenient" |
| impact:data-quality | "data quality", "data richness", "tracking" |
| impact:friction-reduction | "friction", "pain point", "smoother", "easier" |

**Friction:**

| Label | Keywords |
|-------|----------|
| friction:context-loss | "context loss", "compaction", "forgot", "re-explain" |
| friction:tooling-gap | "missing tool", "no tool for", "had to manually" |
| friction:slow-feedback | "slow build", "waiting", "takes too long" |
| friction:manual-step | "manual", "by hand", "automate this" |
| friction:signal-noise | "noisy", "too many", "hard to find" |
| friction:repeated-work | "again", "repeated", "redo", "duplicate effort" |

**Scope:**

| Label | Keywords |
|-------|----------|
| scope:cross-repo | "cross-repo", names 2+ repos |
| scope:architectural | "architecture", "fundamental", "redesign" |
| scope:config-only | "config", "CLAUDE.md", "yaml", "json config" |

These conditional labels are only applied when the keyword match is strong and unambiguous. Do not force them -- omitting is better than misapplying.

### Title Extraction

- If `--body` provided: remaining text after flags is the title
- Otherwise: entire text (after type flag if present) is the title
- If text is long (>80 chars): first sentence or clause becomes title, rest becomes body

---

## Workflow

1. **Parse input** for title, body, type flags, and area flags
2. **Infer type** from keywords if not explicit
3. **If type unclear:** Ask user with options:
   - [B] Bug (visual / functional / build / regression / data)
   - [F] Feature (new / enhancement / integration)
   - [I] Idea (exploration / design / architecture)
   - [V] Behavior (personality, workflow rules)
   - [H] Housekeeping (docs / cleanup / tooling / debt / migration)
   - [X] Investigation (debugging, root cause)
4. **Infer area** from keywords if not explicit
5. **If title missing:** Ask "What would you like to log?"
6. **Infer conditional labels** (impact, friction, scope) from keywords
7. **Show confirmation:**

```
Creating issue:
  Title: Graph nodes overlap when cycle present
  Labels: origin:agent, bug:visual, area:sbs:graph, impact:visual

[Y] Create  [E] Edit labels  [C] Cancel
```

When user selects [E], present current labels with option to add/remove from taxonomy.

8. **Create issue** via `sbs_issue_create` MCP tool:
   - `title`: The issue title
   - `body`: Optional description
   - `labels`: `["origin:agent", "<type>", "<area>", ...optional impact/friction/scope...]`
9. **On success:**
   - Archive with `issue_refs` populated
   - Report issue number, URL, and labels to user
10. **On failure:**
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

Claude: I'll categorize this as **bug:visual** (detected "doesn't" + "sidebar").

Creating issue:
  Title: Sidebar doesn't highlight the active section
  Labels: origin:agent, bug:visual, area:sbs:sidebar, impact:visual

[Y] Create  [E] Edit labels  [C] Cancel

User: Y

Claude: Created issue #42: "Sidebar doesn't highlight the active section"
        Labels: origin:agent, bug:visual, area:sbs:sidebar, impact:visual
        https://github.com/e-vergo/Side-By-Side-Blueprint/issues/42
```

### Inferred Type with Multi-Area

```
User: /log graph nodes look wrong in dark mode

Claude: Creating issue:
  Title: Graph nodes look wrong in dark mode
  Labels: origin:agent, bug:visual, area:sbs:graph, area:sbs:theme, impact:visual

[Y] Create  [E] Edit labels  [C] Cancel

User: Y

Claude: Created issue #43: https://github.com/...
```

### Explicit Type

```
User: /log --feature add dark mode toggle to paper view

Claude: Creating issue:
  Title: Add dark mode toggle to paper view
  Labels: origin:agent, feature:new, area:sbs:paper, area:sbs:theme

[Y] Create  [E] Edit labels  [C] Cancel

User: Y

Claude: Created feature issue #44: "Add dark mode toggle to paper view"
        https://github.com/...
```

### Edit Labels Flow

```
User: /log slow build times are painful

Claude: Creating issue:
  Title: Slow build times are painful
  Labels: origin:agent, bug:functional, impact:performance, friction:slow-feedback

[Y] Create  [E] Edit labels  [C] Cancel

User: E

Claude: Current labels:
  1. [x] origin:agent (always included)
  2. [x] bug:functional
  3. [x] impact:performance
  4. [x] friction:slow-feedback

  [A] Add label  [R] Remove label (by number)  [D] Done

User: R 2, A investigation

Claude: Updated labels:
  1. [x] origin:agent
  2. [x] investigation
  3. [x] impact:performance
  4. [x] friction:slow-feedback

  [A] Add label  [R] Remove label (by number)  [D] Done

User: D

Claude: Created issue #46: "Slow build times are painful"
        Labels: origin:agent, investigation, impact:performance, friction:slow-feedback
        https://github.com/...
```

### Full Specification

```
User: /log --idea --body "Could show node metadata on hover instead of requiring click" tooltips for graph nodes

Claude: Creating issue:
  Title: Tooltips for graph nodes
  Labels: origin:agent, idea:design, area:sbs:graph, area:sbs:tooltips

[Y] Create  [E] Edit labels  [C] Cancel

User: Y

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
| Label doesn't exist in repo | Issue still created; missing labels silently skipped by GitHub |

---

## AI Attribution

**All issues created by this skill are transparently marked as AI-authored:**

1. **Label:** `origin:agent` label is always added
2. **Footer:** The MCP tool (`sbs_issue_create`) automatically appends an attribution footer

This ensures clear provenance and transparency for all AI-generated content.
