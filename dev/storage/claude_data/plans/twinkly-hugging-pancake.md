# Plan: #96 + #105 + #107 — Autonomous Logging, Oracle-First, Multiagent Extension

## Issues

| # | Title | Scope |
|---|-------|-------|
| 96 | `sbs_issue_log` MCP tool for autonomous agent logging | Code (MCP fork) |
| 105 | Oracle-first agent behavior mandate | Doc (sbs-developer.md) |
| 107 | Extend multi-agent concurrency to all /task phases + /self-improve | Doc (4 files) |

## Wave 1: MCP Tool (1 agent, direct commit to fork)

**Agent A1** — `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/`

### sbs_models.py
- Add `IssueLogResult` model after `IssueCreateResult` (~line 419)
- Fields: `success`, `number`, `url`, `context_attached`, `error`

### sbs_tools.py
- Import `IssueLogResult`
- Add `sbs_issue_log` tool after `sbs_issue_create` (~line 1703)
- **Implementation:**
  - Params: `title` (required), `body` (optional), `labels` (optional)
  - Internally calls `load_archive_index()` for context (global_state, epoch entries, last epoch timestamp)
  - Appends auto-populated context block to body
  - Always includes `origin:agent` + `ai-authored` labels
  - Uses same `gh issue create` subprocess pattern as `sbs_issue_create`
  - Archive failures are non-fatal: `context_attached=False`, issue still created
- **Commit directly** to fork (per repo strategy table)

### Gate
```yaml
gates:
  tests: all_pass
  test_tier: evergreen
```
Smoke test: call `sbs_issue_log` with test title, verify creation, close test issue.

---

## Wave 2: Documentation Refresh (4 parallel agents, feature branch + PR)

### Agent B1: `CLAUDE.md`
1. **Orchestration Model (lines 29-33):** Replace phase-restricted concurrency with universal rule — up to 4 agents during all `/task` phases and `/self-improve`
2. **Spawning Protocol (~line 146):** Remove "(execution phase only)" qualifier
3. **Proactive Bug Logging (~line 434):** Replace `/log` reference with `sbs_issue_log` MCP tool
4. **New section: "Multiagent Behavior Definition"** after Proactive Bug Logging:
   - **What constitutes multiagent:** Multiple `sbs-developer` agents writing files and/or interacting with archival system concurrently. Read-only exploration agents don't count.
   - **When allowed:** All `/task` phases, `/self-improve`, up to 4 concurrent, non-overlapping files
   - **When NOT allowed:** `/log`, `/update-and-archive`, `/oracle`, idle state

### Agent B2: `.claude/agents/sbs-developer.md`
1. **Agent Parallelism (lines 83-89):** Update to all-phase concurrency
2. **New section: "Information Gathering Protocol"** (after line 27): Oracle-first mandate — `sbs_oracle_query` before user questions. User questions reserved for requirements/preferences only.
3. **New section: "Autonomous Issue Logging"** (before EOF): Instructions and example for `sbs_issue_log` usage

### Agent B3: `.claude/skills/task/SKILL.md`
1. **Phase 3: Execution (~line 200):** Update concurrency to "any phase"
2. **Phases 1, 2, 4:** Add agent concurrency notes to each phase
3. **Phase 3:** Add autonomous bug logging encouragement via `sbs_issue_log`

### Agent B4: `.claude/skills/self-improve/SKILL.md`
1. **New section: "Agent Concurrency"** (after line 59): Phase-specific concurrency table (discovery/logging: up to 4, selection/dialogue/archive: 1)
2. **Issue Tools table (~line 408):** Prefer `sbs_issue_log` over `sbs_issue_create`
3. **Phase 4: Logging (~line 178):** Replace `sbs_issue_create` with `sbs_issue_log` in example

### Gate
```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

---

## PR Strategy

| Repo | Strategy | Agents |
|------|----------|--------|
| `forks/sbs-lsp-mcp` | Direct commit | A1 |
| Main repo | PR: `task/96-105-107-multiagent-logging` | B1-B4 |

Submodule pointer bump for sbs-lsp-mcp included in main repo PR.

## Verification

1. Wave 1: Smoke-test `sbs_issue_log` end-to-end
2. Wave 2: Evergreen tests pass, no regressions
3. All three issues closable after merge
