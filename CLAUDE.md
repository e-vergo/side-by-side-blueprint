# Side-by-Side Blueprint: Development Guide

Pure Lean toolchain for formalization documentation that displays formal proofs alongside LaTeX theorem statements.

---

## How This Document Works

This guide governs Claude Code sessions on the Side-by-Side Blueprint project. It defines:
- **Orchestration structure:** How the top-level chat and `sbs-developer` agents divide labor
- **User preferences:** Communication, planning, and meta-cognitive expectations
- **Domain context:** Architecture, conventions, and project-specific patterns

The user and Claude are actively refining this document together. If something here doesn't match how work is actually proceeding, surface it.

---

## Orchestration Model

The top-level chat is the **orchestrator**. It does not implement--it coordinates.

| Top-Level Chat | `sbs-developer` Agent |
|----------------|----------------------|
| Discusses requirements with user | Executes ALL implementation tasks |
| Decomposes and plans work | Has deep architectural knowledge |
| Spawns agents (one at a time) | Works within defined scope |
| Synthesizes results | Reports outcomes |

**Single Agent Architecture:**
- `sbs-developer` is the ONLY implementation agent
- Only ONE `sbs-developer` agent runs at a time (architectural invariant)
- Multiple read-only exploration agents may run in parallel alongside

---

## Project Context

Building tooling that:
1. Displays formal Lean proofs alongside LaTeX statements (side-by-side)
2. Couples document generation to build for soundness guarantees
3. Visualizes dependency graphs to catch logical errors (Tao incident motivation)
4. Expands what "verified" means beyond just "typechecks"

**This is Lean software development, not proof writing.** MCP tools are used differently here.

---

## Repository Map

| Directory | Repo | Purpose |
|-----------|------|---------|
| `forks/` | **subverso** | Syntax highlighting (O(1) indexed lookups) |
| `forks/` | **verso** | Document framework (SBSBlueprint/VersoPaper genres) |
| `forks/` | **LeanArchitect** | `@[blueprint]` attribute (8 metadata + 3 status options) |
| `forks/` | **sbs-lsp-mcp** | MCP server (29 tools: 18 Lean + 11 SBS) |
| `toolchain/` | **Dress** | Artifact generation + graph layout + validation |
| `toolchain/` | **Runway** | Site generator + dashboard + paper/PDF |
| `toolchain/` | **SBS-Test** | Minimal test project (33 nodes) |
| `toolchain/` | **dress-blueprint-action** | CI/CD action (432 lines) + CSS/JS assets (3,805 lines) |
| `showcase/` | **GCR** | Production example with paper (57 nodes) |
| `showcase/` | **PNT** | Large-scale integration (591 annotations) |
| `dev/scripts/` | - | Python tooling (sbs CLI) |
| `dev/storage/` | - | Build metrics, screenshots, session archives |

### Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

---

## Local Development

### One-Click Build Scripts (Recommended)

```bash
./dev/build-sbs-test.sh   # SBS-Test (~2 min)
./dev/build-gcr.sh        # GCR (~5 min)
./dev/build-pnt.sh        # PNT (~20 min)
```

### Direct Build Script Usage

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/SBS-Test
python ../../dev/scripts/build.py
```

Options: `--dry-run`, `--skip-cache`, `--verbose`, `--capture`

**Required:** `runway.json` must include `assetsDir` pointing to CSS/JS assets.

---

## Visual Testing

**Screenshot capture is the FIRST reflex for any visual/CSS/layout issue.**

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts

# Capture with interactive states
python3 -m sbs capture --project SBSTest --interactive

# Run compliance check
python3 -m sbs compliance --project SBSTest
```

### Standard Workflow

1. **Build:** `python ../../dev/scripts/build.py`
2. **Capture:** `python3 -m sbs capture --interactive`
3. **Make changes** to CSS/JS/Lean/templates
4. **Rebuild and re-capture**
5. **Validate:** `python3 -m sbs compliance`

