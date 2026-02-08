# Strange Loop Station: Development Guide

AI-assisted development orchestration with recursive self-improvement. SLS provides archive-driven feedback loops, skill state machines, and introspection hierarchies for structured agentic workflows.

> **Note:** MCP tool names use the `sls_` prefix (e.g., `sls_task`, `sls_archive_state`). Lean LSP tools are served by `lean-lsp-mcp`; all SLS orchestration, browser, and Zulip tools are served by `sls-mcp`.

---

## How This Document Works

This guide governs Claude Code sessions in the Strange Loop Station repository. It defines:
- **Orchestration structure:** How the top-level chat and `sbs-developer` agents divide labor
- **User preferences:** Communication, planning, and meta-cognitive expectations
- **SBS project context:** Architecture and build commands for the formalization toolchain that SLS orchestrates

The user and Claude are actively refining this document together. If something here doesn't match how work is actually proceeding, surface it.

---

## Orchestration Model

The top-level chat is the **orchestrator**. It does not implement--it coordinates.

| Top-Level Chat | `sbs-developer` Agent |
|----------------|----------------------|
| Discusses requirements with user | Executes ALL implementation tasks |
| Decomposes and plans work | Has deep architectural knowledge |
| Spawns agents (up to 4 concurrent during /task and /introspect) | Works within defined scope |
| Synthesizes results | Reports outcomes |

**Multiagent Concurrency:**
- `sbs-developer` is the ONLY implementation agent type (writes files, interacts with archival system)
- **Up to 4 concurrent `sbs-developer` agents** are allowed during ALL phases of `/task` (alignment, planning, execution, finalization) and during `/introspect`, when the approved plan or skill definition specifies parallel work
- Files targeted by parallel agents must not overlap
- Multiple read-only exploration agents may run in parallel alongside at all times

### Post-Task Self-Improvement

After every `/task` session completes (success or failure), the orchestrator spawns `sbs-self-improve` in the background. The orchestrator does NOT wait for completion. This ensures every task session triggers at least L0 introspection.

The introspection hierarchy uses geometric 4x decay:
| Level | Trigger | Input |
|-------|---------|-------|
| L0 | Every task session | Session transcript + recent entries |
| L1 | Every 4 sessions | All L0 findings since last L1 |
| L2 | Every 16 sessions | All L1 findings since last L2 |
| L(N) | Every 4^N sessions | All L(N-1) findings since last L(N) |

---

## SLS Purpose & Scope

Strange Loop Station is the orchestration framework that was extracted from the Side-by-Side Blueprint monorepo. It provides:

1. **Archive-driven feedback loops** -- Session extraction, tagging, quality scoring
2. **Skill state machines** -- `/task`, `/log`, `/qa`, `/introspect`, `/converge`, `/update-and-archive`
3. **Introspection hierarchies** -- L0-LN self-improvement with geometric decay
4. **Quality validation** -- T1-T8 deterministic and heuristic test suite
5. **Build orchestration** -- Project builds with artifact generation and visual compliance

SLS still builds and manages SBS formalization projects (SBS-Test, GCR, PNT). The SBS toolchain (Dress, Runway, LeanArchitect, etc.) remains in the SBS monorepo; SLS orchestrates builds against it.

---

## Dual-Repo Architecture

SBS and SLS are now separate repositories. SLS is the **development workstation** that wraps SBS as a submodule.

### Repo Topology

```
SLS-Strange-Loop-Station/          (private, development workstation)
├── SBS/                           (submodule -> e-vergo/Side-By-Side-Blueprint)
│   ├── toolchain/                 (Dress, Runway, SBS-Test, dress-blueprint-action)
│   ├── showcase/                  (GCR, PNT)
│   └── forks/                     (LeanArchitect, subverso, verso)
├── forks/
│   ├── sls-mcp/                   (SLS orchestration MCP server)
│   └── vscode-lean4/              (development tooling)
├── dev/
│   ├── scripts/                   (sbs + sls CLIs, build tooling, tests, oracle)
│   ├── storage/                   (submodule -> sbs-storage)
│   └── markdowns/                 (living + permanent docs)
├── sbs-mcp/                       (SBS build/quality MCP server)
├── .claude/agents/                (sbs-developer, sbs-oracle, sbs-self-improve)
└── CLAUDE.md                      (this file)
```

