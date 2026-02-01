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

---

## Grab-Bag Mode

A variant workflow for ad-hoc improvement sessions where scope emerges from brainstorming rather than predefined requirements.

### Invocation

`/execute --grab-bag` or `/execute grab-bag`

### Collaboration Style

**User leads, Claude follows actively.** Enable "head in the clouds, feet firmly on the ground" ideation:
- User drives brainstorming direction
- Claude actively contributes ideas but follows user's lead
- Balance visionary thinking with practical grounding

### Phase 1: Brainstorm (User-Led)

Claude follows the user's lead in identifying improvements:

1. User proposes ideas, Claude asks clarifying questions
2. Claude identifies patterns and suggests related improvements
3. No predefined structure - let ideas flow naturally
4. Continue until user signals "ready for metrics"

**Transition signals:**
- "ready for metrics"
- "let's formalize"
- "time to measure"

### Phase 2: Metric Alignment

Claude and user formalize the brainstorm into measurable metrics:

1. Group improvements into natural categories (user-defined, not predefined)
2. For each category, identify 2-4 measurable metrics
3. Discuss measurement approaches (deterministic vs heuristic, binary vs gradient)
4. User approves metric definitions

**Key principle:** Formal but ad-hoc. No predefined template - derive categories from the brainstorm itself.

### Phase 3: Rubric Creation

Claude creates a formal rubric for user approval:

1. Convert metrics to `RubricMetric` objects with:
   - Unique ID (slugified from name)
   - Threshold (minimum acceptable value)
   - Weight (contribution to overall score, sum to 1.0)
   - Scoring type (pass_fail, percentage, score_0_10)
2. Assign weights based on user priorities
3. Present rubric for user approval
4. On approval, save to `archive/rubrics/{id}.json`
5. Auto-generate markdown at `archive/rubrics/{id}.md`

**CLI integration:**
```bash
sbs rubric show <id> --format markdown  # Human review
sbs rubric list                          # See all rubrics
```

### Phase 4: Plan Mode

Standard planning with rubric integration:

1. Enter plan mode
2. Create one task per metric in rubric
3. Add human review step after metric test implementation
4. Map validator specifications to rubric metrics
5. Present plan for user approval

**Plan structure:**
- Step N: Implement/test metric M (for each metric)
- Step N+1: Human review of metric apparatus
- Step N+2: Execution loop with rubric grading

### Phase 5: Execution Loop

Execute with rubric-based validation:

1. Execute agents sequentially (standard rules apply)
2. After each metric's task, evaluate that metric
3. Track progress: `{metric_id: score, passed: bool}`
4. If metric fails threshold:
   - Offer retry or continue
   - Log finding for summary
5. Continue until all metrics evaluated

**Progress tracking:**
```python
evaluation.results["metric-id"] = MetricResult(
    value=0.85,
    passed=True,
    findings=["Minor issue with X"],
    evaluated_at="2025-01-15T..."
)
```

### Phase 6: Finalization

Always ends with /update-and-archive:

1. Complete rubric evaluation (calculate overall score)
2. Record evaluation in archive entry:
   - `rubric_id` links to rubric
   - `rubric_evaluation` contains results snapshot
3. Generate summary with rubric scores
4. Invoke `/update-and-archive` (mandatory)

### Rubric Persistence

Rubrics persist beyond sessions:

| Action | Command |
|--------|---------|
| View rubric | `sbs rubric show <id>` |
| List all | `sbs rubric list` |
| Reuse rubric | `/execute --rubric <id>` |
| Evolve rubric | Copy JSON, modify, create new |

### Example Workflow

```
User: /execute grab-bag
Claude: What areas would you like to explore for improvements?

User: I've been thinking about the dashboard... [brainstorm]
Claude: [active following, asks questions, suggests related ideas]

User: Ready for metrics
Claude: Based on our discussion, I see three categories:
1. Dashboard clarity (3 metrics)
2. Toggle discoverability (2 metrics)
3. Color consistency (2 metrics)

[Metric alignment dialogue]

User: Approved
Claude: Creating rubric "dashboard-ux-2025-01"...
[Saved to archive/rubrics/dashboard-ux-2025-01.json]

[Plan mode, execution, finalization]
```

### Rubric Storage

```
archive/rubrics/
├── index.json              # Registry of all rubrics
├── {rubric-id}.json        # Rubric definition
├── {rubric-id}.md          # Human-readable (auto-generated)
└── {rubric-id}_eval_*.json # Evaluation results (optional)
```
