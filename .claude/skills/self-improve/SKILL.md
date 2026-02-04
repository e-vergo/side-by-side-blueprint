---
name: self-improve
description: Recursive self-improvement through archive analysis
version: 1.1.0
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

## Agent Concurrency

`/self-improve` supports multiagent execution:
- **Up to 4 `sbs-developer` agents** may run concurrently during discovery and logging phases
- Useful for: parallel pillar analysis (each agent queries different analysis tools), parallel issue creation
- Collision avoidance: agents must target independent analysis dimensions or issue creation

**Phase-specific guidance:**

| Phase | Concurrency | Use Case |
|-------|-------------|----------|
| discovery | Up to 4 agents | Each agent analyzes a different pillar |
| selection | 1 agent (user interaction) | Interactive selection requires single thread |
| dialogue | 1 agent (user interaction) | Refinement requires single thread |
| logging | Up to 4 agents | Parallel issue creation via `sbs_issue_log` |
| archive | 1 agent | Final summary is sequential |

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

**Step 0: Retrospective Review (FIRST)**

Before running any MCP analysis tools, read all session retrospectives generated since the last self-improve cycle. These are L1 introspections (see Introspection Hierarchy below) and are the primary input for discovery.

1. List files in `dev/storage/archive/retrospectives/` that are newer than the last self-improve cycle
   - Use `sbs_entries_since_self_improve` to find the timestamp boundary
   - Read each retrospective file (they are markdown documents with 5 analysis dimensions)
2. Extract observations, patterns, and specific examples from each retrospective
3. Note recurring themes across multiple retrospectives -- these are high-signal findings
4. Identify items that retrospectives flagged but MCP analysis tools would not surface (e.g., user answer patterns, question quality, alignment gaps observed in-the-moment)

The retrospectives contain observations captured while context was hot -- things that automated analysis of archive metadata cannot reconstruct. Treat them as the highest-fidelity input available.

**Step 1: Automated Analysis**

5. Query recent archive entries via `sbs_search_entries` or `sbs_epoch_summary`
6. Analyze patterns across the four pillars (see below)
7. Generate list of potential improvements (combining retrospective insights with MCP tool findings)
8. Score findings by impact and actionability

### Per-Pillar Minimum Requirement

Discovery is **not complete** until at least 1 finding exists for each pillar:
- [ ] Pillar 1 (User Effectiveness): Use `sbs_user_patterns()` + `sbs_successful_sessions()`
- [ ] Pillar 2 (Claude Execution): Use `sbs_successful_sessions()` + `sbs_comparative_analysis()`
- [ ] Pillar 3 (Alignment Patterns): Use `sbs_comparative_analysis()`
- [ ] Pillar 4 (System Engineering): Use `sbs_system_health()`

If a pillar genuinely has zero findings after querying all relevant tools, document the absence explicitly:
"Pillar X: No findings. Queried [tool names]. Archive data insufficient for this pillar."

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
1. Infer labels from the finding (see Finding-to-Label Mapping below)
2. Create issue via `sbs_issue_log`:
   - Title: Clear, actionable description
   - Body: Context from dialogue, recommended approach
   - Labels: `["origin:self-improve", ...inferred labels]` (`origin:agent` and `ai-authored` are auto-added by the tool)
3. Track created issue numbers

Example call:
```python
sbs_issue_log(
    title="Add tool call batching guidance to sbs-developer agent",
    body="...",
    labels=[
        "origin:self-improve",
        "feature:enhancement",
        "area:devtools:skills",
        "pillar:claude-execution",
        "impact:performance",
        "friction:slow-feedback",
    ]
)
```

### Output

List of created issue numbers with URLs.

### Finding-to-Label Mapping

Every issue created by `/self-improve` includes:

**Always present:**
- `origin:self-improve`
- `ai-authored`

**Type label** -- inferred from finding content:

