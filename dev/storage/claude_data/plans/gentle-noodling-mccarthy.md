# Task #48: Gated Environment Awareness in sbs-developer.md

## Summary

Add a generic behavioral principle to the `sbs-developer` agent prompt that makes it aware of and responsive to the gated workflow environment it operates within.

## Change

**File:** `.claude/agents/sbs-developer.md`

**Location:** Insert new `## Gated Environment` section between line 8 (opening description) and line 10 (`## Project Purpose`). This is the first thing the agent reads after learning what it is.

**Content principles:**
- The agent operates within a structured, phased workflow controlled by global state
- Global state tags (queryable via `sbs_archive_state`) define what's active
- The agent MUST check its context before taking action
- Phase constrains behavior: e.g., alignment phase = no file writes; planning = no implementation
- Trust orchestrator-provided context; verify via MCP when uncertain or on cold start
- Generic framing -- applies to any skill using global state, not /task-specific

**Approximate section (~15-20 lines):**
- Short principle statement
- Behavioral rules (what to do, what not to do)
- How to check context (MCP tool reference)
- Phase-action mapping table (generic, not exhaustive)

## Execution

Single `sbs-developer` agent:
1. Insert the new section into `sbs-developer.md`
2. No other files modified

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

## Verification

1. Run evergreen tests: `sbs_run_tests(tier="evergreen")`
2. Verify file is valid markdown (no syntax issues)
3. Confirm insertion is correctly placed (before `## Project Purpose`)
