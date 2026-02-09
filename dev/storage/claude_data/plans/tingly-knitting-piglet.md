# Plan: Unified Skill-Agent Architecture with MCP Orchestration

**Issue:** #29
**Status:** Ready for approval

## Summary

Transform the current 3-agent + 4-skill architecture into a unified 1-agent + 5-skill model with MCP orchestration tools.

**Before:** sbs-developer, sbs-oracle, sbs-improver agents + /task, /log, /self-improve, /update-and-archive skills
**After:** sbs-developer agent only + /task, /oracle (NEW), /log, /self-improve, /update-and-archive skills + MCP orchestration tools

---

## Gates

```yaml
gates:
  tests: all_pass
  quality:
    T1: >= 0.9  # CLI execution
    T2: >= 0.9  # Ledger population
  regression: >= 0
```

---

## Wave 1: Create /oracle Skill

**Goal:** Transform Oracle agent into user-invocable skill.

### Files to Create

| File | Description |
|------|-------------|
| `.claude/skills/oracle/SKILL.md` | Oracle skill definition (~400 lines) |

### SKILL.md Structure

```markdown
---
name: oracle
description: Zero-shot codebase question answering
version: 1.0.0
---

# /oracle - Codebase Question Answering

## Invocation
| Pattern | Behavior |
|---------|----------|
| `/oracle` | Interactive - prompts for question |
| `/oracle <question>` | Direct query |

## Archive Protocol
- Atomic skill (single archive upload on completion)
- No global_state tracking (lightweight queries)

## Required Reading
```
/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/agents/sbs-oracle.md
```

## Query Processing
1. Load concept index from sbs-oracle.md
2. Search for file/concept matches
3. Report paths with context
4. Flag uncertainty if no clear match
```

**Note:** Keep sbs-oracle.md for now (MCP tool `sbs_oracle_query` uses it). Will be regenerated during /update-and-archive.

---

## Wave 2: Consolidate /self-improve

**Goal:** Move improver framework into skill, remove agent dependency.

### Files to Modify

| File | Changes |
|------|---------|
| `.claude/skills/self-improve/SKILL.md` | Add Four Pillars framework, Analysis Workflow, Finding Template |

### Content to Add (from sbs-improver.md)

1. **Four Pillars Framework** (lines 26-94)
   - User Effectiveness signals
   - Claude Execution signals
   - Alignment Patterns signals
   - System Engineering signals

2. **Analysis Workflow** (lines 124-161)
   - Step 1: Gather Data
   - Step 2: Pattern Detection
   - Step 3: Generate Findings
   - Step 4: Prioritize

3. **Finding Template** (lines 166-184)
   - YAML structure for findings

### Line to Remove

```markdown
## Agent

This skill uses the `sbs-improver` agent for analysis work. See `.claude/agents/sbs-improver.md`.
```

---

## Wave 3: Add MCP Orchestration Tools

**Goal:** Python-native MCP tools for skill orchestration.

### Files to Modify

| File | Changes |
|------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | Add skill result models |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | Add skill orchestration tools |

### New MCP Tools

| Tool | Purpose | State Change |
|------|---------|--------------|
| `sbs_skill_status` | Get current skill/substate | Read-only |
| `sbs_skill_start` | Start a skill, set global_state | Write |
| `sbs_skill_transition` | Move to next phase | Write |
| `sbs_skill_end` | Clear global_state | Write |

### Tool Specifications

**sbs_skill_status** (read-only)
```python
def sbs_skill_status(ctx: Context) -> SkillStatusResult:
    """Get current skill orchestration status."""
    # Returns: active_skill, substate, can_start_new
```

**sbs_skill_start** (write)
```python
def sbs_skill_start(
    ctx: Context,
    skill: str,  # task, self-improve, update-and-archive
    initial_substate: str,
    issue_refs: Optional[List[int]] = None,
) -> SkillStartResult:
    """Start a skill by setting global_state."""
    # Checks for conflicts, runs archive upload
```

**sbs_skill_transition** (write)
```python
def sbs_skill_transition(
    ctx: Context,
    skill: str,
    to_phase: str,
    is_final: bool = False,
) -> SkillTransitionResult:
    """Transition skill to next phase."""
    # Runs archive upload with state_transition marker
```

**sbs_skill_end** (write)
```python
def sbs_skill_end(
    ctx: Context,
    skill: str,
    issue_refs: Optional[List[int]] = None,
) -> SkillEndResult:
    """End a skill, clear global_state."""
    # Runs archive upload with phase_end
```

### Pydantic Models

