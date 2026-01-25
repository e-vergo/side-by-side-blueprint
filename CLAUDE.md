# Side-by-Side Blueprint: Development Guide

## Orchestration Model

**By default, the top-level chat discusses with the user and orchestrates `sbs-developer` agents to accomplish tasks, always one at a time.** The top-level chat serves as:
- Communication interface with the user
- Task decomposition and planning
- Agent orchestration and result synthesis

Actual implementation work is delegated to `sbs-developer` agents which have deep architectural knowledge embedded in their prompts.

## Project Context

Building a pure Lean toolchain for formalization documentation that:
- Displays formal proofs alongside LaTeX statements (side-by-side)
- Couples document generation to build for soundness guarantees
- Visualizes dependency graphs to catch logical errors
- Expands what "verified" means beyond just "typechecks"

**This is Lean software development, not proof writing.** The MCP tools are used differently here.

## Repository Map

| Repo | Purpose | Key Files |
|------|---------|-----------|
| **Runway** | Site generator (replaces Python leanblueprint) | `Main.lean`, `Render.lean`, `Theme.lean`, `Latex/Parser.lean` |
| **Dress** | Artifact generation during elaboration | `Capture/ElabRules.lean`, `Generate/Declaration.lean`, `HtmlRender.lean` |
| **LeanArchitect** | `@[blueprint]` attribute and metadata | `Architect/Attribute.lean`, `Architect/Basic.lean` |
| **SubVerso** | Syntax highlighting extraction (fork) | `Highlighting/Highlighted.lean` |
| **SBS-Test** | Minimal test project for fast iteration | `SBSTest/Chapter{1,2,3}/*.lean`, `blueprint/src/blueprint.tex` |
| **General_Crystallographic_Restriction** | Production example (goal reference) | Full formalization project |
| **dress-blueprint-action** | GitHub Action for CI | Automates full pipeline |

## Dependency Chain

```
SubVerso → LeanArchitect → Dress → Runway
                              ↓
                          Consumer projects (SBS-Test)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

## Current Priority

**LaTeX structure parsing**: Runway outputs flat list instead of chapter/section hierarchy.

Goal output should match:
- `goal2.png`: Hierarchical sidebar, numbered theorems (4.1.1), prose between declarations
- `goal1.png`: Clean side-by-side rendering with proof toggle

## Development Workflow

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh
# Serves at localhost:8000
```

Inspect: `.lake/build/runway/` for HTML output, `.lake/build/dressed/` for artifacts.

## MCP Tool Usage

**For Lean software development (not proofs):**

| Tool | Use For |
|------|---------|
| `lean_diagnostic_messages` | Compilation errors after edits |
| `lean_hover_info` | Verso/SubVerso API signatures |
| `lean_completions` | Discover available functions |
| `lean_file_outline` | Module structure overview |
| `lean_local_search` | Find declarations across repos |

**Less relevant:** `lean_goal`, `lean_multi_attempt`, `lean_leansearch`, `lean_loogle` (proof-focused tools)

## Agent Usage

**When to spawn `sbs-developer`:**
- Fixing LaTeX parsing or HTML rendering in Runway
- Debugging artifact generation in Dress
- Cross-repo changes (LeanArchitect → Dress → Runway)
- Running builds and inspecting output
- CSS/JS fixes in Theme.lean or Assets.lean

**How to use:**
1. Discuss task with user, clarify requirements
2. Spawn single `sbs-developer` agent with clear instructions
3. Wait for agent to complete
4. Synthesize results for user
5. Repeat if needed

**Never:** Run multiple agents in parallel for this project. Sequential, one at a time.

## Cross-Repo Editing

1. Identify affected repos via dependency chain
2. Edit upstream first (LeanArchitect before Dress before Runway)
3. Run `build_blueprint.sh` (handles rebuild order)
4. Test with SBS-Test, compare to goal images

## Soundness Vision

The toolchain should enforce:
- No `sorry` in deployments
- Connected dependency graphs (catch Tao-style errors)
- Declaration-label consistency
- Uses completeness vs actual code dependencies

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Work directly in repo files, not scratch files
- Check `lean_diagnostic_messages` after edits
- Test via SBS-Test and visual inspection

## Reference Images

- `goal1.png`: Target quality for individual theorem rendering
- `goal2.png`: Target page structure with chapters/sections/numbered theorems
