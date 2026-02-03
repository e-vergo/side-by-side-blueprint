# Side-by-Side Blueprint Monorepo

> **This monorepo is the primary location for development of the Side-by-Side Blueprint project.**

---

## First and foremost

Every line of every file in this repo and its sub-repos has been written with Claude Code. This has been true, for all intents and purposes, since the start of all of those repo, and will be so moving forward.


## Dual Nature

The project has multiple distinct but interwoven purposes, and so does this repository:

### 1. Tool Development

A coherent, compact, and dedicated environment for developing the **Side-by-Side Blueprint tool** itself:

- **SubVerso** - Syntax highlighting with O(1) indexed lookups
- **Verso** - Document framework with SBSBlueprint/VersoPaper genres
- **LeanArchitect** - `@[blueprint]` attribute with 8 metadata + 3 status options
- **Dress** - Artifact generation, graph layout, validation
- **Runway** - Site generator, dashboard, paper/PDF

### 2. Meta-Tooling Development

The active development environment for **agentic and project-specific development tools**:

- **Archive system** - Event log, state machine, context provider
- **Validators** - T1-T8 quality scoring, visual compliance
- **MCP tools** - Lean LSP integration via sbs-lsp-mcp (51 tools: 18 Lean + 33 SBS)
- **Skills** - `/task`, `/update-and-archive` workflow definitions
- **Agents** - `sbs-developer`, `sbs-oracle` agent specifications

---

## Why This Matters for Agents

Agents working in this codebase are simultaneously:

1. **Building the product** (SBS tool)
2. **Building the tools that build the product** (archive system, validators, MCP tools)
3. **Being tracked by the tools they're building** (strange loops)

This recursive structure is intentional.

The archive system that tracks your work is itself being developed in this repo. The validators that check your output are themselves subjects of validation. The MCP tools you'll use were built by previous agents whose work was tracked by those same tools.

### Implications

- Changes to meta-tooling affect future agents (including future versions of yourself)
- The archive is the source of truth for project state - treat it as such
- Quality scoring applies to both product and meta-tooling work
- Context injection means you benefit from what previous agents learned

### Critical requirement - one agent at a time
- Execept for the `/update-and-archive` skill, there will only ever be one agent working on the repo at a time
- This eliminates the signifigant overhead required in preventing collisions
- Helps reduce costs
- Allows for meaningful human oversight will allowing large amounts of autonomy to the agents


---

## What This Means in Practice

### Use `/task` for Comprehensive Data Collection

All significant development work should go through the `/task` skill. This ensures:
- Your work is tracked in the archive
- Quality metrics are captured
- Context is available for future agents
- Epochs provide natural checkpoints

### The Archive Is the Source of Truth

The archive tracks:
- What skill is currently active (`global_state`)
- What phase you're in (`substate`)
- What happened since the last epoch (`entries`)
- Aggregate metrics (`epoch_summary`)
- Allows for meaningful and powerful data collection (crucial for long term analysis and introspection)

When in doubt about project state, the archive knows.

### Changes to Meta-Tooling Are High-Impact

When you modify:
- Archive system (`dev/scripts/sbs/archive/`)
- Validators (`dev/scripts/sbs/tests/validators/`)
- Skills (`.claude/skills/`)
- Agent definitions (`.claude/agents/`)

You are changing the environment for all future work. Think carefully.

### The Single-Agent Constraint Is Architectural

Agents are spawned sequentially, never in parallel. This is not a limitation - it's a foundation:
- Archive state remains consistent
- No race conditions on ledgers
- Context injection works reliably
- Epochs have clear boundaries

---

## Quick Reference

### Build Commands

```bash
./dev/build-sbs-test.sh   # SBS-Test (~2 min)
./dev/build-gcr.sh        # GCR (~5 min)
./dev/build-pnt.sh        # PNT (~20 min)
```

### Key Documentation

| Document | Purpose | Category |
|----------|---------|----------|
| [CLAUDE.md](../../../CLAUDE.md) | Orchestration model, user preferences | Config |
| [TAXONOMY.md](../permanent/TAXONOMY.md) | Document classification system | Permanent |
| [Archive_Orchestration_and_Agent_Harmony.md](../permanent/Archive_Orchestration_and_Agent_Harmony.md) | Script-agent boundary, archive roles | Permanent |
| [ARCHITECTURE.md](../permanent/ARCHITECTURE.md) | Build pipeline, components | Permanent |
| [GOALS.md](../permanent/GOALS.md) | Project vision, problem statement | Permanent |
| [dev/storage/README.md](../../storage/README.md) | CLI commands, validators, archive | Hub |

### Skills

| Skill | Invocation | Purpose |
|-------|------------|---------|
| task | `/task` | General-purpose agentic task execution |
| update-and-archive | `/update-and-archive` | Documentation refresh, porcelain state |

### Agent Types

| Agent | Purpose |
|-------|---------|
| `sbs-developer` | Implementation work with deep architectural knowledge |
| `sbs-oracle` | Pre-compiled codebase knowledge for instant Q&A |

---

## Repository Structure

```
Side-by-Side-Blueprint/
  forks/                    # Forked Lean 4 repositories
    subverso/               # Syntax highlighting
    verso/                  # Document framework
    LeanArchitect/          # @[blueprint] attribute
  toolchain/                # Core toolchain components
    Dress/                  # Artifact generation
    Runway/                 # Site generator
    SBS-Test/               # Minimal test project
    dress-blueprint-action/ # CI/CD + assets
  showcase/                 # Production examples
    General_Crystallographic_Restriction/
    PrimeNumberTheoremAnd/
  dev/                      # Development tooling
    scripts/                # sbs CLI and Python tooling
    storage/                # Archive data
    markdowns/
      permanent/            # Architectural bedrock
      living/               # Current state (this file)
    build-*.sh              # One-click build scripts
```

---

## For the Public README

The user-facing project overview (features, getting started, examples) is in:
- Individual repository READMEs
- [GOALS.md](../permanent/GOALS.md) for vision
- [ARCHITECTURE.md](../permanent/ARCHITECTURE.md) for technical details

This document (`living/README.md`) is for agents working in the codebase.
