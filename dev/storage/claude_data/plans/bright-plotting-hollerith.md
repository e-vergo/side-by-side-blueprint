# Plan: Grab-Bag Improvements Workflow

## Overview

Add "grab-bag" mode to the existing `/execute` skill, enabling user-led brainstorming sessions that produce custom rubrics with metric-specific thresholds. Establish `archive/README.md` as the master hub for monorepo tooling.

---

## Alignment Summary

| Decision | Choice |
|----------|--------|
| Trigger | `/execute --grab-bag` or `/execute grab-bag` |
| Hub location | Keep `archive/README.md`, add prominent header |
| Rubric storage | JSON + CLI renderer + auto-generated markdown |
| Finalization | Always invoke /update-and-archive |
| Brainstorm style | User-led, Claude as active collaborative follower |
| Scope | Conversation-driven, no hard limit |
| Template | Fully custom categories from brainstorm |
| Thresholds | Metric-specific per rubric |

---

## Phase 1: Rubric Infrastructure

### Step 1: Rubric Data Model

**Create:** `scripts/sbs/rubric.py` (~200 lines)

```python
@dataclass
class RubricMetric:
    id: str                    # e.g., "css-alignment-score"
    name: str                  # Human-readable name
    description: str           # What this measures
    category: str              # User-defined from brainstorm
    threshold: float           # Minimum acceptable
    weight: float              # 0.0-1.0
    scoring_type: str          # "pass_fail", "percentage", "score_0_10"

@dataclass
class Rubric:
    id: str                    # UUID or slugified name
    name: str
    created_at: str
    categories: list[str]      # From brainstorm
    metrics: list[RubricMetric]

@dataclass
class RubricEvaluation:
    rubric_id: str
    evaluated_at: str
    results: dict[str, MetricResult]
    overall_score: float
    passed: bool
```

**Validation:** Unit tests pass

---

### Step 2: Rubric CLI Commands

**Modify:** `scripts/sbs/cli.py` (add rubric command group, ~50 lines)

**Create:** `scripts/sbs/rubric_cmd.py` (~250 lines)

| Command | Purpose |
|---------|---------|
| `sbs rubric create --from-json FILE` | Create from JSON |
| `sbs rubric show ID [--format json\|markdown]` | Display rubric |
| `sbs rubric list` | List all rubrics |
| `sbs rubric evaluate ID --project NAME` | Run evaluation |
| `sbs rubric delete ID [--force]` | Delete rubric |

**Validation:** `sbs rubric --help` shows subcommands, basic operations work

---

### Step 3: Rubric Storage

**Create directory:** `archive/rubrics/`

**File structure:**
- `archive/rubrics/{id}.json` - Primary storage
- `archive/rubrics/{id}.md` - Auto-generated human-readable
- `archive/rubrics/index.json` - Rubric index

**Validation:** Create rubric, verify both JSON and markdown appear

---

### Step 4: ArchiveEntry Integration

**Modify:** `scripts/sbs/archive/entry.py` (~20 lines)

```python
@dataclass
class ArchiveEntry:
    # ... existing fields ...
    rubric_id: Optional[str] = None
    rubric_evaluation: Optional[dict] = None
```

**Validation:** Existing entries still load, new entries can include rubric data

---

## Phase 2: Skill Modification

### Step 5: Update /execute SKILL.md

**Modify:** `.claude/skills/execute/SKILL.md` (~150 lines added)

Add grab-bag mode documentation:

```markdown
## Grab-Bag Mode

### Invocation
`/execute --grab-bag` or `/execute grab-bag`

### Phase 1: Brainstorm (User-Led)
- User proposes ideas, Claude asks clarifying questions
- Claude identifies patterns and suggests related improvements
- Continue until user signals "ready for metrics"

### Phase 2: Metric Alignment
- Group improvements into natural categories
- For each category, identify 2-4 measurable metrics
- User approves metric definitions

### Phase 3: Rubric Creation
- Convert metrics to RubricMetric objects with thresholds
- Assign weights, present for approval
- Save to archive/rubrics/{id}.json

### Phase 4: Plan Mode
- One task per metric in rubric
- Final task: human review step
- Present plan for approval

### Phase 5: Execution Loop
- Execute agents sequentially
- After each metric's task, evaluate that metric
- Track progress in rubric evaluation

### Phase 6: Finalization
- Complete rubric evaluation
- Record in archive entry
- Invoke /update-and-archive
```

**Validation:** Skill documentation renders correctly

---

### Step 6: Rubric Validator

**Create:** `scripts/sbs/validators/rubric_validator.py` (~150 lines)