**SBS repo** (`e-vergo/Side-By-Side-Blueprint`) is **pure Lean** — no Python, no MCP, no AI tooling. It's what the Lean community sees: toolchain submodules, showcase projects, and a clean README. All development infrastructure lives in SLS.

### Submodule Sync Workflow

SBS changes follow a **commit-inside-then-update-parent** pattern:

1. **Make changes** inside `SBS/toolchain/Dress/` (or any SBS submodule-of-submodule)
2. **Commit inside the submodule**: `cd SBS/toolchain/Dress && git add -A && git commit -m "..."`
3. **Update SBS pointer**: `cd SBS && git add toolchain/Dress && git commit -m "chore: update Dress"`
4. **Push SBS**: `cd SBS && git push` (pure Lean changes visible to the community)
5. **Update SLS pointer**: `cd ../.. && git add SBS && git commit -m "chore: update SBS submodule"`
6. **Push SLS**: via `sls archive upload` (triggers full porcelain check)

**Key rule**: SBS commits should be clean, descriptive, and standalone — they're public. SLS commits can reference internal context (issue numbers, session IDs, agent names).

`ensure_porcelain()` in archive upload handles steps 3-6 automatically for dirty submodules.

### Build Tooling Paths

All Python build tooling lives in SLS, not SBS.

| What | Path (from SLS root) | Notes |
|------|---------------------|-------|
| Build orchestrator | `dev/scripts/sbs/build/orchestrator.py` | Main build logic |
| Build entry point | `dev/scripts/build.py` | CLI wrapper |
| Shell scripts | `dev/build-sbs-test.sh`, `dev/build-gcr.sh`, `dev/build-pnt.sh` | One-click builds |
| SBS CLI | `python3 -m sbs` | Build commands (capture, validate, compliance, etc.) |
| SLS CLI | `python3 -m sls` | Orchestration commands (archive, labels, watch, etc.) |
| Lean projects | `SBS/toolchain/SBS-Test/`, `SBS/showcase/GCR/`, etc. | Inside SBS submodule |

**`SBS_ROOT` resolution**: The `SBS_ROOT` environment variable tells all tooling where the SBS repo is. In SLS context, `.mcp.json` sets it to the SBS submodule path. The auto-detect heuristic walks up looking for `CLAUDE.md` + `forks/`, which finds the SLS root — build scripts then locate Lean projects via `SBS_ROOT` or relative paths.

### MCP Server Topology

Three MCP servers provide tools, each with a distinct role:

| Server | Package | Tools | Audience |
|--------|---------|-------|----------|
| `lean-lsp` | `lean-lsp-mcp` | 18 Lean LSP tools | Any Lean project (domain-agnostic) |
| `sbs-mcp` | `sbs-mcp` | 8 SBS build/quality tools | SBS toolchain development |
| `sls-mcp` | `sls-mcp` | 49 SLS orchestration + 5 browser + 3 Zulip | SLS workflow management |

**Tool name conventions:**
- `lean_*` — Lean language server tools (no prefix change)
- `sbs_*` — SBS build tools (build_project, validate_project, etc.)
- `sls_*` — SLS orchestration tools (archive_state, skill_start, issue_log, etc.)
- `browser_*` / `zulip_*` — Integration tools (in sls-mcp)

**MCP prefix in tool calls:**
- `mcp__lean-lsp__lean_goal` (Lean tools)
- `mcp__sbs-mcp__sbs_build_project` (SBS tools)
- `mcp__sls-mcp__sls_archive_state` (SLS tools)