| Signal | Label |
|--------|-------|
| severity: high + category contains "error"/"failure"/"broken" | `bug:functional` |
| category contains "build"/"compile"/"lake" | `bug:build` |
| category contains "data"/"ledger"/"manifest" | `bug:data` |
| category contains "visual"/"render"/"css" | `bug:visual` |
| recommendation contains "add"/"implement"/"create" (new capability) | `feature:new` |
| recommendation contains "improve"/"enhance"/"optimize" | `feature:enhancement` |
| recommendation contains "connect"/"integrate"/"bridge" | `feature:integration` |
| recommendation contains "investigate"/"debug"/"profile" | `investigation` |
| recommendation contains "document"/"clarify" | `housekeeping:docs` |
| recommendation contains "clean"/"remove"/"simplify" | `housekeeping:cleanup` |
| Default | `housekeeping:tooling` |

**Area label** -- inferred from finding category and evidence (entry IDs link to repos):
- Map to the most specific `area:sbs:*`, `area:devtools:*`, or `area:lean:*` label
- When uncertain, prefer the broader area (e.g., `area:devtools:cli` over `area:devtools:gates`)

**Pillar label** -- direct mapping from `finding.pillar`:

| Pillar | Label |
|--------|-------|
| User Effectiveness | `pillar:user-effectiveness` |
| Claude Execution | `pillar:claude-execution` |
| Alignment Patterns | `pillar:alignment-patterns` |
| System Engineering | `pillar:system-engineering` |

**Impact labels** (optional, multi-select) -- inferred from finding content:
- Performance-related findings -> `impact:performance`
- Visual/UI findings -> `impact:visual`
- Developer workflow findings -> `impact:dx`
- Data quality findings -> `impact:data-quality`
- Alignment-related findings -> `impact:alignment`

**Friction labels** (optional) -- inferred from finding description keywords:

| Keyword Pattern | Label |
|-----------------|-------|
| "compaction"/"context lost"/"state recovery" | `friction:context-loss` |
| "misunderstanding"/"different understanding" | `friction:alignment-gap` |
| "missing tool"/"no way to"/"needed capability" | `friction:tooling-gap` |
| "slow"/"wait"/"rebuild"/"iteration time" | `friction:slow-feedback` |
| "manual"/"by hand"/"should be automated" | `friction:manual-step` |
| "submodule"/"cross-repo"/"dependency chain" | `friction:cross-repo` |
| "state confusion"/"orphaned"/"stale state" | `friction:state-confusion` |
| "noise"/"false positive"/"buried" | `friction:signal-noise` |
| "repeated"/"duplicate"/"same work again" | `friction:repeated-work` |
| "no data"/"not captured"/"missing metrics" | `friction:missing-data` |
| "too many"/"cognitive load"/"overwhelm" | `friction:cognitive-load` |

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

1. Write self-improvement summary document (L2 introspection):
   - **Path:** `dev/storage/archive/summaries/<entry-id>.md`
   - **Content:** A structured markdown document synthesizing observations across all retrospectives (L1) read during discovery, combined with MCP analysis findings. Must include:
     - **Retrospectives reviewed:** Count and entry IDs
     - **Cross-session patterns:** Themes that appeared in multiple retrospectives
     - **Per-pillar synthesis:** What the combined L1 + automated analysis revealed for each pillar
     - **Behavioral observations:** Longer-term patterns visible only when viewing multiple sessions together (e.g., how user communication style evolved, recurring alignment gaps, tool usage trends)
     - **Findings logged:** Issue numbers and titles
     - **Recommendations for next cycle:** What the next self-improve should pay attention to
   - This document is the L2 introspection -- it observes patterns across L1 documents that no single retrospective could see
