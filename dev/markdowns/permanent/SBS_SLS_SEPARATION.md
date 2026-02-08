# SBS/SLS Separation Architecture

This document defines the architecture for separating the Side-by-Side Blueprint (SBS) formalization toolchain from the Strange Loop Station (SLS) orchestration framework.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Map](#current-state-map)
3. [MCP Tool Split Matrix](#mcp-tool-split-matrix)
4. [Python Scripts Split](#python-scripts-split)
5. [Proposed Repository Structure](#proposed-repository-structure)
6. [Migration Strategy](#migration-strategy)
7. [Dependency Analysis](#dependency-analysis)
8. [Open Questions](#open-questions)

---

## Executive Summary

The Side-by-Side Blueprint project started as a pure Lean formalization documentation toolchain. Over time, the orchestration machinery built to develop that toolchain -- archive systems, skill state machines, introspection hierarchies, quality validation loops -- grew into its own framework: Strange Loop Station.

These two concerns are now entangled in a single monorepo. They have different scopes, different audiences, and different evolutionary pressures:

| Dimension | SBS | SLS |
|-----------|-----|-----|
| **Purpose** | Display formal Lean proofs alongside LaTeX theorem statements | AI-assisted development orchestration with recursive self-improvement |
| **End users** | Mathematicians writing formalization projects | Developers using Claude Code for structured agentic workflows |
| **Core deliverable** | Generated documentation sites (HTML, PDF) with dependency graphs | Archive-driven feedback loops, skill state machines, introspection hierarchies |
| **Stability profile** | Converging toward 1.0 release | Actively evolving, experimental |
| **Dependencies** | Lean 4, mathlib, SubVerso, Verso | Claude Code, GitHub API, DuckDB, Playwright |

Separation enables SBS to ship as a clean, documented tool for the Lean community without carrying orchestration machinery. It enables SLS to evolve as a general-purpose framework without being coupled to Lean-specific build details.

---

## Current State Map

### SBS (Pure Formalization Toolchain)

| Directory | Purpose |
|-----------|---------|
| `toolchain/Dress/` | Artifact generation, graph layout (Sugiyama), validation |
| `toolchain/Runway/` | Site generator, dashboard, paper/PDF, LaTeX parser |
| `toolchain/SBS-Test/` | Minimal test project (33 nodes: 32 Lean + 1 LaTeX) |
| `toolchain/dress-blueprint-action/` | GitHub Action (432 lines, 14 steps) + CSS/JS assets (3,805 lines) |
| `showcase/General_Crystallographic_Restriction/` | Production example with paper (57 nodes) |
| `showcase/PrimeNumberTheoremAnd/` | Large-scale integration (591 annotations) |
| `showcase/ReductiveGroups/` | Planned showcase project |
| `forks/subverso/` | Syntax highlighting (O(1) indexed lookups via InfoTable) |
| `forks/verso/` | Document framework (SBSBlueprint/VersoPaper genres) |
| `forks/LeanArchitect/` | `@[blueprint]` attribute (8 metadata + 3 status options) |

### SLS (Orchestration/Meta-Layer)

| Directory | Purpose |
|-----------|---------|
| `dev/scripts/sbs/archive/` | Archive upload, entry models, session extraction, tagging, gates, iCloud sync |
| `dev/scripts/sbs/labels/` | GitHub label synchronization |
| `dev/scripts/sbs/readme/` | README freshness checking |
| `dev/scripts/sbs/test_catalog/` | Component catalog generation |
| `dev/scripts/sbs/commands/` | CLI commands (watch, dev) |
| `dev/storage/` | Build metrics, screenshots, session archives, unified ledger |
| `dev/storage/archive/` | Session archive data |
| `dev/storage/archive_data/` | Extracted Claude Code session data |
| `dev/storage/tagging/` | Tagging rules and configuration |
| `dev/markdowns/` | Living and permanent documentation |
| `.claude/` | Agent definitions (sbs-developer, sbs-oracle, sbs-self-improve) |
| `CLAUDE.md` | Project orchestration instructions |

### Hybrid (Requires Splitting)

| Component | SBS Parts | SLS Parts |
|-----------|-----------|-----------|
| `forks/sbs-lsp-mcp/` | 18 Lean LSP tools, ~10 build/quality tools | ~33 orchestration/analysis tools, 8 skill tools, 5 browser tools, 3 Zulip tools, 1 improvement capture tool |
| `forks/vscode-lean4/` | Blueprint infoview panel | Development-time only tooling |
| `dev/scripts/sbs/build/` | Build phases, orchestrator, caching, config, versions | Archive hooks in orchestrator |
| `dev/scripts/sbs/tests/` | T1-T8 validators, visual compliance framework | Orchestration integration tests (archive invariants, gates, tagger, self-improve) |
| `dev/scripts/sbs/core/` | Shared utilities, timing | Git ops for archive, branch ops, ledger |
| `dev/scripts/sbs/oracle/` | Concept index compilation and extraction | Archive query integration via DuckDB |
| `dev/scripts/build.py` | Build orchestration | Commit/push hooks, archive triggers |

---

## MCP Tool Split Matrix

Total tools in `sbs-lsp-mcp`: **75** (18 Lean + 41 sbs_tools + 8 skill_tools + 5 browser + 3 Zulip)

### Category A: Lean LSP (18 tools) -- Standard `lean-lsp-mcp` package

These tools are domain-agnostic Lean language server wrappers with no SBS or SLS dependencies.

| Tool | Source File | Purpose |
|------|------------|---------|
| `lean_build` | `server.py` | Trigger Lake build |
| `lean_file_contents` | `server.py` | Read Lean file content |
| `lean_file_outline` | `server.py` | Module structure overview |
| `lean_diagnostic_messages` | `server.py` | Compilation errors/warnings |
| `lean_goal` | `server.py` | Proof state at cursor |
| `lean_term_goal` | `server.py` | Expected term type at cursor |
| `lean_hover_info` | `server.py` | Type signature and docs |
| `lean_completions` | `server.py` | Autocomplete suggestions |
| `lean_declaration_file` | `server.py` | Find declaration source file |
| `lean_multi_attempt` | `server.py` | Try multiple tactics |
| `lean_run_code` | `server.py` | Execute Lean code snippet |
| `lean_local_search` | `server.py` | Find declarations across project |
| `lean_leansearch` | `server.py` | Natural language theorem search |
| `lean_loogle` | `server.py` | Type-based theorem search |
| `lean_leanfinder` | `server.py` | Alternative theorem finder |
| `lean_state_search` | `server.py` | Search by proof state |
| `lean_hammer_premise` | `server.py` | Premise selection for hammer |
| `lean_profile_proof` | `server.py` | Profile proof performance |

### Category B: SBS Build & Quality (~10 tools) -- SBS repo or shared package

These tools operate on SBS build artifacts and project structure. No archive or orchestration dependencies.

| Tool | Source File | Purpose |
|------|------------|---------|
| `sbs_build_project` | `sbs_tools.py` | Trigger full project build |
| `sbs_validate_project` | `sbs_tools.py` | Run T1-T8 validators on project |
| `sbs_serve_project` | `sbs_tools.py` | Start/stop/check dev server |
| `sbs_inspect_project` | `sbs_tools.py` | Prepare context for visual QA |
| `sbs_run_tests` | `sbs_tools.py` | Run pytest suite (shared -- tests both SBS and SLS) |
| `sbs_last_screenshot` | `sbs_tools.py` | Get most recent screenshot for page |
| `sbs_visual_history` | `sbs_tools.py` | View screenshot history across entries |
| `ask_oracle` | `sbs_tools.py` | Unified query: concept index + archive + quality metrics (shared) |

### Category C: SLS Orchestration (~41 tools) -- `sls-mcp`

These tools manage archive state, skill lifecycle, GitHub issues/PRs, and session analysis.

**Archive & Context (4 tools):**

| Tool | Source File | Purpose |
|------|------------|---------|
| `sbs_archive_state` | `sbs_tools.py` | Current global state and skill substate |
| `sbs_epoch_summary` | `sbs_tools.py` | Aggregated epoch data |
| `sbs_context` | `sbs_tools.py` | Build context for agent spawn |
| `sbs_search_entries` | `sbs_tools.py` | Search archive entries by tag/project/trigger |

**Skills (8 tools):**

| Tool | Source File | Purpose |
|------|------------|---------|
| `sbs_task` | `skill_tools.py` | General-purpose task execution with validation |
| `sbs_log` | `skill_tools.py` | Quick issue/idea capture to GitHub |
| `sbs_qa` | `skill_tools.py` | Live interactive QA against blueprint site |
| `sbs_introspect` | `skill_tools.py` | Self-improvement across hierarchy levels |
| `sbs_self_improve` | `skill_tools.py` | Compute introspection level and assemble context |
| `sbs_converge` | `skill_tools.py` | Autonomous QA convergence loop |
| `sbs_update_and_archive` | `skill_tools.py` | Documentation refresh and porcelain state |
| `sbs_divination` | `skill_tools.py` | Forecasting test outcomes and system behavior |

**Skill State Machine (6 tools):**

| Tool | Source File | Purpose |
|------|------------|---------|
| `sbs_skill_status` | `sbs_tools.py` | Get current skill/substate |
| `sbs_skill_start` | `sbs_tools.py` | Start skill, set global_state |
| `sbs_skill_transition` | `sbs_tools.py` | Move to next phase |
| `sbs_skill_end` | `sbs_tools.py` | Clear global_state |
| `sbs_skill_fail` | `sbs_tools.py` | Record failure and release global_state |
| `sbs_skill_handoff` | `sbs_tools.py` | Atomic skill-to-skill transition |

**GitHub Integration (7 tools):**

| Tool | Source File | Purpose |
|------|------------|---------|
| `sbs_issue_create` | `sbs_tools.py` | Create GitHub issue |
| `sbs_issue_log` | `sbs_tools.py` | Agent-optimized issue logging with auto-populated context |
| `sbs_issue_list` | `sbs_tools.py` | List issues with filters |
| `sbs_issue_get` | `sbs_tools.py` | Get issue details |
| `sbs_issue_close` | `sbs_tools.py` | Close issue |
| `sbs_issue_summary` | `sbs_tools.py` | Aggregate stats for open issues |
| `sbs_pr_create` | `sbs_tools.py` | Create pull request |
| `sbs_pr_list` | `sbs_tools.py` | List open PRs |
| `sbs_pr_get` | `sbs_tools.py` | Get PR details |
| `sbs_pr_merge` | `sbs_tools.py` | Merge PR to main |

**Session Analysis (14 tools):**

| Tool | Source File | Purpose |
|------|------------|---------|
| `sbs_analysis_summary` | `sbs_tools.py` | Aggregated analysis metrics |
| `sbs_entries_since_self_improve` | `sbs_tools.py` | Entries since last self-improve |
| `sbs_successful_sessions` | `sbs_tools.py` | Mine successful session patterns |
| `sbs_comparative_analysis` | `sbs_tools.py` | Compare session characteristics |
| `sbs_system_health` | `sbs_tools.py` | System health metrics |
| `sbs_user_patterns` | `sbs_tools.py` | User interaction patterns |
| `sbs_skill_stats` | `sbs_tools.py` | Per-skill usage statistics |
| `sbs_phase_transition_health` | `sbs_tools.py` | Phase transition success rates |
| `sbs_interruption_analysis` | `sbs_tools.py` | Session interruption patterns |
| `sbs_gate_failures` | `sbs_tools.py` | Gate validation failure analysis |
| `sbs_tag_effectiveness` | `sbs_tools.py` | Tag coverage and effectiveness |
| `sbs_question_analysis` | `sbs_tools.py` | AskUserQuestion interaction extraction |
| `sbs_question_stats` | `sbs_tools.py` | Aggregate question usage statistics |
| `sbs_improvement_capture` | `sbs_tools.py` | Capture improvement observations |

### Category D: Browser & Zulip (8 tools) -- `sls-mcp`

These tools provide browser automation and Zulip integration for QA and communication.

**Browser (5 tools):**

| Tool | Source File | Purpose |
|------|------------|---------|
| `browser_navigate` | `browser_tools.py` | Navigate to URL with persistent active page |
| `browser_click` | `browser_tools.py` | Click element on active page |
| `browser_screenshot` | `browser_tools.py` | Capture screenshot of active page |
| `browser_evaluate` | `browser_tools.py` | Run JavaScript on active page |
| `browser_get_elements` | `browser_tools.py` | Query DOM elements on active page |

**Zulip (3 tools):**

| Tool | Source File | Purpose |
|------|------------|---------|
| `zulip_search` | `zulip_tools.py` | Search Zulip messages |
| `zulip_fetch_thread` | `zulip_tools.py` | Fetch full thread |
| `zulip_screenshot` | `zulip_tools.py` | Capture Zulip page screenshot |

### Tool Count Summary

| Category | Count | Destination |
|----------|-------|-------------|
| A: Lean LSP | 18 | `lean-lsp-mcp` (standalone) |
| B: SBS Build & Quality | 8 | SBS repo or shared package |
| C: SLS Orchestration | 41 | `sls-mcp` |
| D: Browser & Zulip | 8 | `sls-mcp` |
| **Total** | **75** | |

---

## Python Scripts Split

### SBS Build Helpers

| Directory/File | Contents |
|----------------|----------|
| `dev/scripts/sbs/build/orchestrator.py` | Build orchestration (48K), phase sequencing |
| `dev/scripts/sbs/build/phases.py` | Individual build phases (10K) |
| `dev/scripts/sbs/build/caching.py` | Build cache management (6K) |
| `dev/scripts/sbs/build/config.py` | Project configuration (3K) |
| `dev/scripts/sbs/build/versions.py` | Version detection and management (6K) |
| `dev/scripts/sbs/build/compliance.py` | Compliance integration (2K) |
| `dev/scripts/sbs/build/inspect.py` | Project inspection (9K) |
| `dev/scripts/sbs/tests/validators/` | T1-T8 quality validators (12 files) |
| `dev/scripts/sbs/tests/compliance/` | Visual compliance framework (7 files) |
| `dev/scripts/sbs/tests/pytest/mvp/` | MVP test suite |
| `dev/scripts/sbs/tests/pytest/oracle/` | Oracle test suite |
| `dev/scripts/sbs/tests/pytest/test_cli.py` | CLI execution tests |
| `dev/scripts/sbs/tests/pytest/test_compliance_mapping.py` | Compliance mapping tests |
| `dev/scripts/sbs/tests/pytest/test_incremental_artifacts.py` | Incremental build tests |
| `dev/scripts/sbs/oracle/compiler.py` | Concept index compilation (8K) |
| `dev/scripts/sbs/oracle/extractors.py` | Content extraction (12K) |
| `dev/scripts/sbs/oracle/templates.py` | Oracle output templates (5K) |

### SLS Orchestration

| Directory/File | Contents |
|----------------|----------|
| `dev/scripts/sbs/archive/upload.py` | Archive upload logic (25K) |
| `dev/scripts/sbs/archive/extractor.py` | ~/.claude session extraction (28K) |
| `dev/scripts/sbs/archive/entry.py` | Archive entry models (12K) |
| `dev/scripts/sbs/archive/tagger.py` | Auto-tagging engine (16K) |
| `dev/scripts/sbs/archive/gates.py` | Phase transition gates (8K) |
| `dev/scripts/sbs/archive/session_data.py` | Session data models (10K) |
| `dev/scripts/sbs/archive/chat_archive.py` | Chat archive management (9K) |
| `dev/scripts/sbs/archive/icloud_sync.py` | iCloud sync (12K) |
| `dev/scripts/sbs/archive/cmd.py` | Archive CLI commands (10K) |
| `dev/scripts/sbs/archive/retroactive.py` | Retroactive tagging (10K) |
| `dev/scripts/sbs/archive/visualizations.py` | Archive visualizations (11K) |
| `dev/scripts/sbs/labels/` | GitHub label sync (2 files, 14K) |
| `dev/scripts/sbs/readme/` | README freshness checking (2 files, 5K) |
| `dev/scripts/sbs/test_catalog/` | Component catalog generation (2 files, 16K) |
| `dev/scripts/sbs/commands/watch.py` | File watch command (20K) |
| `dev/scripts/sbs/commands/dev.py` | Dev command (17K) |
| `dev/scripts/sbs/tests/pytest/test_archive_invariants.py` | Archive invariant tests (31K) |
| `dev/scripts/sbs/tests/pytest/test_gates.py` | Gate tests (19K) |
| `dev/scripts/sbs/tests/pytest/test_self_improve.py` | Self-improve tests (54K) |
| `dev/scripts/sbs/tests/pytest/test_tagger_v2.py` | Tagger tests (26K) |
| `dev/scripts/sbs/tests/pytest/test_taxonomy.py` | Taxonomy tests (28K) |
| `dev/scripts/sbs/tests/pytest/test_ledger_health.py` | Ledger health tests (16K) |
| `dev/scripts/sbs/tests/pytest/test_timing_optimization.py` | Timing tests (6K) |

### Shared Infrastructure

| Directory/File | Used By | Contents |
|----------------|---------|----------|
| `dev/scripts/sbs/core/git_ops.py` | Both | Git operations: ensure_porcelain, commit, push (9K) |
| `dev/scripts/sbs/core/branch_ops.py` | Both | Branch management (6K) |
| `dev/scripts/sbs/core/ledger.py` | Both | UnifiedLedger class, metric persistence (18K) |
| `dev/scripts/sbs/core/timing.py` | Both | Build phase timing (1K) |
| `dev/scripts/sbs/core/utils.py` | Both | Shared utilities (10K) |
| `dev/scripts/sbs/cli.py` | Both | CLI entry point, all command registration (36K) |
| `dev/scripts/sbs/__init__.py` | Both | Package initialization |

---

## Proposed Repository Structure

### SBS Monorepo (`e-vergo/Side-By-Side-Blueprint`)

Clean formalization toolchain, ready for external users.

```
Side-By-Side-Blueprint/
├── toolchain/
│   ├── Dress/                  # Artifact generation, graph layout, validation
│   ├── Runway/                 # Site generator, dashboard, paper/PDF
│   ├── SBS-Test/               # Minimal test project (33 nodes)
│   └── dress-blueprint-action/ # GitHub Action + CSS/JS assets
├── showcase/
│   ├── General_Crystallographic_Restriction/
│   ├── PrimeNumberTheoremAnd/
│   └── ReductiveGroups/
├── forks/
│   ├── subverso/               # Syntax highlighting
│   ├── verso/                  # Document framework
│   └── LeanArchitect/          # @[blueprint] attribute
├── scripts/
│   ├── build.py                # Build orchestration
│   ├── capture.py              # Screenshot capture
│   └── compliance.py           # Visual compliance validation
├── tests/
│   ├── validators/             # T1-T8 quality validators
│   ├── compliance/             # Visual compliance framework
│   └── pytest/                 # SBS-specific test suite
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

### SLS Repository (`e-vergo/SLS-Strange-Loop-Station`)

General-purpose orchestration framework.

```
SLS-Strange-Loop-Station/
├── .claude/
│   └── agents/                 # sbs-developer, sbs-oracle, sbs-self-improve
├── dev/
│   ├── scripts/
│   │   └── sls/
│   │       ├── archive/        # Upload, extraction, tagging, gates, iCloud sync
│   │       ├── labels/         # GitHub label synchronization
│   │       ├── readme/         # README freshness checking
│   │       ├── test_catalog/   # Component catalog generation
│   │       ├── commands/       # watch, dev commands
│   │       └── core/           # git_ops, branch_ops, utils, timing, ledger
│   ├── storage/
│   │   ├── archive/            # Session archive data
│   │   ├── archive_data/       # Extracted Claude Code data
│   │   └── tagging/            # Rules, taxonomy
│   └── markdowns/
│       ├── permanent/          # Architecture docs, planning docs
│       └── living/             # Evolving documentation
├── forks/
│   ├── sls-mcp/                # Extracted from sbs-lsp-mcp (orchestration + analysis tools)
│   └── vscode-lean4/           # Development fork
├── tests/
│   └── pytest/                 # Archive, gates, tagger, self-improve, taxonomy tests
├── CLAUDE.md
└── README.md
```

---

## Migration Strategy

### Phase 1: Extract Lean LSP Tools

**Scope:** Fork `lean-lsp-mcp` as a standalone, domain-agnostic package.

**Steps:**
1. Create `e-vergo/lean-lsp-mcp` repository
2. Extract the 18 `lean_*` tool handlers from `server.py`
3. Extract supporting modules: `client_utils.py`, `outline_utils.py`, `profile_utils.py`, `search_utils.py`, `loogle.py`, `file_utils.py`, `utils.py`
4. Remove Lean LSP tools from `sbs-lsp-mcp/server.py`
5. Update `.mcp.json` to reference both `lean-lsp-mcp` and `sbs-lsp-mcp`
6. Verify all 18 tools work through the new server

**Risk:** Low. The Lean LSP tools have a clean interface boundary -- they communicate with the Lean language server via LSP protocol and have no dependencies on SBS or SLS code.

**Breakage:** Agent definitions reference `mcp__sbs-lsp__lean_*` tool names. These become `mcp__lean-lsp__lean_*`. All agent `.md` files need tool name prefix updates.

### Phase 2: Create SBS Monorepo

**Scope:** Establish the clean SBS repository with toolchain, showcase, and forks.

**Steps:**
1. Create new repo structure (or restructure existing)
2. Move submodules: Dress, Runway, SBS-Test, dress-blueprint-action
3. Move showcase projects: GCR, PNT, ReductiveGroups
4. Move Lean forks: subverso, verso, LeanArchitect
5. Extract and adapt build scripts (remove archive hooks)
6. Update all `lakefile.toml` files with new submodule paths
7. Update `dress-blueprint-action/action.yml` for new repo structure
8. Set up CI workflows for the new repo

**Risk:** Medium. Submodule references are woven throughout `lakefile.toml` files, CI configs, and build scripts. Lake manifest files (`lake-manifest.json`) pin specific git revisions.

**Breakage:**
- All `lakefile.toml` git URLs change
- `runway.json` `assetsDir` paths change
- Build scripts lose archive integration (intentional)
- CI workflows need full rewrite

### Phase 3: Split MCP Server

**Scope:** Extract SBS build tools to a shared package, rename remaining server to `sls-mcp`.

**Steps:**
1. Create `sbs-tools` package with Category B tools (8 tools from `sbs_tools.py`)
2. Move `sbs_models.py`, `sbs_utils.py` to `sbs-tools`
3. Rename `sbs-lsp-mcp` to `sls-mcp`
4. Move `skill_tools.py`, `browser_tools.py`, `zulip_tools.py` to `sls-mcp`
5. Move `duckdb_layer.py`, `gate_validation.py` to `sls-mcp`
6. Update all MCP tool references in `.claude/agents/`, `CLAUDE.md`, and `.mcp.json`
7. Rename tool prefixes: `sbs_archive_state` -> `sls_archive_state`, etc.

**Risk:** High. Tool names are referenced in:
- `.claude/agents/sbs-developer.md` (44K)
- `.claude/agents/sbs-oracle.md` (39K)
- `.claude/agents/sbs-self-improve.md` (3K)
- `CLAUDE.md` (30K+)
- `dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md` (32K)
- DuckDB queries in `duckdb_layer.py` (96K)
- Skill tools that reference other tools by name (120K)
- Test files that assert tool names

**Breakage:** Every tool invocation across every agent definition, documentation file, and test must be updated. This is the highest-risk phase.

### Phase 4: Split Python Scripts

**Scope:** Distribute Python scripts between the two repos.

**Steps:**
1. Move `build/`, `tests/validators/`, `tests/compliance/`, `oracle/` to SBS repo under `scripts/`
2. Keep `archive/`, `labels/`, `readme/`, `test_catalog/`, `commands/` in SLS repo under `dev/scripts/sls/`
3. Handle `core/` (git_ops, branch_ops, utils, timing, ledger):
   - Option A: Copy to both repos (duplication, but zero coupling)
   - Option B: Extract to a pip package `sbs-core`
   - Option C: SLS depends on SBS for shared code (creates coupling)
4. Split `cli.py` into `sbs` CLI (build commands) and `sls` CLI (archive/orchestration commands)
5. Update all import paths: `sbs.build.*` stays, `sbs.archive.*` becomes `sls.archive.*`
6. Split `conftest.py` for separate test suites
7. Split pytest markers (evergreen tests need to run in both repos)

**Risk:** Medium. Import paths are deeply embedded. The `cli.py` file (36K) registers all commands from both SBS and SLS modules.

**Breakage:**
- All `python -m sbs` invocations for archive commands become `python -m sls`
- Agent definitions that call `sbs archive upload` need updating
- Build scripts that import from `sbs.archive` break
- Test conftest shared fixtures need splitting

### Phase 5: CI/CD Migration

**Scope:** Establish independent CI/CD for both repos with cross-repo triggers.

**Steps:**
1. Update `dress-blueprint-action` to work from SBS repo
2. Create SBS CI workflow: build -> test -> deploy Pages
3. Create SLS CI workflow: test -> archive validation
4. Set up cross-repo triggers:
   - SBS build completion -> SLS archive entry (via webhook or GitHub Actions)
   - SLS quality gate pass -> SBS release gate
5. Update GitHub Pages deployment for SBS repo
6. Migrate GitHub Issues (or use cross-repo references)

**Risk:** Medium. The current CI assumes a single repo. Cross-repo triggers add latency and failure modes.

**Breakage:**
- `dress-blueprint-action` references current repo structure
- Archive upload assumes local access to build artifacts
- Quality validators assume local access to storage directory

---

## Dependency Analysis

### What Breaks Immediately on Split

| Dependency | Nature | Impact |
|------------|--------|--------|
| Archive hooks in `build/orchestrator.py` | Build completion triggers archive upload | Build script must be decoupled from archive |
| Oracle compilation | Reads both SBS concept index and SLS archive data | `ask_oracle` needs to query across repos |
| Unified test suite | `conftest.py` provides fixtures for both SBS and SLS tests | Test suite must be split |
| `CLAUDE.md` | References files across both repos | Must be split into SBS and SLS versions |
| `.mcp.json` | Configures single server for all 75 tools | Must configure 2-3 servers |
| `cli.py` | Single entry point for all commands | Must be split into `sbs` and `sls` CLIs |
| `ensure_porcelain()` | Commits/pushes across all submodules in one pass | Each repo needs its own porcelain check |
| Unified ledger | `dev/storage/unified_ledger.json` stores both build metrics and archive metrics | Ledger must be split or shared |

### What Stays Connected After Split

| Connection | Direction | Mechanism |
|------------|-----------|-----------|
| SLS builds SBS projects | SLS -> SBS | SLS references SBS repo as git dependency or submodule |
| SBS build triggers SLS archive | SBS -> SLS | Webhook or GitHub Actions cross-repo trigger |
| Quality validators test SBS outputs | SLS -> SBS | Validators run in SLS, read SBS build artifacts |
| Oracle queries span both repos | Bidirectional | Shared oracle or federated query |
| Screenshot storage | SLS -> SBS | Captures stored in SLS, content from SBS |

### Submodule Impact

**Current state:** The monorepo contains submodules for Dress, Runway, SBS-Test, dress-blueprint-action, subverso, verso, LeanArchitect, sbs-lsp-mcp, and vscode-lean4.

**After split:**
- SBS repo: Dress, Runway, SBS-Test, dress-blueprint-action, subverso, verso, LeanArchitect (move from current monorepo)
- SLS repo: sls-mcp (renamed from sbs-lsp-mcp), vscode-lean4 (move from current monorepo)
- SLS repo may reference SBS as a submodule or external dependency for builds

---

## Open Questions

1. **Oracle placement:** The concept index (definitions, theorems, file purposes) is SBS data. Archive queries (session entries, quality metrics) are SLS data. The unified `ask_oracle` tool currently queries both via DuckDB. Where does it live? Does it become two tools, or does one repo expose an API the other consumes?

2. **Test catalog placement:** `test_catalog/catalog.py` generates `TEST_CATALOG.md` by scanning both SBS components (validators, compliance) and SLS components (MCP tools, archive commands). It currently lives in the SLS-side of the codebase but catalogs SBS components.

3. **CLI namespace:** All commands currently live under `python -m sbs`. Should the split create `sbs` (build, capture, compliance, oracle) and `sls` (archive, labels, readme, watch, dev)? Or should `sbs` remain the unified namespace for backward compatibility?

4. **VSCode extension fork:** The `vscode-lean4` fork contains the Blueprint infoview panel (SBS functionality) but is used exclusively during development (SLS context). Does it live in SBS as a user-facing feature or in SLS as development tooling?

5. **Quality validators:** T1-T8 validators test SBS build outputs (status colors, CSS variables, visual compliance) but are driven by SLS orchestration loops (convergence, gating, introspection). Where do the validators live? In SBS (testing its own outputs) or SLS (as part of the orchestration framework)?

6. **Shared utilities:** `core/git_ops.py`, `core/branch_ops.py`, `core/utils.py`, `core/timing.py`, `core/ledger.py` are needed by both repos. Options: (a) separate pip package, (b) copy to both repos, (c) one repo depends on the other. Each has tradeoffs between coupling, maintenance burden, and complexity.

7. **Storage directory:** `dev/storage/` contains both SBS data (screenshots, compliance ledger, project-specific captures) and SLS data (archive, archive_data, tagging rules, session archives). The unified ledger stores metrics from both domains. How is this split?

8. **GitHub Issues:** The current issue tracker on `e-vergo/Side-By-Side-Blueprint` contains both SBS bugs (rendering, layout, graph) and SLS issues (archive, orchestration, skills). Migration requires classifying 200+ issues and setting up cross-repo references for mixed concerns.
