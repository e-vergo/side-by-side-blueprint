---
name: oracle
description: Zero-shot codebase question answering
version: 1.0.0
---

# /oracle - Codebase Question Answering

Answer codebase questions using the pre-compiled concept index. Flag uncertainty explicitly.

---

## Invocation

| Pattern | Behavior |
|---------|----------|
| `/oracle` | Interactive - prompts for question |
| `/oracle <question>` | Direct query |

---

## Archive Protocol

This is an **atomic skill** (single operation, no multi-phase workflow):
- No global_state tracking (lightweight queries)
- Single archive upload on completion (optional, for tracking usage)
- Can run even when another skill owns global_state

---

## Required Reading

Before answering, load the concept index:

```
/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/agents/sbs-oracle.md
```

This file contains:
- Concept Index (concept -> file location)
- File Purpose Map (file -> purpose)
- How-To Patterns (common tasks)
- Gotchas & Anti-Patterns
- Cross-Repo Impact Map

---

## Query Processing

**Priority order:**
1. Factual correctness (accuracy/precision of answer)
2. Response formatting (efficient tokens, full clarity)
3. Speed

**Process:**
1. Parse user question to identify key concepts
2. Search concept index for matches
3. If file locations found, report with paths and brief context
4. If concepts found, explain relationships
5. Flag uncertainty if no clear match ("I don't know" is acceptable)

---

## MCP Tool Integration

The skill can leverage these MCP tools:
- `sbs_oracle_query` - Search the compiled oracle for quick lookups
- `Read` - Read file contents when needed for context
- `Grep` - Search for patterns when concept index is insufficient

---

## Example Sessions

### Direct Query
```
User: /oracle graph layout
Claude: Graph layout is implemented in:
- `toolchain/Dress/Graph/Layout.lean` (~1500 lines)
  - Sugiyama algorithm for layered drawing
  - `assignLayers`, `orderLayers`, `assignXCoordinates`
  - >100 node optimizations (barycenter iterations, transpose skip)
```

### Interactive Mode
```
User: /oracle
Claude: What would you like to know about the codebase?
User: Where are status colors defined?
Claude: Status colors are defined in:
- **Source of truth**: `toolchain/Dress/Graph/Svg.lean` - canonical hex values
- **CSS variables**: `toolchain/dress-blueprint-action/assets/common.css` - must match Lean
```

### Uncertainty
```
User: /oracle quantum entanglement
Claude: I don't know. The concept "quantum entanglement" doesn't appear in the codebase index. This project is about Lean formalization tooling, not physics.
```

---

## When to Use /oracle vs. Other Tools

| Scenario | Use |
|----------|-----|
| "Where is X implemented?" | `/oracle` |
| "How does Y work?" | `/oracle` for overview, then `Read` for details |
| Quick file location lookup | `sbs_oracle_query` MCP tool |
| Deep exploration across multiple files | `Explore` agent |
| Specific code search | `Grep` tool |

---

## Relationship to sbs_oracle_query MCP Tool

The `sbs_oracle_query` MCP tool and `/oracle` skill share the same knowledge base but serve different purposes:

| Aspect | `/oracle` Skill | `sbs_oracle_query` Tool |
|--------|-----------------|-------------------------|
| Invocation | User or agent via skill | Programmatic MCP call |
| Output | Human-readable answer | Structured JSON |
| Follow-up | Can read files, ask questions | Single query/response |
| Archive tracking | Optional upload on completion | No tracking |

---

## Standards

- Never guess - flag uncertainty explicitly
- Prefer file paths over vague references
- Include brief context with each match
- Use sbs_oracle_query for quick lookups before spawning full exploration
