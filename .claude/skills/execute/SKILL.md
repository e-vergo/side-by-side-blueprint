---
name: execute
description: General-purpose agentic task execution with validation
disable-model-invocation: true
version: 2.0.0
---

# /execute - Agentic Task Workflow

## Invocation

User triggers `/execute` with a task description.

## Phase 1: Alignment (Q&A)

Claude asks clarifying questions until user explicitly signals readiness:
- "ready to plan"
- "let's plan"
- "proceed to planning"

Questions should cover:
- Task scope and boundaries
- Success criteria
- Validation requirements
- Affected repositories

## Phase 2: Planning

User moves chat to plan mode. Claude presents:
1. Task breakdown into waves/agents
2. Validator specifications per wave
3. Success criteria mapped to ledger checks
4. Estimated scope (files, repos, complexity)

## Phase 3: Execution

Fully autonomous:
1. Execute agents sequentially (one at a time) for code changes
2. **Exception: Documentation-only waves** - Agents can run in parallel when:
   - No code is being modified (only README/docs)
   - No collision risk between agents
   - Spawn all wave agents in a SINGLE message with multiple Task tool calls
3. After each agent/wave, run specified validators
4. If validation fails:
   - Retry failed agent once
   - If retry fails, pause for re-approval
5. Continue until all agents complete

## Phase 4: Finalization

1. Run full validation suite
2. Update unified ledger
3. Generate summary report
4. Commit final state

## Phase 5: Documentation Cleanup (MANDATORY)

**Execution is NOT complete until this phase runs.**

Invoke `/update-and-archive` as the final step. This:
1. Refreshes all repository READMEs in parallel waves
2. Synchronizes core documentation (ARCHITECTURE.md, CLAUDE.md, GOALS.md, README.md)
3. Ensures documentation reflects the changes made during execution

This phase cannot be skipped. The `/execute` skill is considered incomplete until `/update-and-archive` completes successfully.

## Validators

Specify validators in plan:

```
validators:
  - visual: [dashboard, dep_graph, chapter]
  - timing: true
  - git_metrics: true
  - code_stats: [loc, file_counts]
```

Available validators:
- `visual-compliance` - AI vision validation of screenshots (category: visual)
- `timing` - Build phase timing metrics (category: timing)
- `git-metrics` - Commit/diff tracking (category: git)
- `code-stats` - LOC and file counts (category: code)

## Error Handling

- Agent failure: retry once, then pause
- Validation failure: pause for re-approval with findings
- Build failure: halt, report, wait for user

## Summary Report

After completion:
- Agents spawned: N
- Validation passes: X/Y
- Build metrics: timing, commits, diffs
- Failures: list with causes

## Implementation Notes

All builds must go through `python build.py` (never skip commits/pushes). The unified ledger at `archive/unified_ledger.json` tracks all metrics across builds.

To run validators programmatically:
```python
from sbs.validators import discover_validators, registry, ValidationContext

discover_validators()
validator = registry.get('visual-compliance')
result = validator.validate(context)
```