---

## When to Spawn `sbs-developer`

Spawn an agent for:
- Fixing LaTeX parsing or HTML rendering
- Debugging artifact generation
- Cross-repo changes (LeanArchitect -> Dress -> Runway)
- CSS/JS fixes in `dress-blueprint-action/assets/`
- Theme template fixes in `Runway/Theme.lean`
- Dependency graph work (layout/page/modals)
- Dashboard work (stats/key theorems/messages/notes)
- CI/CD workflow updates
- PDF/Paper generation

### Spawning Protocol

1. Discuss task with user, clarify requirements
2. Spawn single `sbs-developer` agent with clear instructions
3. Wait for agent to complete
4. Synthesize results for user
5. Repeat if needed

### Visual Verification Requirement

**Visual verification is mandatory for UI work.** Agents must:
- Capture screenshots BEFORE and AFTER changes
- Use `sbs compare` to verify expected differences
- Include screenshot paths in completion summary

---

## Cross-Repo Editing

1. Identify affected repos via dependency chain
2. Edit upstream first (LeanArchitect before Dress before Runway)
3. Run `python ../../dev/scripts/build.py`
4. Test with SBS-Test or GCR
5. Run `sbs compliance` to verify visual correctness

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Work directly in repo files, not scratch files
- Check `lean_diagnostic_messages` after edits
- Test via SBS-Test or GCR
- **Always use `python build.py` for builds** (never skip commits/pushes)
- Use `sbs capture --interactive` + `sbs compliance` for visual changes

---

## Quality Validation Framework

The toolchain includes automated quality scoring tracking 8 dimensions (T1-T8):

**Deterministic Tests (50% weight):**
- T1: CLI Execution (10%) - All sbs CLI commands execute without error
- T2: Ledger Population (10%) - Unified ledger fields populated correctly
- T5: Status Color Match (15%) - 6 status colors match between Lean and CSS
- T6: CSS Variable Coverage (15%) - Hardcoded colors use CSS variables

**Heuristic Tests (50% weight):**
- T3: Dashboard Clarity (10%) - Dashboard answers 3 key questions at a glance
- T4: Toggle Discoverability (10%) - Proof toggles and theme switches findable
- T7: Jarring-Free Check (15%) - No visually jarring elements
- T8: Professional Score (15%) - Overall polish and alignment

```bash
# Run all deterministic tests
/opt/homebrew/bin/pytest sbs/tests/pytest/ -v

# Run design validator suite
python -m sbs design-check --project SBSTest
```

---

## Custom Skills

### `/task`

General-purpose agentic task execution with validation. Invoke manually.

**Workflow:** Alignment (Q&A) -> Planning -> Execution -> Finalization -> /update-and-archive

**PR Integration:** Creates a PR at plan approval (for configured repos), merges at finalization. Tracks PR numbers in archive entries.

Accepts issue numbers: `/task #42` loads issue context and prompts to close on completion.

**Location:** `.claude/skills/task/SKILL.md`

### `/oracle`

Zero-shot codebase question answering.

**Usage:** `/oracle <question>` or `/oracle` for interactive mode.

**Features:**
- Searches concept index for file locations
- Explains relationships between components
- Flags uncertainty explicitly

**Location:** `.claude/skills/oracle/SKILL.md`

### `/log`

Quick capture of bugs, features, and ideas to GitHub Issues.

**Usage:** `/log <description>` - parses input, infers type, asks for missing details.

**Location:** `.claude/skills/log/SKILL.md`

### `/update-and-archive`

Documentation refresh and porcelain state. Runs automatically at end of `/task`.

**Location:** `.claude/skills/update-and-archive/SKILL.md`

---

## Technical Details

