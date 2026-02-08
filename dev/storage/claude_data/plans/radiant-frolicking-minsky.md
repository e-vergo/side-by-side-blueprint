# Plan: #133 + #134 — Improvement Capture Tool & /task crush

## Overview

Two independent features sharing a single task branch. No file overlap between them.

- **#133**: New MCP tool `sbs_improvement_capture` — lightweight archive entry creation for mid-session improvement observations
- **#134**: New `/task crush` invocation pattern — batch issue resolution pre-loader in SKILL.md

---

## Wave 1: #133 — `sbs_improvement_capture` MCP Tool (Agent 1)

### Files Modified

| File | Change |
|------|--------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | Add `ImprovementCaptureResult` model |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | Add `sbs_improvement_capture` tool function |
| `dev/storage/tagging/agent_state_taxonomy.yaml` | Add `improvement` tag dimension |

### Tool Design

```python
sbs_improvement_capture(
    observation: str,          # User's exact words / the improvement idea
    category: Optional[str],   # "process" | "interaction" | "workflow" | "tooling" | "other"
)
```

**Returns:** `ImprovementCaptureResult(success, entry_id, tags, error)`

### Implementation — Lightweight Path

1. `load_archive_index()` to get current index and global_state
2. Create `ArchiveEntry` directly:
   - `entry_id`: `str(int(time.time()))`
   - `created_at`: ISO timestamp
   - `project`: `"SBSMonorepo"` (meta, not project-specific)
   - `trigger`: `"improvement"` (new trigger type — only the CLI enforces choices, not the dataclass)
   - `notes`: the observation text
   - `tags`: `[f"improvement:{category}"]`
   - `global_state`: snapshot of current global_state (preserves session context)
   - `auto_tags`: minimal set — `["trigger:improvement"]` plus current skill/phase tags derived from global_state
3. `index.add_entry(entry)` → `index.save(archive_path)`
4. No claude_data extraction, no iCloud sync, no git push — sub-second

### Taxonomy Addition

New dimension `improvement` in `agent_state_taxonomy.yaml`:

```yaml
improvement:
  description: "Improvement opportunity captured mid-session"
  tags:
    - name: "improvement:process"
      description: "Process or workflow improvement idea"
    - name: "improvement:interaction"
      description: "Human-AI interaction pattern improvement"
    - name: "improvement:workflow"
      description: "Workflow automation or friction reduction"
    - name: "improvement:tooling"
      description: "Tooling or infrastructure improvement"
    - name: "improvement:other"
      description: "Uncategorized improvement observation"
```

### Retrieval

No new query tool. Use existing `sbs_search_entries(tags=["improvement:process"])` or filter by `trigger: "improvement"`.

---

## Wave 1: #134 — `/task crush` (Agent 2, parallel)

### Files Modified

| File | Change |
|------|--------|
| `.claude/skills/task/SKILL.md` | Add crush invocation pattern and workflow |

### Invocation Pattern

Add fourth row to the invocation table:

| Pattern | Behavior |
|---------|----------|
| `/task crush` | Batch issue resolution — loads all open issues, proposes triage plan |
| `/task crush #1 #5 #12` | Same, but scoped to specified issues |

### Crush Workflow (added as new section in SKILL.md)

When args start with `crush`:

1. **Pre-load issues:**
   - Call `sbs_issue_summary()` to get all open issues with metadata
   - If specific issue numbers follow `crush`, filter to those
   - Otherwise, operate on all open issues

2. **Gather oracle context (parallel):**
   - Spawn up to 4 read-only Explore agents, each taking a batch of issues
   - Each agent calls `sbs_oracle_query` and reads relevant files for its batch
   - Each reports back: issue number, affected files, estimated complexity (trivial/moderate/significant), recommended wave type

3. **Propose triage plan:**
   - Present issues grouped by wave type (direct closure / bug fix / documentation / code change)
   - For each issue: title, age, complexity estimate, what needs to happen
   - Ask user to approve, modify, or exclude specific issues
   - Use AskUserQuestion with multi-select for inclusion

4. **On approval:** Transition to normal `/task` planning with all selected issues as `issue_refs`. The existing triage wave structure (Wave 0-3) applies.

### Argument Parsing

The `crush` keyword is detected before the description fallthrough. Remaining args after `crush` are parsed for `#N` issue references. Examples:
- `/task crush` → all open issues
- `/task crush #133 #134` → only issues 133 and 134

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

No quality validators needed — no visual/CSS changes.

---

## Verification

1. **#133:** Restart MCP server, call `sbs_improvement_capture(observation="test idea", category="process")`, verify entry appears in `archive_index.json` with correct tags. Verify `sbs_search_entries(tags=["improvement:process"])` returns the entry.

2. **#134:** Read the updated SKILL.md and verify the crush section is internally consistent with the existing invocation patterns and triage wave structure.

3. **Tests:** Run `sbs_run_tests(tier="evergreen")` — all must pass.
