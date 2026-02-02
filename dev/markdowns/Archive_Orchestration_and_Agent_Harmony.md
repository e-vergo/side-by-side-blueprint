# Archive, Orchestration, and Agent Harmony

This document describes how scripts and agents interact in the Side-by-Side Blueprint codebase. It defines the boundaries, explains the workflows, and documents the invariants that keep the system coherent.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Archive Workflow Diagrams](#archive-workflow-diagrams)
3. [Trigger Semantics](#trigger-semantics)
4. [Hybrid Compliance Pattern](#hybrid-compliance-pattern)
5. [Validator to T1-T8 Mapping](#validator-to-t1-t8-mapping)
6. [Rubric Lifecycle](#rubric-lifecycle)
7. [File Responsibility Matrix](#file-responsibility-matrix)

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

### Trigger in ArchiveEntry

```python
@dataclass
class ArchiveEntry:
    entry_id: str
    created_at: str
    project: str
    trigger: str  # "build", "skill", or "manual"
    build_run_id: Optional[str]
    claude_data: Optional[dict]
    repo_commits: dict[str, str]
    quality_scores: Optional[dict]
    auto_tags: list[str]
    # ...
```

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
+-- rubric_validator.py  # Custom rubric evaluation
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

## Rubric Lifecycle

Rubrics enable custom quality metrics beyond the fixed T1-T8 tests.

### Phase Diagram

```
+-------------------+     +-------------------+     +-------------------+
| /task --grab-bag  | --> | Phase 1:          | --> | Phase 2:          |
| invocation        |     | Brainstorm        |     | Metric Alignment  |
+-------------------+     | (user-led)        |     | (formalize)       |
                          +-------------------+     +-------------------+
                                                            |
                                                            v
+-------------------+     +-------------------+     +-------------------+
| Phase 6:          | <-- | Phase 5:          | <-- | Phase 3:          |
| /update-and-      |     | Execution Loop    |     | Rubric Creation   |
| archive           |     | (with grading)    |     | (save to storage) |
+-------------------+     +-------------------+     +-------------------+
         |                        ^
         v                        |
+-------------------+     +-------------------+
| Archive entry     |     | Phase 4:          |
| with rubric_id    |     | Plan Mode         |
| and evaluation    |     | (task per metric) |
+-------------------+     +-------------------+
```

### State Table

| Phase | Trigger | What Happens |
|-------|---------|--------------|
| Creation | `/task --grab-bag` Phase 3 | User approves metrics, rubric saved to `dev/storage/rubrics/` |
| Evaluation | Execution loop | Each metric evaluated, results tracked in memory |
| Snapshot | Finalization | Evaluation results copied to archive entry |
| Invalidation | Repo changes | Scores marked stale via `REPO_SCORE_MAPPING` |
| Reuse | `/task --rubric <id>` | Load existing rubric for new evaluation |

### Rubric Storage

```
dev/storage/rubrics/
+-- index.json              # Registry of all rubrics
+-- {rubric-id}.json        # Rubric definition
+-- {rubric-id}.md          # Human-readable (auto-generated)
+-- {rubric-id}_eval_*.json # Evaluation results (optional)
```

### Rubric Schema

```json
{
  "id": "dashboard-ux-2025-01",
  "name": "Dashboard UX Improvements",
  "description": "Metrics from Jan 2025 grab-bag session",
  "created_at": "2025-01-15T10:30:00Z",
  "metrics": [
    {
      "id": "stat-readability",
      "name": "Stats Panel Readability",
      "threshold": 0.8,
      "weight": 0.25,
      "scoring_type": "percentage"
    }
  ]
}
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
| [`.claude/skills/task/SKILL.md`](/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/skills/task/SKILL.md) | Workflow phases, validator specs, rubric lifecycle, grab-bag mode | (self-contained skill definition) |
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
- Rubric integration
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

## Summary

The script-agent boundary is the foundation of this system:

1. **Scripts own state** - They modify ledgers, git repos, and files
2. **Agents own decisions** - They parse output and choose next steps
3. **Hybrid patterns bridge the gap** - When AI is required for decisions that affect state

The archive system demonstrates this:
- `build.py` (script) calls `archive_upload()` (function)
- The function modifies state without AI
- Agents invoke `build.py`, not the internal functions

The compliance system is the exception that proves the rule:
- Visual validation genuinely requires AI
- Scripts prepare work, agents decide, scripts record
- No other pattern would satisfy both design principles

This document serves as the canonical reference for understanding these interactions.