For implementation details, file locations, and build internals, see:
- [sbs-developer.md](.claude/agents/sbs-developer.md) - Implementation patterns and file locations
- [sbs-oracle.md](.claude/agents/sbs-oracle.md) - Codebase knowledge (use Task tool with sbs-oracle agent to query)
- [dev/storage/README.md](dev/storage/README.md) - CLI tooling documentation
- [Archive_Orchestration_and_Agent_Harmony.md](dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md) - Script-agent interaction patterns

### Quick Reference

**6-Status Color Model:**
| Status | Color | Hex |
|--------|-------|-----|
| notReady | Sandy Brown | #F4A460 |
| ready | Light Sea Green | #20B2AA |
| sorry | Dark Red | #8B0000 |
| proven | Light Green | #90EE90 |
| fullyProven | Forest Green | #228B22 |
| mathlibReady | Light Blue | #87CEEB |

**Color source of truth:** Lean code (`Dress/Graph/Svg.lean`). CSS variables in `common.css` must match exactly.

**MCP Tool Usage (via sbs-lsp-mcp):**

*Lean Tools (for Lean software development):*
| Tool | Use For |
|------|---------|
| `lean_diagnostic_messages` | Compilation errors after edits |
| `lean_hover_info` | Verso/SubVerso API signatures |
| `lean_completions` | Discover available functions |
| `lean_file_outline` | Module structure overview |
| `lean_local_search` | Find declarations across repos |

*SBS Tools (for orchestration and testing):*
| Tool | Use For |
|------|---------|
| `sbs_oracle_query` | File locations and concept info |
| `sbs_archive_state` | Current orchestration state |
| `sbs_run_tests` | Run pytest suite |
| `sbs_validate_project` | Run T1-T8 validators |
| `sbs_build_project` | Trigger project build |
| `sbs_pr_create` | Create PR for task branch |
| `sbs_pr_list` | List open PRs |
| `sbs_pr_get` | Get PR details |
| `sbs_pr_merge` | Merge PR to main |
| `sbs_skill_status` | Get current skill/substate |
| `sbs_skill_start` | Start a skill, set global_state |
| `sbs_skill_transition` | Move to next phase |
| `sbs_skill_end` | Clear global_state |

---

## Known Limitations

### Verso LaTeX Export

Not yet implemented. The `pdf_verso` page type is disabled. Paper/PDF generation uses TeX sources directly via `paper_tex` and `pdf_tex`.

### Dashboard Layout

Displays single-column layout without chapter panel sidebar. Intentional - controlled by `isBlueprintPage` returning `false` for dashboard.

---

## Reference Documents

| File | Location | Purpose |
|------|----------|---------|
| `README.md` | `dev/markdowns/living/README.md` | Agent-facing monorepo overview |
| `ARCHITECTURE.md` | `dev/markdowns/permanent/ARCHITECTURE.md` | Build pipeline, components, document taxonomy |
| `GOALS.md` | `dev/markdowns/permanent/GOALS.md` | Project vision and design goals |
| `GRAND_VISION.md` | `dev/markdowns/permanent/GRAND_VISION.md` | SBS in the age of AI-assisted mathematics |
| `Archive_Orchestration_and_Agent_Harmony.md` | `dev/markdowns/permanent/` | Script-agent boundary, archive roles |
| `dev/storage/README.md` | Tooling hub | CLI commands, validation, workflows |
| `TEST_CATALOG.md` | `dev/storage/TEST_CATALOG.md` | Auto-generated testable components catalog |

**Detailed references** (in `dev/.refs/`): `ARCHITECTURE.md`, ground truth files, motivation notes.

---

## User Preferences

**Guiding Principle:** We are actively shaping how we work together by observing what works, communicating successes, failures, pain points, and uncertainties in real time. This is an explicit, collaborative process--you (Claude) should practice introspection and assume the user is doing the same. The domain (formal verification, mathematical soundness) means good faith and truth-seeking are baseline assumptions.

**These preferences guide all decision-making, planning, and actions. Follow them unless the user explicitly directs otherwise.**