### Agent Context Switching

When a Claude Code session opens, it's in one of two contexts:

| Context | Working Directory | CLAUDE.md | Available CLIs | MCP Servers |
|---------|------------------|-----------|----------------|-------------|
| **SLS** (primary) | `SLS-Strange-Loop-Station/` | Full orchestration instructions (this file) | `sbs` + `sls` | lean-lsp + sbs-mcp + sls-mcp |
| **SBS** (rare, public contributions) | `Side-By-Side-Blueprint/` | None (pure Lean repo) | None | None |

**Almost all work happens in SLS context.** Direct SBS context is only for:
- Accepting external PRs from the Lean community
- Reviewing the public-facing state of the repo
- Testing the SBS repo in isolation (no SLS tooling available)

**Agents always operate in SLS context** — `sbs-developer` agents write files within the SLS working tree (including the `SBS/` submodule). They have access to all MCP tools, both CLIs, and the full archive system.

### Shared Infrastructure: sbs-core

The `sbs-core` Python package (`/Users/eric/GitHub/sbs-core/`) provides shared utilities used by both `sbs` and `sls` CLIs:
- `sbs_core.utils` — `SBS_ROOT`, `REPO_PATHS`, logging, git utilities
- `sbs_core.git_ops` — Git status, sync, PR strategies
- `sbs_core.branch_ops` — Feature branch management
- `sbs_core.timing` — Build phase timing
- `sbs_core.ledger` — `UnifiedLedger`, `BuildMetrics`, metric persistence

Both repos install it via `pip install -e /Users/eric/GitHub/sbs-core`.

---

## Repository Map

### SBS Submodule (at `SBS/`)

| Directory | Purpose |
|-----------|---------|
| `SBS/forks/subverso` | Syntax highlighting (O(1) indexed lookups) |
| `SBS/forks/verso` | Document framework (SBSBlueprint genre) |
| `SBS/forks/LeanArchitect` | `@[blueprint]` attribute (8 metadata + 3 status options) |
| `SBS/toolchain/Dress` | Artifact generation + graph layout + validation |
| `SBS/toolchain/Runway` | Site generator + dashboard + paper/PDF |
| `SBS/toolchain/SBS-Test` | Minimal test project (49 nodes) |
| `SBS/toolchain/dress-blueprint-action` | CI/CD action + CSS/JS assets |
| `SBS/showcase/GCR` | Production example with paper (128 nodes) |
| `SBS/showcase/PNT` | Large-scale integration (591 annotations) |

### SLS-Specific

| Directory | Purpose |
|-----------|---------|
| `forks/sls-mcp` | SLS MCP server (49 SLS + 5 browser + 3 Zulip tools) |
| `forks/vscode-lean4` | Development fork (blueprint infoview panel) |
| `sbs-mcp/` | SBS build/quality MCP server (8 tools) |
| `dev/scripts/` | Python tooling (sbs + sls CLIs, build, tests, oracle) |
| `dev/storage/` | Build metrics, screenshots, session archives |
| `dev/markdowns/` | Living and permanent documentation |
| `.claude/agents/` | Agent definitions |

### SBS Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

---

## SLS Repository Structure

