# MCP Skill Migration Plan (#211, #212, #213)

## Summary

Migrate all 6 skills from prompt-based (SKILL.md) to MCP-first implementation:
- **#212**: Full MCP orchestration for task, log, qa, introspect, converge, update-and-archive
- **#211**: New `sbs_divination` MCP tool for deep research
- **#213**: Remove automatic doc updates from update-and-archive

---

## Architecture

### Tool Structure

**Hybrid monolithic:** Single tool per skill with `phase` parameter.

```
sbs_task(phase="start"|"plan"|"execute"|"finalize", ...)
sbs_log(title, body=None, labels=None)  # atomic, no phases
sbs_qa(phase="setup"|"review"|"report", project, pages=None)
sbs_introspect(level, phase="discovery"|"selection"|..., dry_run=False)
sbs_converge(phase="setup"|"eval"|"fix"|"rebuild"|"report", project, ...)
sbs_update_and_archive(phase="retrospective"|"porcelain"|"upload")  # simplified per #213
sbs_divination(query, scope=None, depth="quick")  # NEW per #211
```

### File Locations

| File | Purpose |
|------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` | **NEW:** All skill tool implementations |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/gate_validation.py` | **NEW:** Gate spec parsing and validation |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | Add TaskResult, LogResult, DivinationResult, etc. |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py` | Register skill tools |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | Update VALID_TRANSITIONS for simplified update-and-archive |
| `forks/sbs-lsp-mcp/tests/test_skill_tools_v2.py` | **NEW:** Comprehensive skill tests |

### Relationship to Lifecycle Tools

Skill tools USE lifecycle tools (don't replace):

```
sbs_task() → sbs_skill_start() → _run_archive_upload()
           → sbs_skill_transition()
           → sbs_skill_handoff()
```

---

## Implementation Waves

### Wave 1: Infrastructure (skill_tools.py skeleton + models)

**Files:**
- `sbs_lsp_mcp/skill_tools.py` - module with `register_skill_tools(mcp)`
- `sbs_lsp_mcp/gate_validation.py` - GateSpec dataclass, parse_gate_spec_from_plan()
- `sbs_lsp_mcp/sbs_models.py` - TaskResult, LogResult, QAResult, IntrospectResult, ConvergeResult, UpdateArchiveResult, DivinationResult

**Result models pattern:**
```python
class TaskResult(BaseModel):
    success: bool
    error: Optional[str] = None
    phase_completed: Optional[str] = None
    next_action: Optional[str] = None  # "plan", "execute", "finalize", "update-and-archive"
    gate_results: List[str] = []
    gate_failures: List[str] = []
    requires_approval: bool = False
    pr_number: Optional[int] = None
    agents_to_spawn: Optional[List[Dict]] = None  # Instructions for orchestrator
