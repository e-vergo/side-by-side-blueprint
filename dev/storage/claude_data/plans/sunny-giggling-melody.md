# Plan: Migrate Skills from Prompt Injection to MCP Tool Architecture

**Issues:** #212 (skill migration), #213 (end-epoch cleanup)
**Strategy:** Big-bang migration of all 6 skills
**Approach:** Remove `.claude/skills/` entirely, skills implemented as MCP tools

---

## Architecture Overview

### Current System
- User types `/task` → Claude Code injects `<command-name>task</command-name>` tag
- Claude calls `Skill(skill="task")` tool → reads `.claude/skills/task/SKILL.md`
- Claude follows markdown instructions, calling MCP tools (`sbs_skill_start`, etc.)
- Gates and phase transitions enforced by Claude following instructions (bypassable)

### Target System
- User types `/task` → Claude Code injects `<command-name>task</command-name>` tag
- Claude calls `sbs_task()` MCP tool directly (documented in CLAUDE.md)
- MCP tool enforces phase transitions and gates in Python (unbypassable)
- MCP tool returns structured workflow metadata + next-step instructions
- Archive integration guaranteed by server-side implementation

### Key Insight
Gates become unbypassable because:
1. Phase transitions happen in Python (`sbs_skill_transition` validates allowed transitions)
2. Gate checks run in Python before allowing execution→finalization transition
3. Claude cannot skip phases or bypass gates - the MCP tool enforces discipline

---

## Implementation Waves

### Wave 0: #213 Cleanup (Preparatory Step)

**Goal:** Simplify end-epoch skill before migration

**Files to modify:**
- `.claude/skills/end-epoch/SKILL.md` - Remove auto-doc update phases
- `CLAUDE.md` - Update end-epoch description

**Changes:**
- Remove Parts 0-2 (README wave, core docs, oracle regen)
- Keep only: retrospective → porcelain → archive-upload
- Simplifies the skill definition before migration

**Gate:** Manual verification that end-epoch still works without auto-docs

---

### Wave 1: Infrastructure (Models + Workflow Definitions)

**Goal:** Add data models and workflow definitions for all skills

**New files:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_workflows.py` - Workflow definitions for all 6 skills
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_models.py` - Pydantic models for skill invocation

**Files to modify:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` - Add base skill models

**New models in `skill_models.py`:**

```python
class SkillPhase(BaseModel):
    """Definition of a single phase within a skill."""
    name: str
    description: str
    valid_transitions: List[str]
    gate_required: bool = False
    agent_concurrency: int = 1

class SkillWorkflow(BaseModel):
    """Complete workflow definition for a skill."""
    skill: str
    version: str
    description: str
    phases: List[SkillPhase]
    initial_phase: str
    final_phases: List[str]
    recovery_semantics: Dict[str, str]

class TaskArgs(BaseModel):
    """Arguments for /task invocation."""
    issue_refs: Optional[List[int]] = None
    mode: Optional[str] = None  # "crush", "--auto"
    scope: Optional[str] = None

class LogArgs(BaseModel):
    """Arguments for /log invocation."""
    text: Optional[str] = None
    issue_type: Optional[str] = None
    area: Optional[str] = None

class QAArgs(BaseModel):
    """Arguments for /qa invocation."""
    project: str
    pages: Optional[List[str]] = None

class IntrospectArgs(BaseModel):
    """Arguments for /introspect invocation."""
    level: int
    dry_run: bool = False

class ConvergeArgs(BaseModel):
    """Arguments for /converge invocation."""
    project: str
    max_iter: int = 3
    mode: Optional[str] = None

class SkillInvokeResult(BaseModel):
    """Result from invoking a skill."""
    success: bool
    error: Optional[str] = None
    skill: str
    current_phase: str
    workflow: SkillWorkflow
    archive_entry_id: Optional[str] = None
    instructions: str  # What Claude should do next
```

**Workflow definitions in `skill_workflows.py`:**

Each skill gets a `SKILL_NAME_WORKFLOW` constant with complete phase definitions:
- `TASK_WORKFLOW` - 4 phases (alignment → planning → execution → finalization)
- `LOG_WORKFLOW` - Atomic (no phases)
- `QA_WORKFLOW` - 3 phases (setup → review → report)
- `INTROSPECT_WORKFLOW` - 5 phases L1, 3 phases L2+ (discovery → selection → dialogue → logging → archive)
- `CONVERGE_WORKFLOW` - Dynamic phases (setup → [eval-N → fix-N → introspect-N → rebuild-N]* → report)
- `END_EPOCH_WORKFLOW` - 3 phases (retrospective → porcelain → archive-upload)

**Gate:** Unit tests verify all workflow models validate correctly

---

### Wave 2: Skill MCP Tools (Big-Bang Implementation)

**Goal:** Implement MCP tools for all 6 skills with unbypassable gates

**New files:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` - All skill MCP tool implementations