| Directory | Purpose |
|-----------|---------|
| `dev/scripts/sbs/archive/` | Archive upload, entry models, session extraction, tagging, gates, iCloud sync |
| `dev/scripts/sbs/labels/` | GitHub label synchronization |
| `dev/scripts/sbs/readme/` | README freshness checking |
| `dev/scripts/sbs/test_catalog/` | Component catalog generation |
| `dev/scripts/sbs/commands/` | CLI commands (watch, dev, clean) |
| `dev/scripts/sbs/core/` | Shared utilities, git ops, branch ops, ledger, timing |
| `dev/scripts/sbs/oracle/` | Oracle concept index compilation and extraction |
| `dev/scripts/sbs/build/` | Build phases, orchestrator, caching, config, versions |
| `dev/scripts/sbs/tests/` | T1-T8 validators, visual compliance, pytest suite |
| `dev/storage/` | Build metrics, screenshots, session archives, unified ledger |
| `dev/markdowns/` | Living and permanent documentation |
| `dev/skills/archive/` | Archived SKILL.md prompt definitions |
| `.claude/agents/` | Agent definitions (sbs-developer, sbs-oracle, sbs-self-improve) |
| `.claude/plans/` | Task plans |

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
cd /Users/eric/GitHub/SLS-Strange-Loop-Station/SBS/toolchain/SBS-Test
python ../../../dev/scripts/build.py
```

Options: `--dry-run`, `--skip-cache`, `--verbose`, `--capture`, `--skip-lake`

**Always Build:** By default, all Lake build phases run on every invocation to prevent stale `.olean` artifacts. Use `--skip-lake` to explicitly skip Lake phases when you know artifacts are fresh.

**Required:** `runway.json` must include `assetsDir` pointing to CSS/JS assets.

---

## Visual Testing

**Screenshot capture is the FIRST reflex for any visual/CSS/layout issue.**

```bash
cd /Users/eric/GitHub/SLS-Strange-Loop-Station/dev/scripts

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

### Cleaning Build Artifacts

```bash
sbs clean --project SBSTest --check   # Show what would be cleaned
sbs clean --project SBSTest           # Clean project + toolchain deps
sbs clean --all --force               # Clean everything
sbs clean --all --full --force        # Also remove .lake/packages/
```

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
- Archive/orchestration infrastructure changes
- Validator and test suite modifications

### Spawning Protocol

1. Discuss task with user, clarify requirements
2. Spawn single `sbs-developer` agent with clear instructions
3. Wait for agent to complete
4. Synthesize results for user
5. Repeat if needed

**Parallel spawning:** During `/task` (all phases) and `/introspect`, up to 4 agents may be spawned in a single message with multiple Task tool calls, per the approved plan's wave structure. Collision avoidance is the plan's responsibility -- parallel agents must target non-overlapping files/repos.

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

### Submodule Commit Workflow

Changes to submodule repos (verso, subverso, LeanArchitect, dress-blueprint-action, etc.) follow a two-step commit pattern:

1. **Commit inside the submodule:** Navigate to the submodule directory, stage, commit, and push changes
2. **Update parent repo:** The parent repo detects the new submodule commit (shows as `modified: <path> (new commits)`) and needs its own commit to update the pointer

**Automated handling:** `sbs archive upload` runs `ensure_porcelain()` which automatically detects dirty submodules, commits them, then commits the parent repo last to capture all pointer updates.

**Manual workflow:**
```bash
# 1. Make changes in submodule
cd toolchain/dress-blueprint-action
git add -A && git commit -m "fix: description" && git push

# 2. Update parent repo pointer
cd ../..
git add toolchain/dress-blueprint-action
git commit -m "chore: update dress-blueprint-action submodule" && git push
```

This is inherent to git submodule architecture. The `ensure_porcelain()` function handles this automatically during archive uploads by committing submodules first, then the main repo.

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Work directly in repo files, not scratch files
- Check `lean_diagnostic_messages` after edits
- Test via SBS-Test or GCR
- **Always use `python build.py` for builds** (never skip commits/pushes)
- Use `sbs capture --interactive` + `sbs compliance` for visual changes

### Git Push Restriction (Archival-First Design)

Direct `git push` from Claude Code Bash is denied by user-configured hooks -- this is intentional. All pushes must flow through archival-aware pathways:

- **`sbs archive upload`** (preferred) -- calls `ensure_porcelain()` via Python subprocess, which commits and pushes all dirty repos. Bypasses the hook because it runs `git push` through `subprocess.run()`, not the Claude Code shell.
- **Build scripts** (`dev/build-*.sh`, `build.py`) -- run git operations via subprocess internally.
- **New branches without upstream tracking** -- `ensure_porcelain()` does not handle `--set-upstream`. For initial push of a new branch, use: `python3 -c "import subprocess; subprocess.run(['git', 'push', '--set-upstream', 'origin', '<branch-name>'], check=True)"`

