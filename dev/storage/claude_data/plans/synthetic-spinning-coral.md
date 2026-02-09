# Task #101: Allow Parallel Agents During Execution Phase

## Change Summary

Relax the single-agent constraint to allow up to 4 concurrent `sbs-developer` agents during the `/task` execution phase only. All other phases retain strict single-agent policy.

## Files to Modify

### 1. [CLAUDE.md](CLAUDE.md)

**Orchestration Model table (~line 27):**
- Change `Spawns agents (one at a time)` → `Spawns agents (one at a time; up to 4 during /task execution)`

**Single Agent Architecture (~line 29-32):**
- Rewrite to make the constraint phase-aware:
  - Default: one `sbs-developer` at a time
  - Exception: up to 4 concurrent during `/task` execution phase
  - Read-only exploration agents still unlimited alongside

**Spawning Protocol (~line 137-143):**
- Add note that during `/task` execution, multiple agents may be spawned in a single message per the plan

### 2. [.claude/skills/task/SKILL.md](.claude/skills/task/SKILL.md)

**Phase 3: Execution (~line 195-210):**
- Replace the current doc-only exception with a general parallel execution rule:
  - Up to 4 `sbs-developer` agents may run concurrently
  - Plan determines which waves are parallel vs sequential
  - Spawn parallel wave agents in a SINGLE message with multiple Task tool calls
  - Validators run after all parallel agents in a wave complete

**Task Agent Model (~line 498-499):**
- Update "Single-agent constraint" bullet to reflect the execution-phase exception

### 3. [.claude/agents/sbs-developer.md](.claude/agents/sbs-developer.md)

**Agent Parallelism (~line 83-89):**
- Update to reflect that up to 4 instances can run concurrently during `/task` execution
- Collision avoidance is the plan's responsibility

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

## Verification

1. Run evergreen tests: `sbs_run_tests(tier="evergreen")`
2. Grep all three files to confirm no stale "one at a time (architectural invariant)" text remains without the exception clause