2. Generate cycle summary:
   - Findings discovered: N
   - Findings selected: M
   - Issues created: K
   - Issue numbers: [#X, #Y, #Z]
   - Summary document path
3. Archive with summary data
4. Clear global state

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

## Introspection Hierarchy

Self-improvement operates on a hierarchy of introspection levels:

| Level | Name | Generated By | Stored At | Observes |
|-------|------|-------------|-----------|----------|
| L1 | Session Retrospective | `/update-and-archive` (Part -1) | `dev/storage/archive/retrospectives/<id>.md` | Single session: user patterns, alignment gaps, plan execution |
| L2 | Self-Improvement Summary | `/self-improve` (Phase 5: Archive) | `dev/storage/archive/summaries/<id>.md` | Multiple L1 docs: cross-session patterns, behavioral trends |
| L3 | Meta-Improvement Analysis | `/introspect 3` | `dev/storage/archive/meta-summaries/L3-<id>.md` | Multiple L2 docs: skill evolution, recurring friction, intervention effectiveness |
| L(N) | Higher-Order Analysis | `/introspect <N>` (N >= 4) | `dev/storage/archive/meta-summaries/L<N>-<id>.md` | Multiple L(N-1) docs: structural insights across improvement cycles |

**Key design principle:** Each level reads the outputs of the level below. L2 reads all L1 documents since the last self-improve cycle. L3 reads all L2 documents since the last L3 cycle via `/introspect 3`.

**Why this matters:** Single-session retrospectives (L1) capture observations while context is hot but cannot see cross-session patterns. The self-improvement summary (L2) synthesizes across sessions and can identify trends invisible to any single retrospective -- e.g., "the user has answered the same type of question 5 times across 3 sessions, suggesting a documentation gap."

As the project grows, higher levels emerge naturally. The hierarchical structure ensures each level adds genuine observational power rather than just repeating lower-level findings.

---

## Tool Inventory

### Archive Tools

| Tool | Use For |
|------|---------|
| `sbs_archive_state` | Check current global state |
| `sbs_search_entries` | Query entries by tag, project, or trigger |
| `sbs_epoch_summary` | Get aggregated epoch statistics |
| `sbs_context` | Build context blocks for analysis |

### Analysis Tools

| Tool | Use For | Pillars |
|------|---------|---------|
| `sbs_analysis_summary` | Overall archive statistics and basic findings | All |
| `sbs_entries_since_self_improve` | Entries since last self-improve cycle | All |
| `sbs_successful_sessions` | Mine completed tasks, clean execution, high quality | 1, 2 |
| `sbs_comparative_analysis` | Approved vs rejected plans, discriminating features | 2, 3 |
| `sbs_system_health` | Build metrics, quality coverage, tag noise | 4 |
| `sbs_user_patterns` | Alignment efficiency, issue-driven patterns | 1 |
| `sbs_skill_stats` | Per-skill lifecycle metrics (count, rate, duration, failures) | 1, 2 |
| `sbs_phase_transition_health` | Phase transition patterns and anomalies | 2, 3 |
| `sbs_interruption_analysis` | User correction/redirection detection | 1, 3 |
| `sbs_gate_failures` | Gate validation failure analysis | 4 |
| `sbs_tag_effectiveness` | Auto-tag signal-to-noise ratio | 4 |

### Search Tools

| Tool | Use For |
|------|---------|
| `Grep` | Search for patterns in skill/agent files |
| `Read` | Read specific archive entries or config |
| `Glob` | Find relevant files by pattern |

### Issue Tools

| Tool | Use For |
|------|---------|
| `sbs_issue_log` | Create improvement issues (preferred -- auto-populates context) |
| `sbs_issue_create` | Create issues when manual label control needed |
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
  labels:
    - "origin:self-improve"
    - "ai-authored"
    - "feature:enhancement"
    - "area:devtools:mcp"
    - "pillar:claude-execution"
    - "impact:performance"
    - "friction:slow-feedback"
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
| `discovery` | Re-read retrospectives, re-query archive, regenerate findings |
| `selection` | Show findings again, re-prompt for selection |
| `dialogue` | Check which findings were already refined, continue with remaining |
| `logging` | Check which issues were created, create remaining |
| `archive` | Re-generate summary document (L2), complete archival |

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

Issues created by `/self-improve` use the enriched label taxonomy defined in
`dev/storage/labels/taxonomy.yaml`. Every issue includes `origin:self-improve`
and `ai-authored`, plus labels from the type, area, pillar, impact, and friction
dimensions as inferred from the finding content (see Finding-to-Label Mapping
in Phase 4 above).

The old `label`/`area` parameters on `sbs_issue_create` are superseded by
the `labels` list parameter, which accepts any label name from the taxonomy.