```python
class SkillStatusResult(BaseModel):
    active_skill: Optional[str]
    substate: Optional[str]
    can_start_new: bool
    entries_in_phase: int

class SkillStartResult(BaseModel):
    success: bool
    error: Optional[str]
    archive_entry_id: Optional[str]

class SkillTransitionResult(BaseModel):
    success: bool
    from_phase: Optional[str]
    to_phase: str
    archive_entry_id: Optional[str]

class SkillEndResult(BaseModel):
    success: bool
    archive_entry_id: Optional[str]
```

---

## Wave 4: Delete Obsolete Agents

**Goal:** Remove agent files after migration verified.

### Files to Delete

| File | Verification Before Delete |
|------|---------------------------|
| `.claude/agents/sbs-oracle.md` | /oracle skill works, sbs_oracle_query still functional |
| `.claude/agents/sbs-improver.md` | /self-improve has all framework content |

**Note:** sbs-oracle.md is the compiled concept index. After deletion, `sbs oracle compile` will regenerate it. The /oracle skill's "Required Reading" will need to point to the new location or use inline content.

### Decision: Keep sbs-oracle.md as generated file

The concept index should remain at `.claude/agents/sbs-oracle.md` because:
1. `sbs_oracle_query` MCP tool parses it
2. `sbs oracle compile` generates it
3. /oracle skill references it via Required Reading

Only delete `sbs-improver.md`.

---

## Wave 5: Documentation Updates

### Files to Modify

| File | Changes |
|------|---------|
| `CLAUDE.md` | Update Orchestration Model, skill descriptions, MCP tool reference |
| `.claude/agents/sbs-developer.md` | Update Oracle reference section |
| `dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md` | Update architecture description |
| `dev/storage/README.md` | Add MCP skill tools to reference |

### CLAUDE.md Updates

1. **Orchestration Model** - Change from "3 agents" to "1 agent"
2. **Custom Skills** - Add /oracle description
3. **MCP Tool Usage** - Add skill orchestration tools table

### sbs-developer.md Updates

Change lines 185-207:
```markdown
## SBS-Oracle for Codebase Questions
When you need to know "where is X?"...
spawn the Oracle BEFORE searching
```

To:
```markdown
## /oracle Skill for Codebase Questions
When you need to know "where is X?"...
invoke /oracle or use sbs_oracle_query MCP tool
```

---

## Wave 6: Tests

### New Test File

`forks/sbs-lsp-mcp/tests/test_skill_tools.py`

### Test Cases

```python
def test_sbs_skill_status_idle():
    """Status returns null when no skill active."""

def test_sbs_skill_status_active():
    """Status returns skill/substate when active."""

def test_sbs_skill_start_success():
    """Start sets global_state correctly."""

def test_sbs_skill_start_conflict():
    """Start fails when another skill owns state."""

def test_sbs_skill_transition_success():
    """Transition updates substate correctly."""

def test_sbs_skill_end_clears_state():
    """End clears global_state."""
```

---

## Execution Order

```
Wave 1: /oracle skill ─────────────────────────────┐
                                                   │
Wave 2: /self-improve consolidation ───────────────┤
                                                   ├─► Wave 4: Delete sbs-improver.md
Wave 3: MCP orchestration tools ───────────────────┤
                                                   │
Wave 6: Tests (parallel) ──────────────────────────┘
                                                   │
                                                   ▼
                                    Wave 5: Documentation updates
```

---

## Verification

### After Each Wave

1. **Wave 1:** `/oracle where is graph layout` returns correct paths
2. **Wave 2:** `/self-improve --dry-run` shows Four Pillars analysis
3. **Wave 3:** `sbs_skill_status` MCP tool returns valid response
4. **Wave 4:** No references to deleted files remain
5. **Wave 5:** Documentation renders correctly, no broken links
6. **Wave 6:** `pytest forks/sbs-lsp-mcp/tests/test_skill_tools.py -v` passes

### End-to-End Test

1. Start fresh session
2. Invoke `/task #29` (or similar)
3. Verify MCP tools track state correctly
4. Complete task through all phases
5. Verify archive entries have correct global_state
6. Invoke `/self-improve` to analyze the task
7. Verify Four Pillars framework is applied

---

## Critical Files Summary

| Action | File |
|--------|------|
| CREATE | `.claude/skills/oracle/SKILL.md` |
| MODIFY | `.claude/skills/self-improve/SKILL.md` |
| MODIFY | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` |
| MODIFY | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` |
| DELETE | `.claude/agents/sbs-improver.md` |
| MODIFY | `CLAUDE.md` |
| MODIFY | `.claude/agents/sbs-developer.md` |
| MODIFY | `dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md` |
| CREATE | `forks/sbs-lsp-mcp/tests/test_skill_tools.py` |
