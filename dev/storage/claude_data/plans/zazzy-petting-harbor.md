# Plan: Batch Dev Issues #84-93 (3 Waves)

**Branch:** `task/84-93-devtools-overhaul`
**Issues:** #84, #85, #86, #87, #88, #89, #90, #91, #92, #93

---

## Wave 1: Foundation Fixes

Single `sbs-developer` agent. All changes are independent.

### 1a. #85 -- Fix outcome_tagger import

**File:** `dev/scripts/sbs/archive/tagger.py` lines 216-224

Problem: `_execute_hook` uses `importlib.util.spec_from_file_location(module_name, module_path)` which registers modules with bare names (no parent package). `outcome_tagger.py` uses `from .signal_detector import ...` which needs package context.

Fix: Before loading hook modules, register hooks directory as a package in `sys.modules`:
```python
import types
# In _execute_hook, before line 218:
hooks_pkg_name = "tagging_hooks"
if hooks_pkg_name not in sys.modules:
    hooks_pkg = types.ModuleType(hooks_pkg_name)
    hooks_pkg.__path__ = [str(self.hooks_dir)]
    hooks_pkg.__package__ = hooks_pkg_name
    sys.modules[hooks_pkg_name] = hooks_pkg
# Use package-qualified name
qualified_name = f"{hooks_pkg_name}.{module_name}"
spec = importlib.util.spec_from_file_location(qualified_name, module_path, ...)
```

### 1b. #92 -- Phase ordering enforcement (MCP + SKILL.md)

**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` lines 2999-3011

Problem: `sbs_skill_transition` only validates skill ownership, not phase ordering. 5.7% of tasks skip planning.

Fix: Add `VALID_TRANSITIONS` dict after skill-match check:
```python
VALID_TRANSITIONS = {
    "task": {"alignment": {"planning"}, "planning": {"execution"}, "execution": {"finalization"}},
    "update-and-archive": {"retrospective": {"readme-wave"}, "readme-wave": {"oracle-regen"}, "oracle-regen": {"porcelain"}, "porcelain": {"archive-upload"}},
}
```
Reject transitions not in allowed set. Also reinforce in `.claude/skills/task/SKILL.md`.

Add tests in `forks/sbs-lsp-mcp/tests/test_skill_tools.py`.

### 1c. #91 -- Question-skill correlation fix (MCP)

**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` lines 1348-1381

Problem: `_correlate_with_archive` uses point-in-time lookup. Most entries have `global_state: null`, so all 474 questions get `skill='none'`.

Fix: Replace with interval-based lookup. Build time intervals from skill lifecycle entries (`phase_start` opens interval, `phase_end`/`phase_fail`/`handoff` closes it). Check if question timestamp falls within any interval.

### 1d. #88 -- sbs_skill_fail MCP tool

**Files:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` -- new `SkillFailResult` model
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` -- new tool after `sbs_skill_end` (line 3109)

Parameters: `skill`, `reason`, `work_preserved` (optional dict), `recovery_hint` (optional str), `issue_refs`.
Uses `state_transition="phase_fail"`. Clears global_state.

### 1e. #87 -- Auto-validators on every build

**File:** `dev/scripts/sbs/archive/upload.py` line 362

Change: `should_validate = validate or (trigger == "build" and not quality_scores)`
To: `should_validate = validate or (trigger == "build")`

One-line fix. T5+T6 always run after builds (~5s overhead).

### Wave 1 Validation
- `pytest sbs/tests/pytest -m evergreen --tb=short` -- all pass
- Verify `sbs archive upload --trigger build` runs outcome_tagger without ImportError
- Verify `sbs_skill_transition` rejects alignment->execution for task skill

---

## Wave 2: Tag System Redesign

