---
name: self-improve
description: Recursive self-improvement through archive analysis
version: 1.0.0
---

# /self-improve - Recursive Self-Improvement

Analyze archived Claude sessions to identify patterns and capture actionable improvements.

---

## Invocation

| Pattern | Behavior |
|---------|----------|
| `/self-improve` | Full interactive cycle through all phases |
| `/self-improve --dry-run` | Discovery only, no issue creation |

---

## Mandatory Archive Protocol

**This is not optional. Violations break the skill contract.**

### First Action on Invocation

Before doing ANYTHING else:

1. Call `sbs_archive_state()` via MCP
2. Check `global_state` field:
   - `null` -> Fresh run, proceed to discovery
   - `{skill: "self-improve", substate: X}` -> Resume from substate X
   - `{skill: "other", ...}` -> Error: state conflict, do NOT proceed

### Phase Transitions

Every phase change MUST execute:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"self-improve","substate":"<phase>"}' \
  --state-transition phase_start
```

Phases: `discovery` -> `selection` -> `dialogue` -> `logging` -> `archive`

### Ending the Skill

Final archive call clears state:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill \
  --state-transition phase_end
```

This sets `global_state` to `null`, returning system to idle.

---

## Phase 1: Discovery

**Purpose:** Query archive, identify patterns, generate findings.

### Entry Transition

```bash
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"self-improve","substate":"discovery"}' \
  --state-transition phase_start
```

### Actions

1. Query recent archive entries via `sbs_search_entries` or `sbs_epoch_summary`
2. Analyze patterns across the four pillars (see below)
3. Generate list of potential improvements
4. Score findings by impact and actionability

### Output

A structured list of findings, each with:
- **Pillar**: Which pillar it relates to
- **Finding**: What was observed
- **Recommendation**: Proposed action
- **Impact**: Expected benefit (high/medium/low)

---

## Phase 2: Selection

**Purpose:** Present summary, user picks items for refinement.

### Entry Transition

```bash
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"self-improve","substate":"selection"}' \
  --state-transition phase_start
```

### Actions

1. Present findings in GUI-style format with checkbox options:
   ```
   Select findings to refine (comma-separated numbers, or 'all'):

   [ ] 1. [User] Alignment questions could be more structured
   [ ] 2. [Claude] Tool call batching suboptimal in graph work
   [ ] 3. [Alignment] Recovery semantics unclear after compaction
   [ ] 4. [System] Build caching not leveraged for incremental work
   ```

2. Wait for user selection

### Output

List of selected finding indices for dialogue phase.

---

## Phase 3: Dialogue

**Purpose:** Refine each selected finding via discussion.

### Entry Transition

```bash
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"self-improve","substate":"dialogue"}' \
  --state-transition phase_start
```

### Actions

For each selected finding:
1. Present the finding with context
2. Ask clarifying questions:
   - Is this accurately characterized?
   - What's the root cause?
   - What would a good solution look like?
3. Refine into actionable issue specification
4. Confirm with user before proceeding

### Output

Refined issue specifications ready for logging.

---

## Phase 4: Logging

**Purpose:** Log confirmed items via `/log` skill.

### Entry Transition

```bash
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"self-improve","substate":"logging"}' \
  --state-transition phase_start
```

### Actions

For each confirmed improvement:
1. Determine issue type (bug, feature, idea)
2. Create issue via `sbs_issue_create`:
   - Title: Clear, actionable description
   - Body: Context from dialogue, recommended approach
   - Label: Appropriate type + `ai-authored` + `self-improve`
3. Track created issue numbers

### Output

List of created issue numbers with URLs.

---

## Phase 5: Archive

**Purpose:** Record cycle completion with summary.

### Entry Transition

```bash
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"self-improve","substate":"archive"}' \
  --state-transition phase_start
```

### Actions