This design ensures every push is accompanied by an archive entry, porcelain state is checked holistically, and no "orphan pushes" bypass tracking.

### 6-Status Color Model

| Status | Color | Hex |
|--------|-------|-----|
| notReady | Sandy Brown | #F4A460 |
| ready | Light Sea Green | #20B2AA |
| sorry | Dark Red | #8B0000 |
| proven | Light Green | #90EE90 |
| fullyProven | Forest Green | #228B22 |
| mathlibReady | Light Blue | #87CEEB |

**Color source of truth:** Lean code (`Dress/Graph/Svg.lean`). CSS variables in `common.css` must match exactly.

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

## Skill MCP Tools

Skills are implemented as MCP tools in `sls-mcp`. Invoke via slash commands or direct MCP tool calls.

### `sls_task` (`/task`)

General-purpose agentic task execution with validation.

**Workflow:** Alignment (Q&A) -> Planning -> Execution -> Finalization -> update-and-archive

**PR Integration:** Creates a PR at plan approval (for configured repos), merges at finalization. Tracks PR numbers in archive entries.

**Arguments:**
- `issue_refs`: Optional list of GitHub issue numbers to load context from
- `description`: Optional task description

### `sls_log` (`/log`)

Quick capture of bugs, features, and ideas to GitHub Issues.

**Arguments:**
- `description`: Issue description (parsed for type/area inference)
- `label`: Optional explicit type label (bug, feature, idea)
- `area`: Optional explicit area label

### `sls_qa` (`/qa`)

Live interactive QA against a running SBS blueprint site. Browser-driven visual and interactive verification.

**Arguments:**
- `project`: Project name (SBSTest, GCR, PNT)
- `pages`: Optional list of specific pages to check

**Workflow:** Setup (ensure server, navigate) -> Review (per-page checks) -> Report (structured findings)

### `sls_update_and_archive` (`/update-and-archive`)

Documentation refresh and porcelain state. Runs automatically at end of `/task`.

**Workflow:** Retrospective -> README wave -> Oracle regen -> Porcelain -> Archive upload

### `sls_introspect` (`/introspect`)

Introspection and self-improvement across hierarchy levels.

**Arguments:**
- `level`: Hierarchy level (2 for L2 self-improvement, 3+ for meta-analysis)
- `dry_run`: If true, discovery only without issue creation

**Workflow (L2):** Discovery -> Selection -> Dialogue -> Logging -> Archive
**Workflow (L3+):** Ingestion -> Synthesis -> Archive

### `sls_converge` (`/converge`)

Autonomous QA convergence loop with in-loop introspection.

**Arguments:**
- `project`: Project name (SBSTest, GCR, PNT)
- `max_iterations`: Maximum fix iterations (default: 3)

**Workflow:** Setup -> [Eval -> Fix -> Introspect -> Rebuild]xN -> Report -> L3

### `sls_divination`

Forecasting tool for predicting test outcomes and system behavior.

**Arguments:**
- `question`: Natural language question about expected outcomes
- `context`: Optional additional context

**Archived SKILL.md files:** Original prompt-based skill definitions preserved at `dev/skills/archive/`

### `sls_self_improve`

Computes introspection level and assembles context for the sbs-self-improve background agent.

**Arguments:**
- `multiplier`: Geometric decay multiplier (default: 4). Level N triggers every 4^N sessions.

**Returns:** `SelfImproveContext` with computed level, session transcript path, entries since last level, lower-level findings, open issues, and improvement captures.

**Usage:** Called by the `sbs-self-improve` agent at the start of each run. Not typically called directly by the orchestrator.

---

## Technical Details