**Files to modify:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` - Expand `VALID_TRANSITIONS` to cover all skills
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py` - Register skill tools
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py` - Add all skills to `SKILL_PHASE_ORDERS`

**Key implementation: Gate enforcement in `sbs_skill_transition`**

Modify `sbs_tools.py` to add gate checks before transitions:

```python
# Comprehensive transition table (expand existing VALID_TRANSITIONS)
VALID_TRANSITIONS: Dict[str, Dict[str, set]] = {
    "task": {
        "alignment": {"planning"},
        "planning": {"execution"},
        "execution": {"finalization"},  # Gate check required
    },
    "qa": {
        "setup": {"review"},
        "review": {"report"},
    },
    "introspect": {
        "discovery": {"selection"},
        "selection": {"dialogue"},
        "dialogue": {"logging"},
        "logging": {"archive"},
        "ingestion": {"synthesis"},  # L2+ path
        "synthesis": {"archive"},
    },
    "converge": {
        # Dynamic - validation relaxed for converge
    },
    "end-epoch": {
        "retrospective": {"porcelain"},
        "porcelain": {"archive-upload"},
    },
    "log": {},  # Atomic, no phases
}

# Gates required before transitioning
GATED_TRANSITIONS = {
    ("task", "execution", "finalization"): True,
}

def _check_gate_before_transition(
    ctx: Context,
    skill: str,
    from_phase: str,
    to_phase: str,
    project: str = "SBSTest"
) -> tuple[bool, list[str]]:
    """Check if gates pass before allowing transition.

    Returns (passed, findings).
    """
    key = (skill, from_phase, to_phase)
    if key not in GATED_TRANSITIONS:
        return (True, [])

    # Import gate checking from dev/scripts
    from sbs.archive.gates import find_active_plan, parse_gates_from_plan, check_gates

    plan_path = find_active_plan()
    if not plan_path:
        return (False, ["No active plan found - gates cannot be validated"])

    plan_content = plan_path.read_text()
    gate_def = parse_gates_from_plan(plan_content)

    if not gate_def:
        return (False, ["No gates defined in plan"])

    gate_result = check_gates(project=project)
    return (gate_result.passed, gate_result.findings)
```

**Modify `sbs_skill_transition` to check gates:**

```python
@mcp.tool("sbs_skill_transition")
def sbs_skill_transition(
    ctx: Context,
    skill: str,
    to_phase: str,
    is_final: bool = False,
) -> SkillTransitionResult:
    # ... existing state validation ...

    # NEW: Check gates before transition
    if (skill, current_substate, to_phase) in GATED_TRANSITIONS:
        passed, findings = _check_gate_before_transition(
            ctx, skill, current_substate, to_phase
        )
        if not passed:
            return SkillTransitionResult(
                success=False,
                error=f"Gate validation failed: {'; '.join(findings)}",
                from_phase=current_substate,
                to_phase=to_phase,
                archive_entry_id=None,
            )

    # ... rest of transition logic ...
```

**Skill tool implementations in `skill_tools.py`:**

```python
@mcp.tool("sbs_task")
def sbs_task(
    ctx: Context,
    args: Optional[TaskArgs] = None,
) -> SkillInvokeResult:
    """Execute the /task skill: agentic task execution with validation."""
    from sbs_lsp_mcp.skill_workflows import TASK_WORKFLOW

    # Parse invocation args
    issue_refs = args.issue_refs if args else None
    mode = args.mode if args else None

    # Check current state
    db = _get_db(ctx)
    current_skill, current_substate = db.get_global_state()

    # If skill already active, return current state + workflow
    if current_skill == "task":
        return SkillInvokeResult(
            success=True,
            skill="task",
            current_phase=current_substate or "alignment",
            workflow=TASK_WORKFLOW,
            instructions=f"Continue from {current_substate} phase. Check archive state for context.",
        )

    # If another skill active, fail
    if current_skill:
        return SkillInvokeResult(
            success=False,
            error=f"Skill '{current_skill}' already active",
            skill="task",
            current_phase="",
            workflow=TASK_WORKFLOW,
            instructions="",
        )

    # Start the skill
    success, entry_id, error = _run_archive_upload(
        trigger="skill",
        global_state={"skill": "task", "substate": "alignment"},
        state_transition="phase_start",
        issue_refs=issue_refs,
    )

    if not success:
        return SkillInvokeResult(
            success=False,
            error=error or "Failed to start task",
            skill="task",
            current_phase="",
            workflow=TASK_WORKFLOW,
            instructions="",
        )

    db.invalidate()

    return SkillInvokeResult(
        success=True,
        skill="task",
        current_phase="alignment",
        workflow=TASK_WORKFLOW,
        archive_entry_id=entry_id,
        instructions=ALIGNMENT_INSTRUCTIONS,  # From workflow definitions
    )

# Similar implementations for sbs_log, sbs_qa, sbs_introspect, sbs_converge, sbs_end_epoch
```

**Register in `server.py`:**

```python
# After existing registrations
from sbs_lsp_mcp.skill_tools import register_skill_tools
register_skill_tools(mcp)
```

**Gate:**
- Unit tests verify gate enforcement
- Adversarial tests verify gates cannot be bypassed

---

### Wave 3: Documentation + Cleanup

**Goal:** Update documentation and remove old skill files

**Files to modify:**
- `CLAUDE.md` - Update "Custom Skills" section to document MCP invocation
- `dev/storage/README.md` - Update skill documentation

**Files to delete:**
- `.claude/skills/` directory (entire directory)

**CLAUDE.md changes:**

```markdown
## Custom Skills

