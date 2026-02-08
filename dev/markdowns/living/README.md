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
- **MCP tools** - Lean LSP integration via sbs-lsp-mcp (67 tools: 18 Lean + 41 SBS + 5 Browser + 3 Zulip)
- **Skills** - `/task`, `/qa`, `/converge`, `/introspect`, `/update-and-archive` workflow definitions
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

### Agent Concurrency
- Up to 4 concurrent `sbs-developer` agents in any `/task` phase or `/self-improve` when the orchestrator determines work is parallelizable with non-overlapping file scopes
- Multiple read-only exploration agents may run in parallel at all times
- Archive state consistency enforced: single writer for state transitions, no race conditions on ledgers
- Collision avoidance is the orchestrator's responsibility via file-scope isolation in plans


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

### Agent Concurrency Is Architectural

Controlled parallelism across all workflow phases:
- Up to 4 concurrent `sbs-developer` agents when the orchestrator ensures non-overlapping file scopes
- Archive state remains consistent (single writer at a time for state transitions)
- No race conditions on ledgers
- Context injection works reliably
- Applies to all `/task` phases (alignment, planning, execution, finalization) and `/self-improve`

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
| log | `/log` | Quick capture of bugs, features, ideas to GitHub Issues |
| qa | `/qa` | Live interactive browser-driven QA |
| converge | `/converge` | Autonomous QA convergence loop (eval/fix/rebuild) |
| introspect | `/introspect` | Self-improvement across hierarchy levels |
| update-and-archive | `/update-and-archive` | Documentation refresh, porcelain state |

### Agent Types

| Agent | Purpose |
|-------|---------|
| `sbs-developer` | Implementation work with deep architectural knowledge |
| `sbs-oracle` | Pre-compiled codebase knowledge for instant Q&A |
| `sbs-self-improve` | Background introspection after task sessions (L0-LN hierarchy) |

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
