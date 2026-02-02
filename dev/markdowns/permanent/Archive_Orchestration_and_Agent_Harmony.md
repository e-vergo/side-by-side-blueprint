# Archive, Orchestration, and Agent Harmony

This document describes how scripts and agents interact in the Side-by-Side Blueprint codebase. It defines the boundaries, explains the workflows, and documents the invariants that keep the system coherent.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Three Roles of Archive](#three-roles-of-archive)
3. [State Machine Model](#state-machine-model)
4. [Epoch Semantics](#epoch-semantics)
5. [MCP Fork Philosophy](#mcp-fork-philosophy)
6. [Context Injection Patterns](#context-injection-patterns)
7. [Archive Workflow Diagrams](#archive-workflow-diagrams)
8. [Trigger Semantics](#trigger-semantics)
9. [Hybrid Compliance Pattern](#hybrid-compliance-pattern)
10. [Validator to T1-T8 Mapping](#validator-to-t1-t8-mapping)
11. [File Responsibility Matrix](#file-responsibility-matrix)
12. [Schema Reference](#schema-reference)

---

## Design Principles

### Script-Agent Boundary

**Scripts are standalone CLI tools.** They:
- Produce output (JSON, text, files)
- Modify state (ledgers, git repos, iCloud)
- NEVER invoke Claude APIs
- NEVER spawn agents
- NEVER make AI decisions

**Agents orchestrate scripts.** They:
- Invoke scripts via Bash
- Parse script output
- Make AI-powered decisions
- Coordinate multi-step workflows
- NEVER bypass scripts for state changes

This separation ensures:
1. **Testability**: Scripts can be tested without mocking AI
2. **Reproducibility**: Script behavior is deterministic
3. **Auditability**: All state changes go through versioned code
4. **Composability**: Scripts combine into complex workflows

### Why This Matters

Consider `sbs archive upload`:

```
+------------------+     +-------------------+     +------------------+
|  build.py        | --> | archive_upload()  | --> | archive_index.json|
|  (orchestrator)  |     | (Python function) |     | (state file)      |
+------------------+     +-------------------+     +------------------+
         |
         v
+------------------+
| unified_ledger   |
| (metrics store)  |
+------------------+
```

The build orchestrator calls `archive_upload()` at the end of every build. The function:
1. Extracts `~/.claude` session data
2. Creates an `ArchiveEntry`
3. Applies tagging rules
4. Saves to `archive_index.json`
5. Syncs to iCloud
6. Ensures porcelain git state

No agent is involved. The agent's job is to *invoke* `build.py`, not to replicate its logic.

### Hybrid Patterns

Some workflows require both script logic and AI decisions. The **compliance workflow** is the canonical example:

```
+--------+     +-----------+     +--------+     +------------+     +--------+
| Agent  | --> | sbs       | --> | Agent  | --> | sbs        | --> | Ledger |
| starts |     | capture   |     | vision |     | compliance |     | update |
+--------+     +-----------+     +--------+     +------------+     +--------+
                   |                  |
                   v                  v
              Screenshots         JSON validation
              (state)             (AI decision)
```

**Why this hybrid exists:**
- Scripts don't call AI APIs (design principle)
- Agents don't bypass scripts for state (design principle)
- Visual validation requires AI (technical necessity)

The intersection is handled by:
1. Script prepares work (captures screenshots, generates prompts)
2. Agent makes AI decisions (vision analysis)
3. Script (or agent) updates state (ledger)

---

## Three Roles of Archive

The archive system serves as an **active orchestration substrate** with three distinct roles:

### Role 1: Event Log

The archive is an **append-only event log** with a regularized schema. Every significant event in the development process creates an entry.

**Characteristics:**
- Entries are immutable once created
- Schema is consistent across all entry types
- Source of truth for all project state
- Enables reconstruction of project history

**What gets logged:**
- Build completions (trigger=build)
- Skill invocations (trigger=skill)
- Manual operations (trigger=manual)
- State transitions (phase boundaries)

### Role 2: State Machine

The archive tracks **global state** and **state transitions**, functioning as a state machine for the development workflow.

**State tracking:**
- `global_state` in ArchiveIndex: Current skill and substate
- `state_transition` in entries: Phase boundaries ("phase_start", "phase_end")
- Epochs: Logical groupings closed by `/update-and-archive`

**State machine properties:**
- Single active skill at a time (sequential agent constraint)
- Clear phase boundaries within skills
- Epochs provide natural checkpoints

### Role 3: Context Provider

The archive enables **context injection** for agents, providing historical awareness without requiring agents to search.

**Context provision:**
- Query archive state before spawning agents
- Build context from entries since phase started
- Inject visual changes, quality trends, task plan into agent
- Future: MCP tools for direct archive queries

---

## State Machine Model

### Global State

The `global_state` field in `ArchiveIndex` tracks the current workflow state:

```python
{
    "skill": "task",           # Current skill name or null
    "substate": "execution"    # Current phase within skill
}
```

**When null:** No skill is active; system is idle.

**When populated:** A skill is in progress; orchestrator is coordinating work.

### State Transitions

The `state_transition` field in `ArchiveEntry` marks phase boundaries:

| Value | Meaning |
|-------|---------|
| `"phase_start"` | Beginning of a new phase |
| `"phase_end"` | Completion of a phase |
| `null` | Regular entry (not a boundary) |

### Skill Substates

Each skill has defined substates that form its internal workflow:

**`/task` skill:**
```
alignment -> planning -> execution -> finalization
```

**`/update-and-archive` skill:**
```
readme-wave -> oracle-regen -> porcelain -> archive-upload
```

### State Transition Diagram

```
                    +---------------+
                    |    IDLE       |
                    | global_state  |
                    |   = null      |
                    +-------+-------+
                            |
            /task invocation|
                            v
                    +---------------+
                    |  ALIGNMENT    |
                    | skill: task   |
                    | substate:     |
                    |  alignment    |
                    +-------+-------+
                            |
           user confirms Q&A|
                            v
                    +---------------+
                    |  PLANNING     |
                    | skill: task   |
                    | substate:     |
                    |  planning     |
                    +-------+-------+
                            |
            plan approved   |
                            v
                    +---------------+
                    |  EXECUTION    |
                    | skill: task   |
                    | substate:     |
                    |  execution    |<--+
                    +-------+-------+   |
                            |           |
                            +-----------+
                            | agent cycles
                            v
                    +---------------+
                    | FINALIZATION  |
                    | skill: task   |
                    | substate:     |
                    | finalization  |
                    +-------+-------+
                            |
          /update-and-archive
                            v
                    +---------------+
                    | README-WAVE   |
                    | skill: update |
                    | -and-archive  |
                    +-------+-------+
                            |
                            v
                    +---------------+
                    |    IDLE       |
                    | global_state  |
                    |   = null      |
                    | epoch closed  |
                    +---------------+
```

---

## Epoch Semantics

### Definition

An **epoch** is a logical unit of work bounded by `/update-and-archive` invocations. Epochs have a 1:1 correspondence with skill completions.

### Epoch Lifecycle

```
Epoch N starts (previous /update-and-archive completed)
    |
    +-- Build entries (trigger=build)
    +-- Manual entries (trigger=manual)
    +-- Skill-triggered entries (trigger=skill, state_transition=phase_start/end)
    |
    v
/update-and-archive invoked
    |
    +-- README updates
    +-- Oracle regeneration
    +-- Porcelain git state
    +-- Archive upload with epoch_summary
    |
    v
Epoch N closes, Epoch N+1 begins
```

### Epoch Summary

When an epoch closes, the final entry includes an `epoch_summary` with aggregated data:

```python
{
    "epoch_number": 42,
    "duration_hours": 3.5,
    "entry_count": 12,
    "builds": 4,
    "skill_invocations": ["task"],
    "quality_delta": {
        "start": 89.5,
        "end": 91.77,
        "change": 2.27
    },
    "repos_changed": ["Dress", "Runway"],
    "tags_applied": ["visual-improvement", "successful-build"]
}
```

### Why Epochs Matter

1. **Natural checkpoints**: Safe points for review and summary
2. **Quality tracking**: Compare metrics across epochs
3. **Context boundaries**: Clear separation between work units
4. **Audit trail**: Traceable history of development

---

## MCP Fork Philosophy

### sbs-lsp-mcp: Extending lean-lsp-mcp

The planned `sbs-lsp-mcp` will be a fork of `lean-lsp-mcp` that extends it with SBS-specific capabilities while retaining all Lean proof-writing features.

**Design principle:** General-purpose tools, not hyper-specific agents.

### Retained Capabilities (from lean-lsp-mcp)

All existing Lean tools remain available:
- `lean_diagnostic_messages` - Compilation errors
- `lean_hover_info` - Type signatures and docs
- `lean_completions` - IDE autocompletions
- `lean_goal` - Proof goals at position
- `lean_file_outline` - Module structure
- `lean_local_search` - Declaration search
- `lean_leansearch` / `lean_loogle` / `lean_leanfinder` - Mathlib search

### Added Capabilities (SBS-specific)

New tools for archive and orchestration:

| Tool | Purpose |
|------|---------|
| `sbs_oracle_query` | Query Oracle knowledge base |
| `sbs_archive_state` | Get current global state and recent entries |
| `sbs_context` | Build context for agent spawn |
| `sbs_epoch_summary` | Get summary of current or previous epoch |

### Why a Fork?

1. **Single MCP server**: Agents connect to one server for both Lean and SBS tools
2. **Shared state**: Archive context available alongside Lean capabilities
3. **Clean integration**: No coordination between multiple MCP servers
4. **Upstream potential**: SBS-specific tools could be generalized

---

## Context Injection Patterns

### Agent Spawn Context

When the orchestrator spawns an agent, it queries archive state and builds relevant context:

```
+----------------+     +------------------+     +---------------+
| Orchestrator   | --> | sbs_archive_     | --> | Context blob  |
| prepares spawn |     | state query      |     | for agent     |
+----------------+     +------------------+     +---------------+
                              |
                              v
                       +------------------+
                       | Entries since    |
                       | phase started    |
                       +------------------+
                              |
                              v
                       +------------------+
                       | Visual changes,  |
                       | quality trends,  |
                       | task plan        |
                       +------------------+
```

### What Gets Injected

| Context Type | Source | Purpose |
|--------------|--------|---------|
| **Task plan** | Current `/task` state | What the agent should accomplish |
| **Recent changes** | Entries since phase start | What's been done this session |
| **Quality trends** | Quality ledger history | Whether things are improving |
| **Visual baselines** | Screenshot hashes | What visual state to expect |
| **Relevant oracle** | Oracle KB excerpts | Domain knowledge for task |

### Context vs. Search

**Context injection** provides agents with pre-computed, relevant information.
**Search** requires agents to discover information themselves.

**When to use context injection:**
- Agent needs historical awareness
- Information is predictable and bounded
- Search would waste tokens

**When to use search:**
- Information needs are unpredictable
- Codebase exploration required
- Fresh/current state needed

---

## Archive Workflow Diagrams

### Trigger Convergence

Three sources can trigger archive upload, all converging to the same behavior:

```
build.py completion ----+---- trigger="build" ----+
                        |                         |
/update-and-archive ----+---- trigger="skill" ----+----> sbs archive upload ----> ArchiveEntry
                        |                         |
manual CLI -------------+---- trigger=none -------+
```

### Full Build Workflow

```
+------------------+
| python build.py  |
+------------------+
         |
         v
+------------------+     +------------------+     +------------------+
| Sync repos       | --> | Build toolchain  | --> | Build project    |
| (git push)       |     | (Lake build)     |     | (BLUEPRINT_DRESS)|
+------------------+     +------------------+     +------------------+
         |
         v
+------------------+     +------------------+     +------------------+
| Generate graph   | --> | Generate site    | --> | Start server     |
| (Dress CLI)      |     | (Runway CLI)     |     | (python http)    |
+------------------+     +------------------+     +------------------+
         |
         v
+------------------+     +------------------+     +------------------+
| Save metrics     | --> | Archive upload   | --> | iCloud sync      |
| (unified_ledger) |     | (archive_index)  |     | (non-blocking)   |
+------------------+     +------------------+     +------------------+
```

### /task Workflow

```
+------------------+
| User: /task      |
+------------------+
         |
         v
+------------------+     +------------------+     +------------------+
| Phase 1:         | --> | Phase 2:         | --> | Phase 3:         |
| Alignment (Q&A)  |     | Planning         |     | Execution        |
+------------------+     +------------------+     +------------------+
                                                          |
                                                          v
                              +------------------------------------------+
                              | For each agent/wave:                     |
                              |   1. Spawn sbs-developer                 |
                              |   2. Agent runs build.py                 |
                              |   3. Run validators                      |
                              |   4. Retry on failure (once)             |
                              +------------------------------------------+
                                                          |
                                                          v
+------------------+     +------------------+     +------------------+
| Phase 4:         | --> | Phase 5:         | --> | Archive upload   |
| Finalization     |     | /update-and-     |     | (trigger=skill)  |
| (full validation)|     | archive          |     |                  |
+------------------+     +------------------+     +------------------+
```

### Standalone Archive Upload

```
+------------------+
| sbs archive      |
| upload           |
+------------------+
         |
         v
+------------------+     +------------------+     +------------------+
| Extract          | --> | Create           | --> | Run tagging      |
| ~/.claude data   |     | ArchiveEntry     |     | engine           |
+------------------+     +------------------+     +------------------+
         |
         v
+------------------+     +------------------+     +------------------+
| Save to          | --> | Sync to          | --> | Ensure           |
| archive_index    |     | iCloud           |     | porcelain git    |
+------------------+     +------------------+     +------------------+
```

---

## Trigger Semantics

| Trigger | Invoked By | What Happens | Purpose |
|---------|-----------|--------------|---------|
| `--trigger build` | `build.py` (automatic) | Extract session, apply tags, sync | Provenance: automated build |
| `--trigger skill` | `/update-and-archive` | Same behavior | Provenance: skill invocation |
| (no flag) | User CLI | Same behavior | Provenance: manual operation |

**Key insight:** Trigger affects metadata only, not behavior. The archive always:
1. Extracts `~/.claude` data
2. Creates an entry with quality scores
3. Applies tagging rules
4. Saves to index
5. Syncs to iCloud
6. Ensures porcelain state

The `trigger` field in the entry records *how* it was created for later analysis.

---

## Hybrid Compliance Pattern

The compliance workflow demonstrates how scripts and agents cooperate when AI decisions are required.

### Data Flow

```
+-------------------+
| Agent invokes:    |
| sbs capture       |
+-------------------+
         |
         v
+-------------------+     +-------------------+
| Playwright        | --> | dev/storage/      |
| captures pages    |     | {project}/latest/ |
+-------------------+     | *.png files       |
                          +-------------------+
         |
         v
+-------------------+
| Agent invokes:    |
| sbs compliance    |
+-------------------+
         |
         v
+-------------------+     +-------------------+
| Script computes:  | --> | For each page:    |
| - Pages to check  |     | - Generate prompt |
| - Affected repos  |     | - Return to agent |
+-------------------+     +-------------------+
         |
         v
+-------------------+
| Agent performs:   |
| Vision analysis   |
| (read screenshots)|
+-------------------+
         |
         v
+-------------------+     +-------------------+
| Agent returns:    | --> | Script updates:   |
| JSON validation   |     | compliance_ledger |
| results           |     | .json             |
+-------------------+     +-------------------+
```

### Why This Pattern

**Scripts don't call AI APIs** - The `sbs compliance` command cannot invoke Claude vision APIs. It can only prepare the work (compute which pages need validation, generate prompts) and record results.

**Agents don't bypass scripts for state** - The agent doesn't write directly to `compliance_ledger.json`. It returns structured results that the compliance module records.

**Compliance is the intersection** - Visual validation genuinely requires AI (no deterministic alternative), so the hybrid pattern is necessary.

### Implementation Files

| File | Role |
|------|------|
| `dev/scripts/sbs/tests/compliance/criteria.py` | Defines what to check per page |
| `dev/scripts/sbs/tests/compliance/mapping.py` | Maps repo changes to affected pages |
| `dev/scripts/sbs/tests/compliance/validate.py` | Orchestrates validation flow |
| `dev/scripts/sbs/tests/compliance/ledger_ops.py` | Manages compliance_ledger.json |
| `dev/storage/compliance_ledger.json` | Persistent pass/fail state |

---

## Validator to T1-T8 Mapping

The quality scoring system uses 8 tests organized by type (deterministic vs. heuristic) and category.

### Test Categories

| Tests | Category | Type | Description |
|-------|----------|------|-------------|
| T1-T2 | CLI | Deterministic | CLI execution, ledger population |
| T3-T4 | Dashboard | AI Vision | Dashboard clarity, toggle discoverability |
| T5-T6 | Design | Deterministic | Status color match, CSS variable coverage |
| T7-T8 | Polish | AI Vision | Jarring-free check, professional score |

### Detailed Breakdown

| Test | Name | Weight | Validator File | Type |
|------|------|--------|----------------|------|
| T1 | CLI Execution | 10% | `pytest/test_cli.py` | Deterministic |
| T2 | Ledger Population | 10% | `pytest/test_ledger_health.py` | Deterministic |
| T3 | Dashboard Clarity | 10% | `design/dashboard_clarity.py` | AI Vision |
| T4 | Toggle Discoverability | 10% | `design/toggle_discoverability.py` | AI Vision |
| T5 | Status Color Match | 15% | `design/color_match.py` | Deterministic |
| T6 | CSS Variable Coverage | 15% | `design/variable_coverage.py` | Deterministic |
| T7 | Jarring-Free Check | 15% | `design/jarring_check.py` | AI Vision |
| T8 | Professional Score | 15% | `design/professional_score.py` | AI Vision |

### Score Calculation

```
quality_score = sum(test_score * weight for each test)
```

With equal weighting between deterministic (50%) and heuristic (50%) tests.

### Validator Location

```
dev/scripts/sbs/tests/validators/
+-- base.py              # Protocol definitions
+-- registry.py          # Plugin registration
+-- visual.py            # Visual compliance wrapper
+-- timing.py            # Build timing metrics
+-- code_stats.py        # LOC and file counts
+-- git_metrics.py       # Commit/diff tracking
+-- design/
    +-- color_match.py          # T5
    +-- variable_coverage.py    # T6
    +-- dashboard_clarity.py    # T3
    +-- toggle_discoverability.py  # T4
    +-- jarring_check.py        # T7
    +-- professional_score.py   # T8
    +-- css_parser.py           # Shared CSS parsing
```

---

## File Responsibility Matrix

Each markdown file owns specific concerns and delegates to others.

### Ownership Table

| File | Owns | Delegates To |
|------|------|--------------|
| [`CLAUDE.md`](/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md) | Orchestration model, user preferences, when to spawn agents, project context | sbs-developer.md for implementation, sbs-oracle.md for codebase Q&A |
| [`.claude/agents/sbs-developer.md`](/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/agents/sbs-developer.md) | Implementation details, file locations, patterns, MCP tool usage | (self-contained technical reference) |
| [`.claude/agents/sbs-oracle.md`](/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/agents/sbs-oracle.md) | Pre-compiled knowledge indices, concept map, file purpose map | (auto-generated from READMEs) |
| [`.claude/skills/task/SKILL.md`](/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/skills/task/SKILL.md) | Workflow phases, validator specs, grab-bag mode | (self-contained skill definition) |
| [`.claude/skills/update-and-archive/SKILL.md`](/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/skills/update-and-archive/SKILL.md) | README wave structure, archive triggers, Oracle regeneration, porcelain state | (self-contained skill definition) |
| [`dev/storage/README.md`](/Users/eric/GitHub/Side-By-Side-Blueprint/dev/storage/README.md) | CLI command reference, validator infrastructure, quality scoring | Repository READMEs for component details |

### What Goes Where

**CLAUDE.md** - High-level orchestration:
- When to spawn agents vs. work directly
- User communication preferences
- Project context and repository map
- Build workflow overview

**sbs-developer.md** - Implementation details:
- Exact file paths for each component
- Code patterns and anti-patterns
- MCP tool recommendations
- Performance thresholds

**sbs-oracle.md** - Quick lookups:
- Concept-to-file mapping
- File purpose one-liners
- Cross-repo impact map
- Gotchas and tribal knowledge

**task/SKILL.md** - Workflow definition:
- Phase structure (alignment, planning, execution, finalization)
- Validator specifications
- Error handling

**update-and-archive/SKILL.md** - Finalization workflow:
- README update waves
- Git porcelain requirements
- Oracle regeneration
- Archive upload integration

**storage/README.md** - Tooling hub:
- All `sbs` CLI commands
- Validator infrastructure
- Quality scoring methodology
- Archive system details

### Cross-Reference Diagram

```
CLAUDE.md
    |
    +---> spawns ---> sbs-developer.md (implementation)
    |
    +---> invokes ---> task/SKILL.md (workflow)
    |                       |
    |                       +---> ends with ---> update-and-archive/SKILL.md
    |                                                   |
    +---> queries ---> sbs-oracle.md                    +---> runs ---> sbs archive upload
                            |                                               |
                            +--- compiled from ---> storage/README.md <-----+
                                                    (tooling hub)
```

---

## Schema Reference

### ArchiveEntry Schema

```python
@dataclass
class ArchiveEntry:
    # Identity
    entry_id: str                           # Unique ID (unix timestamp)
    created_at: str                         # ISO timestamp

    # Context
    project: str                            # Project name
    trigger: str                            # "build", "skill", or "manual"
    build_run_id: Optional[str]             # Links to unified ledger

    # State machine fields (NEW)
    global_state: Optional[dict] = None     # {skill: str, substate: str}
    state_transition: Optional[str] = None  # "phase_start", "phase_end", or null
    epoch_summary: Optional[dict] = None    # Aggregated epoch data (on close)

    # Session data
    claude_data: Optional[dict]             # Extracted ~/.claude data
    repo_commits: dict[str, str]            # Git commits at build time

    # Quality
    quality_scores: Optional[dict]          # T1-T8 scores

    # Metadata
    auto_tags: list[str]                    # Auto-applied tags
    user_tags: list[str]                    # User-applied tags
    notes: Optional[str]                    # User notes
    screenshots: list[str]                  # Captured screenshots

    # Sync status
    synced_to_icloud: bool                  # iCloud sync status
```

### ArchiveIndex Schema

```python
@dataclass
class ArchiveIndex:
    # Index metadata
    version: str                            # Schema version
    last_updated: str                       # ISO timestamp

    # State machine fields (NEW)
    global_state: Optional[dict] = None     # Current {skill, substate} or null
    last_epoch_entry: Optional[str] = None  # entry_id of last epoch close
    current_epoch_number: int = 0           # Monotonically increasing

    # Entry collection
    entries: list[ArchiveEntry]             # All entries (append-only)

    # Quick lookups
    by_project: dict[str, list[str]]        # project -> entry_ids
    by_tag: dict[str, list[str]]            # tag -> entry_ids
```

### Global State Values

```python
# When idle (no skill active)
global_state = None

# During /task skill
global_state = {
    "skill": "task",
    "substate": "alignment"     # or "planning", "execution", "finalization"
}

# During /update-and-archive skill
global_state = {
    "skill": "update-and-archive",
    "substate": "readme-wave"   # or "oracle-regen", "porcelain", "archive-upload"
}
```

### Epoch Summary Structure

```python
epoch_summary = {
    "epoch_number": 42,
    "started_at": "2026-02-01T10:00:00Z",
    "ended_at": "2026-02-01T13:30:00Z",
    "duration_hours": 3.5,
    "entry_count": 12,
    "builds": {
        "total": 4,
        "successful": 3,
        "failed": 1
    },
    "skill_invocations": ["task"],
    "quality_delta": {
        "start": 89.5,
        "end": 91.77,
        "change": 2.27
    },
    "repos_changed": ["Dress", "Runway"],
    "files_modified": 23,
    "lines_changed": 456,
    "tags_applied": ["visual-improvement", "successful-build"]
}
```

---

## Summary

The script-agent boundary is the foundation of this system:

1. **Scripts own state** - They modify ledgers, git repos, and files
2. **Agents own decisions** - They parse output and choose next steps
3. **Hybrid patterns bridge the gap** - When AI is required for decisions that affect state

The archive system now serves three roles:

1. **Event Log** - Append-only truth store for all project events
2. **State Machine** - Tracks workflow state with epochs and transitions
3. **Context Provider** - Enables context injection for agent spawning

These roles work together to create an **orchestration substrate** that agents can rely on for historical awareness and state tracking.

This document serves as the canonical reference for understanding these interactions.