Skills are implemented as MCP tools and invoked when Claude sees `<command-name>` tags.

**Integration:** When you see a `<command-name>skill-name</command-name>` tag, call the corresponding MCP tool:
- `<command-name>task</command-name>` → `sbs_task(args=TaskArgs(...))`
- `<command-name>log</command-name>` → `sbs_log(args=LogArgs(...))`
- `<command-name>qa</command-name>` → `sbs_qa(args=QAArgs(...))`
- `<command-name>introspect</command-name>` → `sbs_introspect(args=IntrospectArgs(...))`
- `<command-name>converge</command-name>` → `sbs_converge(args=ConvergeArgs(...))`
- `<command-name>end-epoch</command-name>` → `sbs_end_epoch()`

### /task
Agentic task execution with validation.

**Invocation:** `sbs_task(args=TaskArgs(issue_refs=[42], mode="crush"))`

**Workflow:** alignment → planning → execution → finalization → (handoff to /end-epoch)

**Location:** MCP tool in `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py`

[Similar sections for other skills...]
```

**Gate:** Manual verification that documentation accurately reflects implementation

---

### Wave 4: Testing

**Goal:** Comprehensive test coverage for skill MCP tools

**New test files:**
- `forks/sbs-lsp-mcp/tests/test_skill_workflows.py` - Unit tests for workflow definitions
- `forks/sbs-lsp-mcp/tests/test_skill_tools.py` - Unit tests for skill MCP tools
- `forks/sbs-lsp-mcp/tests/test_adversarial_gates.py` - Adversarial gate bypass tests
- `dev/scripts/sbs/tests/pytest/test_skill_integration.py` - Full lifecycle integration test

**Test scenarios:**

1. **Unit tests** (`test_skill_tools.py`):
   - Skill invocation with valid args
   - Skill invocation with invalid args
   - State conflict (another skill active)
   - Archive integration verification

2. **Adversarial tests** (`test_adversarial_gates.py`):
   - Attempt alignment→execution without planning (must fail)
   - Attempt execution→finalization with failing gates (must fail)
   - Attempt to start skill when another is active (must fail)
   - Attempt transition with wrong skill name (must fail)

3. **Integration test** (`test_skill_integration.py`):
   - Full /task lifecycle: start → alignment → planning → execution → finalization → handoff
   - Verify all archive entries created
   - Verify gates enforced
   - Verify handoff to /end-epoch works

**Gate:** All tests pass (100% for adversarial tests, >90% for unit tests)

---

## Critical Files Reference

| File | Purpose | Changes |
|------|---------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | Existing skill lifecycle tools | Expand `VALID_TRANSITIONS`, add `GATED_TRANSITIONS`, modify `sbs_skill_transition` |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_workflows.py` | NEW - Workflow definitions | Create with 6 workflow constants |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_models.py` | NEW - Skill data models | Create with Pydantic models |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` | NEW - Skill MCP tools | Create with 6 skill tools |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py` | MCP server registration | Add `register_skill_tools(mcp)` |
| `dev/scripts/sbs/archive/gates.py` | Gate validation logic | Reuse existing `GateDefinition`, `check_gates` |
| `CLAUDE.md` | User-facing documentation | Update "Custom Skills" section |
| `.claude/skills/` | OLD - Skill markdown files | Delete entire directory |

---

## Success Criteria Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    adversarial_gates: all_pass  # All adversarial tests must pass
  regression: >= 0  # No regressions from current behavior
```

**Validation:**
- [ ] All 6 skills work via MCP tools
- [ ] Phase transitions enforced (alignment→planning→execution→finalization required for /task)
- [ ] Gates unbypassable (adversarial tests verify)
- [ ] Archive integration guaranteed (every skill creates archive entries)
- [ ] Unit tests pass (>90% coverage)
- [ ] Integration test passes (full /task lifecycle)
- [ ] Regression tests pass (old behavior preserved)
- [ ] Adversarial gate tests pass (100%)

---

## Migration Risks

| Risk | Mitigation |
|------|------------|
| Skills don't work after migration | Integration test validates full lifecycle before cleanup |
| Gates can be bypassed | Adversarial tests specifically try to bypass gates |
| Archive integration breaks | Unit tests verify archive entries created |
| Cross-skill handoffs break | Integration test verifies task→end-epoch handoff |
| Claude doesn't know to call MCP tools | CLAUDE.md explicitly documents integration |

---

## Execution Notes

- **All 6 skills migrate together** - they share state machine, can't be partially migrated
- **#213 cleanup first** - simplifies end-epoch before migration
- **Gate enforcement is the key win** - Python validation makes discipline unbypassable
- **Integration test before cleanup** - verify everything works before deleting .claude/skills/
- **CLAUDE.md is the integration layer** - documents that `<command-name>` tags map to MCP tools