```python
@register_validator
class RubricValidator(BaseValidator):
    name = "rubric"
    category = "code"

    def set_rubric(self, rubric: Rubric) -> None: ...
    def validate(self, context: ValidationContext) -> ValidatorResult: ...
```

**Validation:** `registry.get("rubric")` returns instance

---

## Phase 3: Documentation Cascade

### Step 7: Master Hub Update

**Modify:** `archive/README.md` (~100 lines added)

New structure:
```markdown
# Side-by-Side Blueprint Archive & Tooling Hub

> **Central reference for all monorepo tooling.**
> All repository READMEs link here.

## Quick Reference
[Command table]

## Rubric System
[New section]

## Archive System
[Existing, reorganized]

## Compliance System
[Existing, reorganized]
```

**Validation:** All links valid, renders correctly

---

### Step 8: Repository README Updates

**Modify:** 10 repository READMEs (add ~5 lines each)

Add to each:
```markdown
## Tooling

See [`archive/README.md`](../archive/README.md) for build commands,
screenshot capture, compliance, archive management, and custom rubrics.
```

**Repositories:**
1. subverso/README.md
2. verso/README.md
3. LeanArchitect/README.md
4. Dress/README.md
5. Runway/README.md
6. SBS-Test/README.md
7. General_Crystallographic_Restriction/README.md
8. PrimeNumberTheoremAnd/README.md
9. dress-blueprint-action/README.md
10. README.md (main)

**Validation:** All links resolve

---

### Step 9: Agent and Core Docs Update

**Modify:** `.claude/agents/sbs-developer.md` (~20 lines)

Add tooling reference section pointing to archive/README.md

**Modify:** `CLAUDE.md` (~50 lines)

Add:
- Tooling Hub reference
- Grab-bag mode documentation in skills section

**Validation:** Documentation consistent

---

## Phase 4: Integration

### Step 10: Unified Ledger Integration

**Modify:** `scripts/sbs/ledger.py` (~30 lines)

```python
@dataclass
class UnifiedLedger:
    # ... existing ...
    rubric_evaluations: list[dict] = field(default_factory=list)

    def add_rubric_evaluation(self, evaluation: RubricEvaluation): ...
```

**Validation:** Ledger saves/loads with rubric data

---

### Step 11: /update-and-archive Awareness

**Modify:** `.claude/skills/update-and-archive/SKILL.md` (~20 lines)

Add rubric context handling when invoked from grab-bag mode.

**Validation:** Skill documentation accurate

---

### Step 12: Human Review + Test

**Orchestrator Task:** Review all changes, run integration test

1. Create test rubric via CLI
2. Verify storage in archive/rubrics/
3. Run evaluation against SBSTest
4. Verify archive entry links to rubric
5. Verify all documentation links work

**Validation:** End-to-end workflow functions

---

## Files Summary

### New Files (3)
| File | Lines |
|------|-------|
| `scripts/sbs/rubric.py` | ~200 |
| `scripts/sbs/rubric_cmd.py` | ~250 |
| `scripts/sbs/validators/rubric_validator.py` | ~150 |

### Modified Files (15)
| File | Lines Changed |
|------|---------------|
| `scripts/sbs/cli.py` | ~50 |
| `scripts/sbs/archive/entry.py` | ~20 |
| `scripts/sbs/ledger.py` | ~30 |
| `.claude/skills/execute/SKILL.md` | ~150 |
| `.claude/skills/update-and-archive/SKILL.md` | ~20 |
| `.claude/agents/sbs-developer.md` | ~20 |
| `archive/README.md` | ~100 |
| `CLAUDE.md` | ~50 |
| 10 repository READMEs | ~5 each |

### New Directory
```
archive/rubrics/
  index.json
  {id}.json
  {id}.md
```

**Total:** ~600 new lines, ~500 modified lines

---

## Verification

### Per-Step
- Unit tests for rubric data model
- CLI command execution
- File existence checks

### End-to-End
```bash
# Create rubric
sbs rubric create --from-json test-rubric.json

# List rubrics
sbs rubric list

# Show rubric (markdown)
sbs rubric show test-rubric --format markdown

# Evaluate
sbs rubric evaluate test-rubric --project SBSTest

# Verify archive entry
sbs archive show <latest>
```

### Documentation
- All internal links resolve
- Markdown renders correctly
- Help text accurate

---

## Dependencies

- Existing validator infrastructure (`scripts/sbs/validators/`)
- Existing archive system (`scripts/sbs/archive/`)
- Existing CLI framework (`scripts/sbs/cli.py`)
- Existing `/update-and-archive` skill