1. Generate cycle summary:
   - Findings discovered: N
   - Findings selected: M
   - Issues created: K
   - Issue numbers: [#X, #Y, #Z]
2. Archive with summary data
3. Clear global state

### Exit Transition

```bash
python3 -m sbs archive upload --trigger skill \
  --state-transition phase_end \
  --issue-refs <comma-separated-issue-numbers>
```

---

## Four Pillars Framework

Self-improvement analysis is organized across four pillars:

### 1. User Effectiveness

*How well does the system serve the user?*

Questions to analyze:
- Were alignment phases thorough enough?
- Did the user have to repeat themselves?
- Were questions asked at the right granularity?
- Was context preserved across compactions?

Signals in archive:
- `notes` field with user corrections
- Multiple entries in same `substate` (retry patterns)
- Long dialogue chains in alignment phase

### 2. Claude Execution

*How efficiently does Claude perform tasks?*

Questions to analyze:
- Were tool calls batched effectively?
- Was unnecessary work performed?
- Were errors recovered gracefully?
- Were patterns reused vs reinvented?

Signals in archive:
- High entry counts in execution phase
- `gate_validation` failures
- Repeated builds without changes

### 3. Alignment Patterns

*How well do user and Claude stay aligned?*

Questions to analyze:
- Were recovery semantics clear after compaction?
- Did substates accurately reflect progress?
- Were plans followed or frequently revised?
- Was scope creep detected early?

Signals in archive:
- `state_transition` patterns
- Plan file changes mid-execution
- Mismatched `global_state` across entries

### 4. System Engineering

*How well does the tooling support the work?*

Questions to analyze:
- Are build times acceptable?
- Is caching leveraged effectively?
- Do validators catch issues early?
- Are error messages actionable?

Signals in archive:
- Timing data in `quality_scores`
- Build retries
- Validator feedback patterns

---

## Recovery Semantics

### Compaction Survival

If context compacts mid-cycle:

1. New context queries `sbs_archive_state()`
2. Reads current `global_state.substate`
3. Resumes from **start** of that substate

### Substate Resume Behavior

| Substate | Resume Action |
|----------|---------------|
| `discovery` | Re-query archive, regenerate findings |
| `selection` | Show findings again, re-prompt for selection |
| `dialogue` | Check which findings were already refined, continue with remaining |
| `logging` | Check which issues were created, create remaining |
| `archive` | Re-generate summary, complete archival |

### State Conflict

If `global_state.skill != "self-improve"`:
- Another skill owns the state
- Do NOT proceed
- Report error: "State conflict: skill '<other_skill>' currently owns global state"
- Wait for user resolution

---

## Dry Run Mode

When invoked with `--dry-run`:
- Execute discovery and selection phases normally
- Skip dialogue, logging, and archive phases
- Report what would have been created
- Do NOT modify any state

---

## Example Session

```
User: /self-improve

Claude: [Checking archive state...]
        Global state is null. Starting fresh discovery.

[Phase 1: Discovery]
Analyzing 47 entries from the current epoch...

Found 6 potential improvements:

Claude: [Phase 2: Selection]
Select findings to refine:

[1] [User] Alignment questions often too broad, causing back-and-forth
[2] [Claude] Graph layout debugging took 3x expected iterations
[3] [Alignment] Plan was modified 4 times during single task
[4] [System] Same CSS file rebuilt 12 times without changes

Enter numbers (comma-separated) or 'all': 1, 4

User: 1, 4

Claude: [Phase 3: Dialogue]

Finding 1: Alignment questions too broad
- Observed in entries: 1700000045, 1700000046, 1700000047
- Pattern: "What would you like to do?" followed by 3+ clarifications

Is this accurately characterized? Would structured options help?

User: Yes, I'd prefer numbered options with clear scope

Claude: Refined recommendation:
  Title: Add structured options to alignment phase questions
  Body: When asking for task clarification, provide 3-5 specific
        options with defined scope rather than open-ended questions.
  Type: feature

Proceed with this specification? [Y/n]

User: y

[... continues through all selected findings ...]

Claude: [Phase 4: Logging]
Created issues:
- #47: Add structured options to alignment phase questions
- #48: Cache CSS compilation during incremental builds

[Phase 5: Archive]
Cycle complete:
- Findings discovered: 6
- Findings refined: 2
- Issues created: 2

State cleared. Returning to idle.
```

---

## Error Handling

| Error | Response |
|-------|----------|
| No archive entries found | Report "No entries in current epoch" and exit cleanly |
| MCP tool fails | Report error, do not proceed, keep state for retry |
| User cancels mid-dialogue | Archive partial progress, clear state |
| Issue creation fails | Report failure, offer retry or skip |

---

## Labels

Issues created by this skill use:
- Type label: `bug`, `feature`, or `idea`
- `ai-authored`: Indicates AI authorship
- `self-improve`: Indicates origin from self-improvement analysis

---

## Agent

This skill uses the `sbs-improver` agent for analysis work. See `.claude/agents/sbs-improver.md`.
