# Devtools Mega-Task: Issues #79/#72, #77, #75, #67, #63

## Overview

Address all 5 unique devtools issues in a single task. Ordered by dependency: archive fix first (unblocks everything), then tools that touch the same code, then independent work, then test audit last to verify the full picture.

## Wave 1: Archive Compaction (#79/#72)

**Problem:** `archive_index.json` is 114MB, exceeding GitHub's 100MB limit. Every `ensure_porcelain()` fails to push storage.

**Approach:** Extract `claude_data` from the main index into per-entry sidecar files. The index becomes metadata-only (~5-10MB).

**Files to modify:**
- `dev/scripts/sbs/archive/entry.py` - Add `claude_data_path` field, lazy-load accessor, modify `to_dict()`/`from_dict()` to exclude claude_data from index
- `dev/scripts/sbs/archive/upload.py` - Write claude_data to sidecar file during upload
- `dev/scripts/sbs/archive/chat_archive.py` - Adjust extraction to write directly to sidecar path
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_utils.py` - Add `load_entry_claude_data(entry_id)` accessor
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` - Update analysis tools that read `claude_data`

**Migration script:** One-time script to extract `claude_data` from existing entries in `archive_index.json` into sidecar files under `dev/storage/archive_data/<entry_id>.json`, then strip it from the index.

**Sidecar file layout:**
```
dev/storage/archive_data/
  1770136844.json    # claude_data for entry 1770136844
  1770137134.json    # etc.
```

**Validation:**
- `archive_index.json` < 100MB after compaction
- `ensure_porcelain()` succeeds (storage push works)
- All MCP tools that read claude_data still function
- Existing analysis tools return same results

---

## Wave 2: Atomic Skill Handoff (#77)

**Problem:** `task -> update-and-archive` handoff has a 13% skip rate because phase_end + skill_start is two separate operations.

**Approach:** Add `handoff` state_transition type that atomically ends one skill and starts another.

**Files to modify:**
- `dev/scripts/sbs/archive/entry.py` - Accept `handoff` as valid `state_transition` value
- `dev/scripts/sbs/archive/upload.py` - Handle `--handoff-to` CLI arg: record outgoing skill completion + set incoming skill state in one entry
- `dev/scripts/sbs/archive/cmd.py` - Add `--handoff-to` argument to CLI parser
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` - Add `handoff_to` param to `sbs_skill_transition`, or add new `sbs_skill_handoff` tool
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` - Add `SkillHandoffResult` model if new tool
- `.claude/skills/task/SKILL.md` - Replace phase_end + skill_start with single handoff call
- `.claude/skills/update-and-archive/SKILL.md` - Document handoff reception

**Design choice:** New `sbs_skill_handoff` MCP tool (cleaner than overloading `sbs_skill_transition`).

```python
sbs_skill_handoff(
    from_skill: str,       # Must match current active skill
    to_skill: str,         # New skill to start
    to_substate: str,      # Initial substate for new skill
    issue_refs: Optional[List[int]] = None
) -> SkillHandoffResult
```

**Validation:**
- Handoff creates single archive entry with both transitions recorded
- `global_state` correctly shows new skill after handoff
- Old skill session marked as completed in analysis tools
- Existing `sbs_skill_end` + `sbs_skill_start` still works (backward compatible)

---

## Wave 3: AskUserQuestion Analysis (#75)

**Problem:** No way to extract and analyze AskUserQuestion interactions from sessions for self-improve.

**Approach:** Two new MCP tools that parse raw Claude Code JSONL session files for `AskUserQuestion` tool calls.

**Files to modify:**
- `dev/scripts/sbs/archive/extractor.py` - Add `extract_ask_user_questions(session_path)` function
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` - Add `question_analysis_impl()` and `question_stats_impl()`
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` - Add `QuestionAnalysisResult`, `QuestionStatsResult` models
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` - Register `sbs_question_analysis` and `sbs_question_stats`

**Data extraction from JSONL:**
1. Find all `tool_use` blocks where `name == "AskUserQuestion"`
2. Extract: question text, options, header, multiSelect flag
3. Find corresponding `tool_result` block for user's answer
4. Capture surrounding context (skill/substate from archive, what triggered the question)

**Tool signatures:**
```python
sbs_question_analysis(
    since: Optional[str] = None,    # Entry ID or ISO timestamp
    until: Optional[str] = None,
    skill: Optional[str] = None,    # Filter by skill type
    limit: int = 50
) -> QuestionAnalysisResult