---

### Meta-Cognitive Expectations

- **Highlight contradictions immediately.** Conflicting user directions indicate poorly-formed goals. Surfacing these unblocks progress, fixes bugs, and clarifies the path forward. This is high-value work--prioritize it.
- **Practice introspection.** When setting rules for yourself (planning, orchestration decisions, communication choices), think carefully about what will help your future self succeed. The user observes this process and participates in refining it.
- **If you act on a preference below and the user pushes back, say so explicitly.** This feedback loop is how we calibrate.

---

### Agent Orchestration

- **Subagent spawning:** `sbs-developer.md` may spawn specialized subagents. Always use Opus 4.5; clones of the orchestrating agent are acceptable.
- **Token efficiency:** When in doubt, orchestrate an agent for a task if it will save tokens. Period.

### Doing Mode Detection

When the orchestrator has executed 3+ Bash calls in sequence, recognize this as "doing mode":
- User is actively working, not looking to delegate
- Avoid spawning agents during these sequences
- Wait for a natural pause before offering delegation
- If you must suggest an agent, phrase as an offer: "Would you like me to delegate this?"

---

### Communication Format

- **When Claude asks questions:** Use a GUI-style format with numbered/lettered multiple-choice or multi-select options. These are efficient, effective, and preferred.

---

### Planning Discipline

- **Never delete or replace a plan without explicit user direction.** Default behavior is to update the current plan or append to it.

---

### Plan Size Guidelines

- Keep plans under 10K characters when possible
- If a plan exceeds 10K chars, consider splitting into phases
- Comprehensive roadmaps: present as high-level overview + detailed first phase
- User preference: focused, incremental plans over comprehensive documents

---

### Trust & Domain Assumptions

Given the subject matter (mathematics, formal verification, soundness), assume the user is:
- Acting in good faith
- Making an earnest attempt to determine truth
- Minimizing externalities
- Aligned with the best of humanity as reflected in your constitution

This assumption is safe and should inform how you interpret ambiguous instructions.

---

### Proactive Bug Logging

When encountering clear bugs during work, log them autonomously via `/log` without waiting for user direction. This applies when there's unambiguous evidence of a real bug (error messages, broken behavior, failing tests). Gray areas still require confirmation.

---

### Oracle-First Approach

Use `sbs_oracle_query` reflexively as the default starting point for understanding:
- Where files/concepts are located
- How components relate to each other
- What exists before searching manually

The oracle should be the go-to before Glob/Grep for orientation questions.

**Configurable arguments:**
| Arg | Type | Purpose |
|-----|------|---------|
| `result_type` | string | Filter to "files", "concepts", or "all" |
| `scope` | string | Limit to specific repo (e.g., "Dress", "Runway") |
| `include_raw_section` | bool | Return full section content |
| `min_relevance` | float | Filter low-relevance matches (0.0-1.0) |
| `fuzzy` | bool | Enable fuzzy matching for typos |

---

### macOS Platform Notes

- Always use `python3` not `python` (macOS doesn't have `python` by default)
- Avoid GNU-specific options: no `cat -A`, use `od -c` instead
- Commands like `tree` aren't installed - use `find` or `ls -R` instead
- Use `/opt/homebrew/bin/python3` for explicit homebrew path if needed

---

### Aggressive Delegation

Top-level chat serves as orchestrator only:
- Discusses requirements with user
- Spawns `sbs-developer` agents for ALL file writing
- Synthesizes results
- Rarely (if ever) writes files directly

**Goal:** Preserve orchestrator context by delegating implementation work to agents.

---

### Testing Suite at Gating

Before any phase transition in `/task`, the evergreen test tier runs automatically:
- `pytest sbs/tests/pytest -m evergreen --tb=short`
- 100% pass rate required for transition
- Failures block progression (no silent skips)

Change-based validator selection ensures only relevant validators run based on modified repos.