For implementation details, file locations, and build internals, see:
- [sbs-developer.md](.claude/agents/sbs-developer.md) - Implementation patterns and file locations
- [sbs-oracle.md](.claude/agents/sbs-oracle.md) - Oracle concept index data (parsed by `ask_oracle` MCP tool via DuckDB)
- [dev/storage/README.md](dev/storage/README.md) - CLI tooling documentation
- [Archive_Orchestration_and_Agent_Harmony.md](dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md) - Script-agent interaction patterns

### MCP Tool Usage

*Lean Tools (via lean-lsp-mcp):*
| Tool | Use For |
|------|---------|
| `lean_diagnostic_messages` | Compilation errors after edits |
| `lean_hover_info` | Verso/SubVerso API signatures |
| `lean_completions` | Discover available functions |
| `lean_file_outline` | Module structure overview |
| `lean_local_search` | Find declarations across repos |

*SLS Tools (via sls-mcp, for orchestration and testing):*
| Tool | Use For |
|------|---------|
| `ask_oracle` | Unified query: concept index + archive + quality metrics |
| `sls_archive_state` | Current orchestration state |
| `sls_run_tests` | Run pytest suite |
| `sls_validate_project` | Run T1-T8 validators |
| `sls_build_project` | Trigger project build |
| `sls_pr_create` | Create PR for task branch |
| `sls_pr_list` | List open PRs |
| `sls_pr_get` | Get PR details |
| `sls_pr_merge` | Merge PR to main |
| `sls_skill_status` | Get current skill/substate |
| `sls_skill_start` | Start a skill, set global_state |
| `sls_skill_transition` | Move to next phase |
| `sls_skill_end` | Clear global_state |
| `sls_skill_fail` | Record skill failure and release global_state |
| `sls_skill_handoff` | Atomic skill-to-skill transition |
| `sls_issue_summary` | Aggregate stats for open issues |
| `sls_issue_log` | Agent-optimized issue logging with auto-populated archive context |
| `sls_question_analysis` | Extract AskUserQuestion interactions from sessions |
| `sls_question_stats` | Aggregate question usage statistics |
| `sls_inspect_project` | Prepare context for visual QA |
| `browser_navigate` | Navigate to URL with persistent active page |
| `browser_click` | Click element on active page |
| `browser_screenshot` | Capture screenshot of active page |
| `browser_evaluate` | Run JavaScript on active page |
| `browser_get_elements` | Query DOM elements on active page |
| `sls_successful_sessions` | Mine successful session patterns |
| `sls_comparative_analysis` | Compare session characteristics |
| `sls_system_health` | System health metrics |
| `sls_user_patterns` | User interaction patterns |
| `sls_self_improve` | Get introspection context for background self-improve agent |

*VSCode Tools (via vscode and vscode-mcp):*
| Tool | Use For |
|------|---------|
| `get_diagnostics` | LSP errors/warnings from VSCode |
| `get_symbol_lsp_info` | Symbol type info + hover data |
| `get_references` | Find all references to a symbol |
| `rename_symbol` | Rename across files via LSP |
| `execute_command` | Run VSCode commands programmatically |
| `open_files` | Open files in VSCode editor |
| `health_check` | Verify VSCode MCP connection |

**When to use VSCode MCP tools vs lean-lsp tools:**
- Use VSCode MCP for real-time LSP diagnostics, symbol info, and refactoring
- Use lean-lsp Lean tools for Lean-specific operations (goal state, hover info, completions)
- VSCode MCP tools require the VSCode MCP bridge extension to be running

*Skill Tools (invoke via slash commands or MCP):*
| Tool | Use For |
|------|---------|
| `sls_task` | General-purpose task execution with validation |
| `sls_log` | Quick capture of issues/ideas to GitHub |
| `sls_qa` | Live interactive QA against blueprint site |
| `sls_introspect` | Self-improvement across hierarchy levels |
| `sls_converge` | Autonomous QA convergence loop |
| `sls_update_and_archive` | Documentation refresh and porcelain state |
| `sls_divination` | Forecasting test outcomes and system behavior |

