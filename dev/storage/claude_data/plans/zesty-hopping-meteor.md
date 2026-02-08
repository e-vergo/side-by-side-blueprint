# Enrich Archive Agent-State Tag Taxonomy

## Summary

Overhaul the archive auto-tagging system with a 16-dimension, ~150 colon-delimited tag taxonomy ("agent-state tags"). Expand `build_tagging_context()` to surface state machine + token + session fields. Rewrite `rules.yaml` v2.0 with hierarchical tags. Replace stub hooks with comprehensive session profiler and signal detector. Add taxonomy validation tests.

---

## Waves

### Wave 1: Taxonomy + Context Expansion (Foundation)

**Files:**
- `dev/storage/tagging/agent_state_taxonomy.yaml` (CREATE) -- Full 16-dimension taxonomy: phase, transition, skill, trigger, session, outcome, signal, scope, repo, epoch, linkage, token, thinking, tool, quality, model
- `dev/scripts/sbs/archive/tagger.py` (MODIFY) -- Expand `build_tagging_context()` to flatten state machine fields, token counts, thinking blocks, quality scores, epoch data into the context dict
- `dev/scripts/sbs/tests/pytest/test_agent_state_taxonomy.py` (CREATE) -- Taxonomy validation: uniqueness, naming conventions, dimension coverage, loader tests

**Context expansion -- new fields to add to `build_tagging_context()`:**

```python
# State machine (from entry directly)
context["skill"] = entry.global_state.get("skill") if entry.global_state else None
context["substate"] = entry.global_state.get("substate") if entry.global_state else None
context["state_transition"] = entry.state_transition
context["has_epoch_summary"] = entry.epoch_summary is not None
context["gate_passed"] = entry.gate_validation.get("passed") if entry.gate_validation else None

# Token counts (from claude_data)
context["total_input_tokens"] = claude_data.get("total_input_tokens", 0)
context["total_output_tokens"] = claude_data.get("total_output_tokens", 0)
context["cache_read_tokens"] = claude_data.get("cache_read_tokens", 0)
context["thinking_block_count"] = claude_data.get("thinking_block_count", 0)
context["unique_tools_count"] = len(claude_data.get("unique_tools_used", []))
context["model_versions"] = claude_data.get("model_versions_used", [])

# Quality (from entry)
context["quality_overall"] = entry.quality_scores.get("overall") if entry.quality_scores else None
context["quality_delta"] = entry.quality_delta.get("overall") if entry.quality_delta else None
```

**Taxonomy YAML structure:**
```yaml
version: "2.0"
name: "agent-state"

dimensions:
  phase:
    description: "Skill lifecycle phase"
    tags:
      - name: "phase:alignment"
        description: "In alignment/Q&A phase"
      # ...
  transition:
    # ...
```

### Wave 2: Rules Rewrite (Declarative Tags)

**Files:**
- `dev/storage/tagging/rules.yaml` (REWRITE) -- v2.0 with colon-delimited tags across 10 declarative dimensions

**Dimensions covered by declarative rules** (simple field matching):

| Dimension | Rules | Example |
|---|---|---|
| **phase** | 9 rules | `substate == "alignment"` -> `["phase:alignment"]` |
| **transition** | 5 rules | `state_transition == "phase_start"` -> `["transition:phase-start"]` |
| **skill** | 5 rules | `skill == "task"` -> `["skill:task"]` |
| **trigger** | 3 rules | `trigger == "build"` -> `["trigger:build"]` |
| **scope** | 8 rules | `repos_changed_count > 2` -> `["scope:cross-repo"]`, file glob matches |
| **repo** | 12 rules | `files_modified matches */Dress/*` -> `["repo:dress"]` |
| **epoch** | 3 rules | `has_epoch_summary == true` -> `["epoch:closing"]` |
| **linkage** | 4 rules | `issue_refs is_empty: false` -> `["linkage:has-issue"]` |
| **quality** | 4 rules | `gate_passed == true` -> `["outcome:gate-pass"]` |
| **outcome** (build) | 3 rules | `build_success == true` -> `["outcome:build-success"]` |