sbs_question_stats(
    since: Optional[str] = None,
    until: Optional[str] = None
) -> QuestionStatsResult
```

**Validation:**
- Tools return structured data from existing session files
- Statistics aggregate correctly (frequency by skill, option distributions)
- Rate: handles sessions with no AskUserQuestion calls gracefully

---

## Wave 4: Inspect Project MCP Tool (#63)

**Problem:** No automated visual QA beyond deterministic validators.

**Approach:** Single MCP tool that builds, captures screenshots, and returns structured evaluation context for agent-driven visual review.

**Files to modify:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` - Register `sbs_inspect_project`
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` - Add `InspectResult` model

**Tool signature:**
```python
sbs_inspect_project(
    project: str,                     # SBSTest, GCR, or PNT
    pages: Optional[List[str]] = None,  # Specific pages, or all
    include_issue_context: bool = True  # Load open+closed issues for context
) -> InspectResult
```

**Returns:**
- Screenshot paths for each page (captured from latest build)
- Open issues summary (for agent context)
- Closed issues summary (for regression awareness)
- Last quality scores (for baseline)
- Suggested evaluation prompts per page type

The tool does NOT do the AI evaluation itself -- it prepares the context. The calling agent (or /self-improve) does the visual assessment.

**Validation:**
- Tool returns valid screenshot paths
- Issue context loads correctly
- Works for all 3 projects

---

## Wave 5: Test Coverage Audit + Write Tests (#67)

**Problem:** Unknown mapping between MVP requirements and test coverage.

**Approach:** Map all 7 MVP success criteria + showcase requirements to existing tests, identify gaps, write missing tests.

**MVP Requirements to map:**
1. Side-by-side display (existing: `test_side_by_side.py` - 15 tests)
2. Dual authoring modes (existing: `test_authoring_modes.py` - 15 tests)
3. Dependency graph (existing: `test_dependency_graph.py` - 20 tests)
4. Status indicators (existing: `test_status_indicators.py` - 12 tests)
5. Dashboard (existing: `test_dashboard.py` - 13 tests)
6. Paper generation (existing: `test_paper_generation.py` - 12 tests)
7. CI/CD integration (existing: `test_cicd.py` - 8 tests)

**Likely gaps to investigate:**
- Visual standards (dark/light theme, responsive layout, rainbow brackets)
- Showcase-specific requirements (SBS-Test feature completeness, GCR polish, PNT scale)
- Interactive component testing (sidebar already has 6 tests, but needs tier markers)
- Cross-page design coherence
- Archive/devtools coverage for new features from waves 1-4

**Files to modify:**
- Existing test files (add missing test cases)
- Potentially new test files for uncovered areas
- `dev/scripts/sbs/tests/pytest/conftest.py` (fixtures if needed)

**Validation:**
- All MVP requirements have at least one test
- All new tests pass
- Evergreen tier tests: 100% pass rate
- Coverage gap analysis document produced

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: >= 0.8
    T6: >= 0.9
  regression: >= 0
  custom:
    - archive_index_size: < 100MB
    - storage_push: succeeds
```

## Execution Order

```
Wave 1 (archive compaction)
  -> Wave 2 (handoff)
  -> Wave 3 (question analysis)
  -> Wave 4 (inspect tool)
  -> Wave 5 (test audit)
```

Sequential: each wave is one sbs-developer agent. Wave 5 runs last to verify everything including the new tools from waves 1-4.

## Issue Closure Plan

- Close #72 immediately as duplicate of #79
- Close #79 after Wave 1 validation
- Close #77 after Wave 2 validation
- Close #75 after Wave 3 validation
- Close #63 after Wave 4 validation
- Close #67 after Wave 5 validation
