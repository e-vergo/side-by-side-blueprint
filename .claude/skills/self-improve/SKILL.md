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

All analysis is organized across four pillars:

### 1. User Effectiveness

*How well does the system serve the user?*

| Signal | Indicates |
|--------|-----------|
| Multiple entries in same substate | Retry pattern, unclear requirements |
| Long dialogue chains in alignment | Questions too broad |
| `notes` field with corrections | Misunderstanding that needed fixing |
| Repeated scope clarifications | Initial alignment insufficient |

**Good patterns to preserve:**
- Structured options in questions
- Explicit confirmation before major actions
- Clear summary after each phase

### 2. Claude Execution

*How efficiently does Claude perform tasks?*

| Signal | Indicates |
|--------|-----------|
| High entry count in execution | Excessive iterations |
| `gate_validation` failures | Quality issues not caught early |
| Repeated builds without changes | Cache not leveraged |
| Multiple attempts at same fix | Incorrect diagnosis |

**Good patterns to preserve:**
- Batched tool calls
- Incremental validation
- Pattern reuse from similar tasks

### 3. Alignment Patterns

*How well do user and Claude stay aligned?*

| Signal | Indicates |
|--------|-----------|
| Mismatched `global_state` | State tracking failure |
| Plan file changes mid-execution | Scope creep or poor initial planning |
| Skip from alignment to execution | Planning phase bypassed |
| Multiple skill invocations for one task | Fragmented work |

**Good patterns to preserve:**
- Explicit phase transitions
- Plan approval before execution
- State verification after compaction

### 4. System Engineering

*How well does the tooling support the work?*

| Signal | Indicates |
|--------|-----------|
| Long build times in `quality_scores` | Performance bottleneck |
| Build retries | Flaky infrastructure |
| Validator false positives | Overly strict rules |
| Missing error context | Poor error messages |

**Good patterns to preserve:**
- Incremental builds
- Early validation
- Actionable error messages

---

## Tool Inventory

### Archive Tools

| Tool | Use For |
|------|---------|
| `sbs_archive_state` | Check current global state |
| `sbs_search_entries` | Query entries by tag, project, or trigger |
| `sbs_epoch_summary` | Get aggregated epoch statistics |
| `sbs_context` | Build context blocks for analysis |

### Search Tools

| Tool | Use For |
|------|---------|
| `Grep` | Search for patterns in skill/agent files |
| `Read` | Read specific archive entries or config |
| `Glob` | Find relevant files by pattern |

### Issue Tools

| Tool | Use For |
|------|---------|
| `sbs_issue_create` | Create improvement issues |
| `sbs_issue_list` | Check for duplicate issues |

---

## Analysis Workflow

### Step 1: Gather Data

```python
# Get current epoch summary
epoch = sbs_epoch_summary()

# Search for recent entries
entries = sbs_search_entries(limit=50, trigger="skill")

# Get state context
context = sbs_context(include=["state", "epoch", "recent"])
```

### Step 2: Pattern Detection

For each pillar, scan entries for signals:

1. **Count patterns**: How often does each signal appear?
2. **Cluster by cause**: Group related signals
3. **Score by impact**: Which patterns hurt most?

### Step 3: Generate Findings

Each finding should have:
- **Pillar**: Which area it affects
- **Evidence**: Specific entry IDs showing the pattern
- **Frequency**: How often this occurs
- **Impact**: Estimated cost (time, quality, frustration)
- **Recommendation**: Concrete action to improve

### Step 4: Prioritize

Sort findings by:
1. Impact (high/medium/low)
2. Actionability (can we fix this now?)
3. Scope (narrow fix vs architectural change)

---

## Finding Template

```yaml
finding:
  pillar: "Claude Execution"
  title: "Tool calls not batched in graph debugging"
  evidence:
    - entry_id: "1700000045"
      observation: "3 sequential Read calls that could be parallel"
    - entry_id: "1700000046"
      observation: "Same pattern repeated"
  frequency: "5 occurrences in 12 entries"
  impact: "high - adds ~30s per iteration"
  recommendation: |
    When reading multiple independent files, batch Read
    calls in a single message. The agent system prompt
    should emphasize parallel tool calls for independent
    operations.
  issue_type: "feature"
```

---

## Anti-Patterns

### Analysis Anti-Patterns

- **Vague findings**: "Things could be better" is not actionable
- **Missing evidence**: Every finding needs specific entry IDs
- **Scope creep**: Stick to what's observable in the archive
- **Blame assignment**: Focus on systems, not individuals

### Recommendation Anti-Patterns

- **Unactionable**: "Be more careful" is not a recommendation
- **Architectural rewrites**: Prefer incremental improvements
- **Missing context**: Include what the current behavior is
- **No success criteria**: How do we know if the fix worked?

---

## Output Format

### Discovery Phase Output

```markdown
## Findings Summary

### High Impact (3)
1. [Claude] Tool call batching suboptimal
2. [System] CSS rebuilds not cached
3. [User] Alignment questions too broad

### Medium Impact (2)
4. [Alignment] Recovery after compaction unclear
5. [Claude] Error recovery inconsistent

### Low Impact (1)
6. [System] Verbose logging in builds
```

### Dialogue Phase Output

```markdown
## Refined Finding: Tool Call Batching

**Original observation:**
3 sequential Read calls that could be parallel in graph debugging.

**Root cause:**
Default behavior is sequential tool calls. Agent system prompt
doesn't emphasize batching for independent operations.

**Proposed solution:**
Add explicit guidance to sbs-developer.md about batching
independent tool calls.

**Success criteria:**
Next graph debugging task shows batched Read calls in archive.

**Issue specification:**
- Title: Add tool call batching guidance to sbs-developer agent
- Type: feature
- Body: [full context above]
```

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