---

## Known Limitations

### Verso Document Generation

Not yet implemented. All Verso page types (`paper_verso`, `blueprint_verso`, `pdf_verso`) have been removed from active surfaces (sidebar, compliance, validation). Lean infrastructure is preserved for future use. Paper/PDF generation uses TeX sources directly via `paper_tex` and `pdf_tex`.

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
| `SBS_SLS_SEPARATION.md` | `dev/markdowns/permanent/SBS_SLS_SEPARATION.md` | Separation architecture and migration plan |
| `SLS_PLANNING.md` | `dev/markdowns/permanent/SLS_PLANNING.md` | SLS-specific planning and roadmap |
| `SLS_EXTENSION.md` | `dev/markdowns/permanent/SLS_EXTENSION.md` | SLS extension points and APIs |
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
- **Block-wait mandatory:** NEVER use `run_in_background=true` when spawning `sbs-developer` agents. Always block-wait for agent completion. Background execution causes lost synchronization and dead time. This was learned from Crush 2 session (#253-#254).
- **Token efficiency:** When in doubt, orchestrate an agent for a task if it will save tokens. Period.

### Doing Mode Detection

Recognize "doing mode" when any of these signals are present:
- Orchestrator has executed 3+ Bash calls in sequence
- User is making direct file edits (VSCode selections, IDE interactions between messages)
- User rejected a previous agent spawn offer in this session
- User is making changes between messages (editing files outside of Claude)

When doing mode is detected:
- Do not spawn agents -- the user is actively working
- Wait for a natural pause before offering delegation
- If you must suggest an agent, phrase as an offer: "Would you like me to delegate this?"

**Before spawning any agent during execution phase**, explicitly check for doing mode signals. This check is mandatory -- not a suggestion.

---

### Communication Format

- **When Claude asks questions:** Use a GUI-style format with numbered/lettered multiple-choice or multi-select options. These are efficient, effective, and preferred.

---

### Structured User Interactions

#### AskUserQuestion Best Practices

**Use AskUserQuestion when:**
- Decision has 2-4 clear options
- User preference will inform future similar decisions
- Consistency is important (e.g., scope, approach, gate selection)
- Binary confirmation needed

**Use freeform when:**
- Response requires creativity/nuance
- Options aren't enumerable
- User is describing something new

**multiSelect guidance:**
- Use for "select all that apply" questions
- Phrase appropriately ("Which X do you want?" not "What X do you want?")
- Limit to related options within same category

#### Standard Header Taxonomy

Use these headers for common question types to enable preference aggregation:

| Header | Use For |
|--------|---------|
| `Confirm` | Binary yes/no, approval |
| `Scope` | Task/feature boundaries |
| `Approach` | Strategy selection |
| `Select` | Priority/choice from list |
| `Finalize` | Completion confirmation |
| `Validation` | Gates, tests, criteria |
| `Next Step` | What happens next |
| `Layout` | Visual arrangement |
| `Format` | Output style |
| `Architecture` | Design decisions |

Avoid ad-hoc headers like "Scope check" or "Task scope". Use the standard header "Scope" to enable preference aggregation.

#### Skill Preamble Injection Pattern

When starting a skill that benefits from preference context:
1. Query `sls_question_stats(skill="<skill>")` for top user selections
2. Query `sls_question_analysis(skill="<skill>", limit=5)` for recent patterns
3. Inject insights into agent prompts or pre-populate likely options

Example: For `/task`, if user historically selects "All gates" 80% of the time, pre-check that option.

#### AskUserQuestion Effectiveness Patterns

Based on observed session patterns (715 questions across 140 sessions):

- **Most effective headers:** `Scope` (60 uses), `Approach` (48), `Confirm` (39) -- these lead to fastest resolution and clearest user answers
- **Optimal option count:** 2-3 options. 4 options only when choices are genuinely distinct.
- **Binary decisions work best** with concrete implications described per option -- `Confirm` questions with "Yes, proceed" are the most-selected single option (12 times)
- **Freeform overrides signal option mismatch:** When users bypass options to type freeform answers (observed in `Architecture` and `Scope` questions), it indicates the options didn't match their mental model. Prefer freeform in ambiguous situations.
- **Multi-select is underused:** Only 10.8% of questions use multi-select (77 of 715). When applicable, it reduces follow-up questions.
- **65% of sessions have zero questions** -- most work proceeds without user interaction. Questions should be reserved for genuine decision points, not information gathering.

---

### Planning Discipline

- **Never delete or replace a plan without explicit user direction.** Default behavior is to update the current plan or append to it.

### Explore-Before-Decompose Pattern

When a `/task` involves architectural planning or multi-feature scoping (not direct implementation):

1. **Explore first:** Spawn an Explore agent to survey relevant infrastructure before decomposing
2. **The agent reports:** What exists, what's missing, key files, risk level
3. **Orchestrator synthesizes:** Use exploration results to ground the decomposition in reality
4. **User validates:** Present findings alongside proposed decomposition

This pattern was validated during Epic #224 scoping, where deep exploration before decomposition produced plans the user called "well researched and thought out." Ad-hoc exploration that happens to work should be standardized.

**When to apply:** Task description involves words like "plan", "scope", "design", "architect", "restructure", or when the task spans 3+ repos.
**When to skip:** Task is a focused bug fix, single-file change, or the user gave very specific instructions.

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

When encountering clear bugs during work, log them autonomously via `sls_issue_log` MCP tool without waiting for user direction. This applies when there's unambiguous evidence of a real bug (error messages, broken behavior, failing tests). Gray areas still require confirmation. Prefer `sls_issue_log` over `/log` for autonomous logging -- it auto-populates archive context and requires zero user interaction.

---

### Improvement Opportunity Shorthand

Users may type `IO` or `IO(message)` to flag improvement opportunities:

- **`IO`** -- Infer the improvement observation from recent conversation context. Summarize the key insight in 1-2 sentences, then call `sls_improvement_capture` with the inferred observation.
- **`IO(message)`** -- Use the provided message directly as the observation. Call `sls_improvement_capture(observation="<message>")`.

In both cases, infer the most appropriate category from context: `process`, `interaction`, `workflow`, `tooling`, or `other`. Do not ask the user to confirm -- capture immediately and report what was logged.

---

### Multiagent Behavior Definition

**What constitutes "multiagent behavior":** Multiple `sbs-developer` agents running concurrently, where each agent writes files and/or interacts with the archival system. Read-only exploration agents do not count as multiagent behavior.

**When multiagent is allowed:**
- All `/task` phases: alignment, planning, execution, finalization
- `/introspect` skill: discovery and logging phases (L2)
- Up to 4 concurrent agents per wave
- Non-overlapping file targets required

**When multiagent is NOT allowed:**
- `/log` (atomic, single-agent operation)
- `/update-and-archive` (sequential by design)
- Outside of any active skill (idle state)

---

### Oracle-First Approach

Use `ask_oracle` reflexively as the default starting point for understanding:
- Where files/concepts are located
- How components relate to each other
- What exists before searching manually
- Archive history and quality metrics for a topic

The oracle should be the go-to before Glob/Grep for orientation questions.

**Configurable arguments:**
| Arg | Type | Purpose |
|-----|------|---------|
| `query` | string | Natural language query to search |
| `max_results` | int | Maximum results to return (default: 10) |
| `min_relevance` | float | Filter low-relevance matches (0.0-1.0) |
| `fuzzy` | bool | Enable fuzzy matching for typos |
| `include_archive` | bool | Include archive entry matches |
| `include_issues` | bool | Include GitHub issue matches |
| `include_quality` | bool | Include quality metric matches |

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