Single `sbs-developer` agent. Depends on Wave 1 (#85 import fix).

### 2a. #86 + #90 -- Prune legacy noise, replace bash-error-rate-high

**Key insight from exploration:** The 5 noise tags (`heavy-session`, `toolchain-change`, `has-plans`, `visual-change`, `css-modified`) are from pre-v2.0 historical data. Current v2.0 rules don't produce these. So the fix has two parts:

**Part 1: Fix `sbs_tag_effectiveness` analysis** (MCP tool)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` -- update to filter by tag format or recent entries only
- Tags with `:` delimiter are v2.0; tags without are legacy
- Report separately or filter legacy tags out of findings

**Part 2: Replace `signal:bash-error-rate-high`**
- `dev/storage/tagging/hooks/signal_detector.py`
- Replace threshold-based bash error rate with `signal:consecutive-bash-failures` (3+ failures in a row)
- Add `signal:same-command-retry` (identical command run 3+ times)

### 2b. Enhance outcome_tagger.py

Now that it loads (#85), add new outcome tags:
- `outcome:scope-expanded` -- plan files modified during execution phase
- `outcome:build-after-fix-failed` -- build fails after an edit attempt
- Update taxonomy YAML with new tag definitions

### 2c. Add `phase_fail` tag rule

**File:** `dev/storage/tagging/rules.yaml`
```yaml
- name: transition-phase-fail
  condition:
    field: state_transition
    equals: "phase_fail"
  tags: ["transition:phase-fail"]
```

### Wave 2 Validation
- `pytest sbs/tests/pytest -m evergreen --tb=short`
- `pytest sbs/tests/pytest/test_tagger_v2.py -v`
- `pytest sbs/tests/pytest/test_agent_state_taxonomy.py -v`
- Verify outcome_tagger hook executes during `sbs archive upload`

---

## Wave 3: Workflow Evolution + Tests

Single `sbs-developer` agent.

### 3a. #84 + #89 -- /update-and-archive redesign

**File:** `.claude/skills/update-and-archive/SKILL.md`

Major changes:
1. **Add `retrospective` substate** as FIRST phase (before readme-wave)
   - 5 dimensions: user orchestration, Claude alignment, system design, plan execution, meta-observations
   - Output: `dev/storage/archive/retrospectives/<entry-id>.md` + summary field in archive entry notes
   - Agent reads current session context + recent archive entries
   - Emphasis on specific examples, user answer patterns, repeated questions

2. **Conditional skip logic** for readme-wave:
   - If `sbs readme-check --json` shows 0 repos changed, skip Parts 0-1
   - Skip oracle-regen if `sbs-oracle.md` modification time is after last code change

3. **Timing instrumentation**:
   - Record start time for each substate in archive entry notes
   - Enable tracking of finalization bottlenecks

4. **Update substate table and transitions:**
   ```
   retrospective -> readme-wave -> oracle-regen -> porcelain -> archive-upload
   ```

5. **Update VALID_TRANSITIONS** in MCP (already included in Wave 1 #92 -- just needs `retrospective` key)

6. **Create directory:** `dev/storage/archive/retrospectives/`

### 3b. #93 -- /log test coverage

**New file:** `dev/scripts/sbs/tests/pytest/test_log_skill.py`

Following `test_self_improve.py` patterns:
- V1: SKILL.md exists and has valid frontmatter (name, version, description)
- V2: Three-phase workflow sections present (Alignment, Draft & Review, Create)
- V3: Archive protocol section references correct commands
- V4: Label taxonomy integration (type/area labels exist in taxonomy)
- V5: Keyword-to-type mapping completeness
- All marked `@pytest.mark.evergreen`

### Wave 3 Validation
- `pytest sbs/tests/pytest -m evergreen --tb=short` -- all pass (including new test_log_skill.py)
- Verify SKILL.md files parse correctly
- Verify retrospectives directory exists

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

Pragmatic enforcement: core functionality works, test coverage for new code. Runtime-dependent improvements (#87 coverage %) validate over time.

---

## Success Criteria

| Issue | Criterion |
|-------|-----------|
| #85 | outcome_tagger hook runs without ImportError during archive upload |
| #86 | tag_effectiveness analysis separates legacy/v2.0 tags; new outcome tags defined |
| #87 | Builds always run T5+T6 validators |
| #88 | `sbs_skill_fail` MCP tool exists and records failure context |
| #89 | /update-and-archive has conditional skips and timing instrumentation |
| #90 | `bash-error-rate-high` replaced with `consecutive-bash-failures` |
| #91 | `sbs_question_stats()` shows questions distributed across skills |
| #92 | `sbs_skill_transition` rejects invalid phase sequences |
| #93 | `test_log_skill.py` exists with evergreen tests, all passing |
| #84 | `retrospective` substate added to u&a; retrospectives directory created |

---

## Files Modified

| File | Issues |
|------|--------|
| `dev/scripts/sbs/archive/tagger.py` | #85 |
| `dev/scripts/sbs/archive/upload.py` | #87 |
| `dev/storage/tagging/hooks/signal_detector.py` | #90 |
| `dev/storage/tagging/hooks/outcome_tagger.py` | #86 |
| `dev/storage/tagging/rules.yaml` | #86, #88 |
| `dev/storage/tagging/agent_state_taxonomy.yaml` | #86 |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | #88, #92 |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | #88 |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` | #86, #91 |
| `forks/sbs-lsp-mcp/tests/test_skill_tools.py` | #88, #92 |
| `.claude/skills/task/SKILL.md` | #92 |
| `.claude/skills/update-and-archive/SKILL.md` | #84, #89 |
| `dev/scripts/sbs/tests/pytest/test_log_skill.py` (new) | #93 |

## Verification

After all waves:
1. `pytest sbs/tests/pytest -m evergreen --tb=short` -- 100% pass
2. `sbs archive upload --trigger build` -- outcome_tagger runs, no ImportError
3. MCP: `sbs_skill_transition(skill="task", to_phase="execution")` from alignment state returns error
4. MCP: `sbs_question_stats()` -- questions distributed across skills (may require new session data)
5. Review tag_effectiveness for reduced noise