**Total:** ~56 declarative rules replacing the current 18.

**Backward compat:** Old flat tag names dropped from rules.yaml. Existing entries in the archive keep their old `auto_tags` values unchanged (immutable archive). New entries get colon-delimited tags.

### Wave 3: Hooks Rewrite (Complex Tags)

**Files:**
- `dev/storage/tagging/hooks/session_profiler.py` (CREATE, replaces `session_quality.py`) -- Comprehensive session behavioral analysis
- `dev/storage/tagging/hooks/signal_detector.py` (CREATE, replaces `cli_arg_misfires.py`) -- Anomaly and red flag detection
- `dev/storage/tagging/hooks/outcome_tagger.py` (CREATE) -- Outcome tags requiring cross-reference logic
- `dev/storage/tagging/rules.yaml` (MODIFY) -- Update hooks section to reference new modules

**Hook 1: `session_profiler.py`** -- Covers dimensions: session, token, thinking, tool, model

Tags produced (~30):
- `session:exploration-heavy`, `session:edit-heavy`, `session:creation-heavy`
- `session:bash-heavy`, `session:mcp-heavy`, `session:search-heavy`, `session:delegation-heavy`
- `session:interactive`, `session:one-shot`, `session:multi-session`, `session:long`, `session:short`
- `token:input-heavy`, `token:output-heavy`, `token:cache-efficient`, `token:cache-unused`, `token:total-heavy`, `token:total-light`
- `thinking:heavy`, `thinking:none`, `thinking:extended`
- `tool:read-dominant`, `tool:edit-dominant`, `tool:bash-dominant`, `tool:failure-rate-high`, `tool:failure-rate-zero`
- `model:opus`, `model:sonnet`, `model:haiku`, `model:multi-model`

**Hook 2: `signal_detector.py`** -- Covers dimension: signal

Tags produced (~10):
- `signal:backward-transition` (phase regression from entry sequence)
- `signal:bash-error-rate-high` (>10% bash errors, migrated from old hook)
- `signal:cli-misfire` (argument pattern errors)
- `signal:max-tokens-hit` (stop_reason analysis)
- `signal:user-correction` (correction keywords in notes)
- `signal:retry-loop` (same substate visited 3+ times)
- `signal:high-churn` (entries > 2x phases visited)
- `signal:context-compaction` (session continuation detected)
- `signal:sync-error` (iCloud sync failure)

**Hook 3: `outcome_tagger.py`** -- Covers dimension: outcome (complex cases)

Tags produced (~8):
- `outcome:clean-execution` (0 tool failures)
- `outcome:had-retries` (repeated tool calls on same file)
- `outcome:task-completed`, `outcome:task-incomplete`
- `outcome:pr-created`, `outcome:pr-merged`
- `outcome:quality-improved`, `outcome:quality-regressed`, `outcome:quality-stable`

### Wave 4: Tests

**Files:**
- `dev/scripts/sbs/tests/pytest/test_agent_state_taxonomy.py` (EXTEND from Wave 1) -- Add rule evaluation tests, hook unit tests
- `dev/scripts/sbs/tests/pytest/test_tagger_v2.py` (CREATE) -- Integration tests: mock entries through full pipeline, verify correct tags

**Test categories (~20 tests, all evergreen):**
- Taxonomy: uniqueness, naming format, dimension coverage, tag count bounds
- Context: all new fields populated correctly from entry + claude_data
- Rules: each dimension produces expected tags given mock context
- Hooks: session profiler produces correct tags for known session patterns
- Hooks: signal detector flags known anomalies
- Integration: full pipeline mock entry → expected tag set

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
```

---

## Verification

1. `python3 -m sbs archive upload` on a real session produces colon-delimited tags across multiple dimensions
2. Tags include `phase:*`, `skill:*`, `trigger:*` (from declarative rules)
3. Tags include `session:*`, `token:*`, `tool:*` (from hooks)
4. `sbs_tag_effectiveness()` shows new tags with varied frequency distributions (not all noise)
5. All evergreen tests pass
6. Old archive entries retain their original flat `auto_tags` (immutability preserved)