```

### Wave 2: Simple Skills (log, divination)

**sbs_log:**
- Parse input for title/body/labels
- Apply taxonomy inference (from SKILL.md parsing rules)
- Call `sbs_issue_create`
- Archive with `sbs archive upload --trigger skill --issue-refs <n>`
- Return LogResult

**sbs_divination (NEW - #211):**
- Background research agent without global_state
- Calls `ask_oracle`, reads files, explores archive
- Returns DivinationResult with files_explored, patterns, suggestions
- No state tracking (stateless operation)

### Wave 3: Medium Skills (qa, update-and-archive)

**sbs_qa:**
- Phase handlers: _qa_setup(), _qa_review(), _qa_report()
- Browser interaction via existing browser_* MCP tools
- Returns QAResult with page_status dict, issues_logged

**sbs_update_and_archive (simplified per #213):**
- Remove readme-wave and oracle-regen phases
- New flow: retrospective → porcelain → upload
- Update VALID_TRANSITIONS in sbs_tools.py:
  ```python
  "update-and-archive": {
      "retrospective": {"porcelain"},
      "porcelain": {"archive-upload"},
  }
  ```

### Wave 4: Complex Skills (task, introspect, converge)

**sbs_task:**
- Phase handlers with gate validation
- _task_start(): Create branch/PR, call sbs_skill_start
- _task_plan(): Parse gate spec, store in context, transition
- _task_execute(): Return agents_to_spawn for current wave
- _task_finalize(): Validate gates, merge PR, handoff to update-and-archive

**sbs_introspect:**
- Level dispatch (L2 vs L3+)
- L2: discovery → selection → dialogue → logging → archive
- L3+: ingestion → synthesis → archive
- Analysis tool calls (sbs_user_patterns, sbs_successful_sessions, etc.)

**sbs_converge:**
- Iteration loop state management
- eval-N → fix-N → introspect-N → rebuild-N
- Plateau detection, hardcore mode
- Returns ConvergeResult with iteration_count, pass_rate_history, exit_reason

### Wave 5: Tests + SKILL.md Deletion

**Test file:** `forks/sbs-lsp-mcp/tests/test_skill_tools_v2.py`

Test categories:
- Phase transition tests (valid/invalid)
- State recovery tests (compaction survival)
- Gate validation tests (pass/fail/override)
- Integration tests (full lifecycle per skill)

**After tests pass:**
- Delete `.claude/skills/*/SKILL.md` files (6 files)
- Update CLAUDE.md "Custom Skills" section to reference MCP tools
- Archive SKILL.md content to `dev/skills/archive/` for reference

---

## Gate Enforcement (#212 core requirement)

**Location:** In skill tool phase handlers, before calling lifecycle tools.

```python
def _task_finalize(ctx, merge_pr):
    # 1. Load gate spec from plan
    spec = load_gate_spec_from_context(ctx)

    # 2. Validate gates
    result = validate_gates(ctx, spec, project)

    # 3. If failure, return requires_approval
    if not result.all_pass:
        return TaskResult(
            success=False,
            requires_approval=True,
            gate_failures=result.failures,
            error="Gates failed - user approval required"
        )

    # 4. If pass, proceed with lifecycle
    sbs_skill_transition(skill="task", to_phase="finalization")
    # ... merge PR, close issues ...
    sbs_skill_handoff(from_skill="task", to_skill="update-and-archive", ...)
```

---

## Changes for #213 (Remove Auto Doc Updates)

1. **VALID_TRANSITIONS update:**
   ```python
   # Before (5 phases):
   "update-and-archive": {
       "retrospective": {"readme-wave"},
       "readme-wave": {"oracle-regen"},
       "oracle-regen": {"porcelain"},
       "porcelain": {"archive-upload"},
   }

   # After (3 phases):
   "update-and-archive": {
       "retrospective": {"porcelain"},
       "porcelain": {"archive-upload"},
   }
   ```

2. **sbs_update_and_archive implementation:**
   - _update_archive_retrospective(): Write L1 retrospective
   - _update_archive_porcelain(): Commit all changes, push via subprocess
   - _update_archive_upload(): Final archive entry, clear state

3. **CLAUDE.md update:**
   - Remove references to automatic README refresh
   - Note that docs are updated manually during regular work

---

## Verification

### Gates for This Task

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: >= 0.8  # CSS variable coverage
    T6: >= 0.9  # Status color match
```

### End-to-End Validation

1. **Unit tests:** `pytest forks/sbs-lsp-mcp/tests/test_skill_tools_v2.py -v`
2. **MCP tool tests:** `sbs_run_tests(repo="mcp")`
3. **Integration:** Invoke each skill tool via MCP, verify archive entries
4. **Functional parity:** Compare behavior to SKILL.md guidance

### Success Criteria

- [ ] All 7 skill tools implemented (6 existing + divination)
- [ ] Gate enforcement in sbs_task before finalization
- [ ] VALID_TRANSITIONS updated for simplified update-and-archive
- [ ] 300+ tests covering all skill behavior
- [ ] SKILL.md files deleted
- [ ] CLAUDE.md updated with MCP tool references
- [ ] Evergreen tests pass

---

## Critical Files to Modify

| File | Changes |
|------|---------|
| [skill_tools.py](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py) | **CREATE:** All skill tool implementations |
| [gate_validation.py](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/gate_validation.py) | **CREATE:** Gate spec parsing |
| [sbs_models.py](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py) | ADD: 7 new result models |
| [server.py](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py) | ADD: `register_skill_tools(mcp)` call |
| [sbs_tools.py](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py) | UPDATE: VALID_TRANSITIONS for update-and-archive |
| [test_skill_tools_v2.py](forks/sbs-lsp-mcp/tests/test_skill_tools_v2.py) | **CREATE:** Comprehensive tests |
| [CLAUDE.md](CLAUDE.md) | UPDATE: Custom Skills section, remove auto doc references |
| `.claude/skills/*/SKILL.md` | **DELETE:** All 6 files after tests pass |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Knowledge loss from SKILL.md | Archive to `dev/skills/archive/`, preserve in tool docstrings |
| Behavioral regression | 300+ tests before deletion, functional parity checks |
| Gate bypass | Enforcement in skill tool, not lifecycle tool (can't skip) |
| Rollback needed | Keep SKILL.md until full test suite passes |
