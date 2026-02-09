# Implementation Plan: `sbs_question_history` MCP Tool

**Issue:** #204
**Goal:** Build a standalone MCP tool that extracts complete question interaction history in agent-optimized format, establishing the pattern for future analytical tools.

---

## Overview

The new `sbs_question_history` tool will be the first in a pattern of "extract structured high-signal data via DuckDB for agent consumption." It differs from existing question tools:

| Tool | Purpose | Limitation |
|------|---------|-----------|
| `sbs_question_analysis` | Extract interactions with skill correlation | Default limit of 50, uses Python extractors |
| `sbs_question_stats` | Aggregate counts by skill/header/option | No raw interactions, aggregates only |
| **`sbs_question_history`** (NEW) | Export ALL interactions + rich metadata | No artificial limits, comprehensive metadata, pure DuckDB queries |

**Key principle:** The tool does NO intelligence work. It returns structured facts; agents do all analysis/filtering/pattern detection.

---

## Implementation Components

### 1. New Pydantic Models

**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py`

Add after `QuestionStatsResult` (around line 1008):

```python
class QuestionHistoryMetadata(BaseModel):
    """Metadata for question history dataset."""

    total_interactions: int = Field(description="Total AskUserQuestion invocations")
    total_questions: int = Field(description="Total individual questions across all interactions")
    date_range: Optional[Tuple[Optional[str], Optional[str]]] = Field(
        None, description="Earliest and latest timestamps (ISO format)"
    )
    skills_present: List[str] = Field(
        default_factory=list, description="Unique skills during which questions were asked"
    )
    sessions_count: int = Field(description="Unique session files containing questions")
    question_types: Dict[str, int] = Field(
        default_factory=dict, description="Counts: single_select, multi_select"
    )
    header_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Question count per header text"
    )
    skill_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Interaction count per skill"
    )


class QuestionHistoryResult(BaseModel):
    """Result from sbs_question_history - complete question dataset for agent analysis."""

    interactions: List[QuestionInteraction] = Field(
        default_factory=list,
        description="All question interactions matching filters (no artificial limit)"
    )
    metadata: QuestionHistoryMetadata = Field(
        description="Aggregate metadata about the dataset"
    )
```

**Why these fields:**
- `total_interactions` vs `total_questions` - agents need to understand scale (one interaction can have 3 questions)
- `date_range` - temporal context
- `skills_present` - shows where questions are concentrated
- `sessions_count` - sessions searched
- `question_types` - multi-select vs single-select usage patterns
- `header_distribution` - which question categories are most common
- `skill_distribution` - which skills prompt the most questions

---

### 2. DuckDB Layer Method

**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py`

Add after `question_stats()` method (around line 1820):

```python
def question_history(
    self,
    since: Optional[str] = None,
    until: Optional[str] = None,
    skill: Optional[str] = None,
    include_context: bool = False,
) -> QuestionHistoryResult:
    """Extract complete question history for agent-driven analysis.

    Unlike `question_analysis()` which limits to 50 interactions, this returns
    ALL matching data optimized for agent consumption. No intelligence applied -
    agents do all filtering, analysis, and pattern detection.

    Args:
        since: Entry ID or ISO timestamp filter (inclusive)
        until: Entry ID or ISO timestamp filter (inclusive)
        skill: Filter to questions asked during this skill (e.g., "task", "introspect")
        include_context: Include context_before field (can be large, default False)

    Returns:
        QuestionHistoryResult with complete interactions list and rich metadata
    """
    self.ensure_loaded()
    self._ensure_questions_loaded()

    # Reuse existing extraction logic from question_analysis()
    # but remove limit and add comprehensive metadata
    try:
        from sbs.archive.extractor import get_sbs_project_dirs, extract_ask_user_questions
    except ImportError:
        return QuestionHistoryResult(
            interactions=[],
            metadata=QuestionHistoryMetadata(
                total_interactions=0,
                total_questions=0,
                sessions_count=0
            )
        )

    session_files = []
    for project_dir in get_sbs_project_dirs():
        for session_file in project_dir.glob("*.jsonl"):
            session_files.append((session_file.stem, session_file))

    since_dt = _parse_ts(since) if since else None
    until_dt = _parse_ts(until) if until else None

    all_interactions: list[QuestionInteraction] = []
    total_questions = 0
    skills_seen = set()
    header_counts: Counter = Counter()
    skill_counts: Counter = Counter()
    question_type_counts = {"single_select": 0, "multi_select": 0}
    sessions_with_questions = set()

    earliest_ts = None
    latest_ts = None

    for session_id, session_path in session_files:
        raw_interactions = extract_ask_user_questions(session_path)

        for raw in raw_interactions:
            ts = raw.get("timestamp")

            # Apply time filters
            if since_dt and ts:
                try:
                    ts_dt = _parse_ts(ts)
                    if ts_dt and ts_dt < since_dt:
                        continue
                except (ValueError, TypeError):
                    pass
            if until_dt and ts:
                try:
                    ts_dt = _parse_ts(ts)
                    if ts_dt and ts_dt > until_dt:
                        continue
                except (ValueError, TypeError):
                    pass

            # Correlate with skill
            active_skill, active_substate = self._correlate_question_with_skill(ts)

            # Apply skill filter
            if skill and active_skill != skill:
                continue

            # Build interaction
            questions_list = raw.get("questions", [])
            interaction = QuestionInteraction(
                session_id=session_id,
                timestamp=ts,
                questions=questions_list,
                answers=raw.get("answers", {}),
                context_before=raw.get("context_before") if include_context else None,
                skill=active_skill,
                substate=active_substate,
            )
            all_interactions.append(interaction)

            # Gather metadata
            sessions_with_questions.add(session_id)
            if active_skill:
                skills_seen.add(active_skill)
                skill_counts[active_skill] += 1

            for q in questions_list:
                total_questions += 1
                header = q.get("header", "")
                if header:
                    header_counts[header] += 1
                if q.get("multiSelect", False):
                    question_type_counts["multi_select"] += 1
                else:
                    question_type_counts["single_select"] += 1

            # Track date range
            if ts:
                if earliest_ts is None or ts < earliest_ts:
                    earliest_ts = ts
                if latest_ts is None or ts > latest_ts:
                    latest_ts = ts

    # Sort by timestamp descending (most recent first)
    all_interactions.sort(key=lambda i: i.timestamp or "", reverse=True)

    # Build metadata
    metadata = QuestionHistoryMetadata(
        total_interactions=len(all_interactions),
        total_questions=total_questions,
        date_range=(earliest_ts, latest_ts) if earliest_ts else None,
        skills_present=sorted(list(skills_seen)),
        sessions_count=len(sessions_with_questions),
        question_types=question_type_counts,
        header_distribution=dict(header_counts.most_common()),
        skill_distribution=dict(skill_counts.most_common()),
    )

    return QuestionHistoryResult(
        interactions=all_interactions,
        metadata=metadata
    )
```

**Design notes:**
- Reuses existing `extract_ask_user_questions()` infrastructure (maintains compatibility)
- No artificial limit - returns ALL matching interactions
- Computes rich metadata during extraction (single pass)
- `include_context` parameter for controlling output size
- Sorts by timestamp descending (most recent first) for agent convenience

---

### 3. MCP Tool Wrapper

**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`

Add after `sbs_question_stats()` (around line 2890):

```python
@mcp.tool(
    "sbs_question_history",
    annotations=ToolAnnotations(
        title="Extract complete question history for agent analysis",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def sbs_question_history(
    ctx: Context,
    since: Annotated[
        Optional[str],
        Field(description="Entry ID or ISO timestamp to filter from")
    ] = None,
    until: Annotated[
        Optional[str],
        Field(description="Entry ID or ISO timestamp to filter until")
    ] = None,
    skill: Annotated[
        Optional[str],
        Field(description="Filter by active skill type (e.g., 'task', 'introspect')")
    ] = None,
    include_context: Annotated[
        bool,
        Field(description="Include context_before field (can be large, default False)")
    ] = False,
) -> str:
    """Extract complete question interaction history for agent-driven analysis.

    Returns ALL matching question interactions with comprehensive metadata. Unlike
    sbs_question_analysis (limited to 50) and sbs_question_stats (aggregates only),
    this tool exports the complete dataset optimized for agent consumption.

    Use cases:
    - /update-and-archive retrospective: analyze question quality in current session
    - /introspect L2 discovery: verify guidance adoption via question pattern changes
    - /introspect L3+ synthesis: track question evolution across improvement cycles
    - Standalone: investigate question patterns for friction reduction

    The tool returns structured facts - agents perform all analysis and filtering.

    Examples:
    - sbs_question_history() # All questions ever asked
    - sbs_question_history(skill="task") # Questions during /task sessions
    - sbs_question_history(since="1770242037") # Since specific archive entry
    - sbs_question_history(since="2026-02-01T00:00:00Z", until="2026-02-04T23:59:59Z") # Date range
    """
    db = _get_db(ctx)
    result = db.question_history(
        since=since,
        until=until,
        skill=skill,
        include_context=include_context
    )
    return result.model_dump_json(indent=2)
```

**Design notes:**
- Comprehensive docstring with use cases and examples
- Clear differentiation from existing question tools
- Annotations follow existing patterns (readOnlyHint, idempotentHint)

---

### 4. Documentation Integration

**File:** `/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md`

Update MCP Tools table (around line 355) to add new tool:

```markdown
| `sbs_question_history` | Extract complete question interaction history for agent analysis |
```

Update detailed tool listing in the same file to include full description and args.

---

## Integration Points

### A. `/update-and-archive` Skill

**File:** `.claude/skills/update-and-archive/SKILL.md`

**Location:** Part -1: Session Retrospective, Methodology section (after line 205)

**Change:** Add guidance for using `sbs_question_history`:

```markdown
### Methodology

- The agent has access to the full conversation context at spawn time (compaction-immune)
- Reads recent archive entries via `sbs_search_entries` or `sbs_context` for quantitative data
- **Uses `sbs_question_history` to extract all AskUserQuestion interactions from the current session** for quality analysis
- Examines user answer patterns, question frequency, correction patterns
- Captures specific examples, not just summaries -- `/introspect 2` reads these as L1 inputs for L2 synthesis
```

**Example usage in retrospective:**

```python
# Extract questions from this session
session_start = <session_start_entry_id>
questions = sbs_question_history(since=session_start, include_context=False)

# Analyze in L1 summary:
# - Were questions clear and well-structured?
# - Did users select first option frequently (signal of leading questions)?
# - Did multi-select get used where appropriate?
# - How many questions triggered clarification rounds?
# - Question type distribution: questions.metadata.question_types
# - Header usage: questions.metadata.header_distribution
```

---

### B. `/introspect` Skill - L2 Discovery

**File:** `.claude/skills/introspect/SKILL.md`

**Location 1:** L2 Phase 1, Step 0.5 Verification Sampling (line 162)

**Change:** Replace "Search session JSONL files" with explicit MCP call:

```markdown
2. **Evidence search:** For each selected item:
   - Use `sbs_question_history` to query question patterns since the guidance was added
   - Search archive entries via `sbs_search_entries` for related tags or patterns
   - Check if related issues were closed and if the fix is present in guidance files
```

**Location 2:** L2 Phase 1, Step 1 Automated Analysis (line 187)

**Change:** Add `sbs_question_history` to Pillar 1 tools:

```markdown
- [ ] Pillar 1 (User Effectiveness): Use `sbs_user_patterns()` + `sbs_successful_sessions()` + `sbs_question_history()`
```

**Example usage in L2 Pillar 1:**

```python
# Pillar 1: User Effectiveness analysis
questions = sbs_question_history(limit=200)  # Recent 200 interactions

# Agent analyzes:
# - questions.metadata.skill_distribution - where are questions concentrated?
# - High question count per session = unclear requirements
# - Low multi-select usage = missed opportunity for nuance
# - Answer distribution (if first option always selected = leading questions)
# - Compare header_distribution across cycles for evolution trends
```

---

### C. `/introspect` Skill - L3+ Meta-Analysis

**File:** `.claude/skills/introspect/SKILL.md`

**Location:** L3+ Phase 2, Synthesis, Required Analysis Dimensions (after line 740)

**Change:** Add explicit question pattern dimension under "1. Skill Evolution Trajectory":

```markdown
**Question Pattern Evolution:** Track how question quality has changed across improvement cycles.
Data sources: L2 summaries (Pillar 1 findings), `sbs_question_history` for trend validation.
Metrics: questions per session, multi-select adoption rate, header diversity, answer distribution.
```

**Example L3+ usage:**

```python
# Query all questions to validate L2 trend claims
all_questions = sbs_question_history()

# Agent synthesizes across L2 cycles:
# - Is multi-select adoption increasing? (metadata.question_types over time)
# - Are header texts becoming more specific? (metadata.header_distribution)
# - Is skill_distribution shifting (e.g., more questions during introspect, fewer during task)?
```

---

## Verification Strategy

### Manual Testing

1. **Test basic functionality:**
   ```python
   # From Claude Code MCP tool invocation:
   sbs_question_history()  # Should return all questions
   sbs_question_history(skill="task")  # Only task questions
   sbs_question_history(since="2026-02-01T00:00:00Z")  # Date filter
   ```

2. **Verify metadata accuracy:**
   - Check `total_interactions` matches length of `interactions` list
   - Check `total_questions` is sum of all questions across interactions
   - Check `skills_present` contains expected skills
   - Check `header_distribution` sums to `total_questions`

3. **Test integration:**
   - Manually invoke `/update-and-archive` and verify retrospective mentions question data
   - Check that L2 discovery can query question patterns
   - Verify L3+ synthesis references question evolution

### Automated Testing

**File:** `dev/scripts/sbs/tests/pytest/test_question_history.py` (new file)

```python
import pytest
from sbs_lsp_mcp.duckdb_layer import DuckDBLayer
from sbs_lsp_mcp.sbs_models import QuestionHistoryResult


def test_question_history_basic(tmp_path):
    """Test basic question_history extraction."""
    db = DuckDBLayer(archive_dir=tmp_path, oracle_path=tmp_path / "oracle.md")
    result = db.question_history()

    assert isinstance(result, QuestionHistoryResult)
    assert result.metadata.total_interactions >= 0
    assert result.metadata.total_questions >= 0
    assert len(result.interactions) == result.metadata.total_interactions


def test_question_history_skill_filter(tmp_path):
    """Test skill filtering works correctly."""
    db = DuckDBLayer(archive_dir=tmp_path, oracle_path=tmp_path / "oracle.md")
    result = db.question_history(skill="task")

    # All interactions should have skill="task"
    for interaction in result.interactions:
        assert interaction.skill == "task"


def test_question_history_metadata_consistency(tmp_path):
    """Test metadata calculations are accurate."""
    db = DuckDBLayer(archive_dir=tmp_path, oracle_path=tmp_path / "oracle.md")
    result = db.question_history()

    # Verify total_questions matches sum of questions in interactions
    actual_count = sum(len(i.questions) for i in result.interactions)
    assert result.metadata.total_questions == actual_count

    # Verify skills_present matches actual skills in interactions
    actual_skills = set(i.skill for i in result.interactions if i.skill)
    assert set(result.metadata.skills_present) == actual_skills
```

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: dev
  quality:
    # No visual changes, no quality score impact
  regression: >= 0  # No regressions in existing tests
```

**Test requirements:**
- New tests in `test_question_history.py` pass
- Existing question analysis tests still pass (`test_question_analysis.py` if exists)
- No regression in MCP server startup

---

## Wave Structure

**Wave 1: Core Implementation** (Sequential - single agent)
- Add Pydantic models to `sbs_models.py`
- Add `question_history()` method to `duckdb_layer.py`
- Add MCP tool wrapper to `sbs_tools.py`
- Write tests in `test_question_history.py`
- Run tests, verify all pass

**Wave 2: Documentation Integration** (Sequential after Wave 1)
- Update `CLAUDE.md` MCP tools table and listings
- Update `/update-and-archive/SKILL.md` methodology
- Update `/introspect/SKILL.md` L2 and L3+ sections
- Verify documentation consistency

**Wave 3: Validation** (Sequential after Wave 2)
- Manual testing: invoke tool with various args
- Verify metadata accuracy
- Test integration in `/update-and-archive` retrospective (optional: run actual retrospective)
- Run full test suite

---

## Critical Files

| File | Purpose | Action |
|------|---------|--------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | Pydantic models | Add `QuestionHistoryMetadata` and `QuestionHistoryResult` |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py` | DuckDB queries | Add `question_history()` method |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | MCP tool wrappers | Add `sbs_question_history()` tool |
| `dev/scripts/sbs/tests/pytest/test_question_history.py` | Test suite | Create new test file |
| `CLAUDE.md` | Agent documentation | Update MCP tools table |
| `.claude/skills/update-and-archive/SKILL.md` | Retrospective integration | Add tool usage guidance |
| `.claude/skills/introspect/SKILL.md` | L2/L3+ integration | Add tool usage in discovery and synthesis |

---

## Pattern Significance

This implementation establishes the **"DuckDB + Rich Args + Structured Export"** pattern for analytical tools:

1. **DuckDB layer method** - queries optimized for data extraction, not analysis
2. **Rich metadata** - pre-computed aggregates save agent work
3. **No artificial limits** - return ALL matching data
4. **Agent-optimized format** - structured JSON, easy to parse and analyze
5. **MCP tool wrapper** - thin wrapper, just serialization
6. **Clear documentation** - examples show how agents should consume the data

**Future tools following this pattern:**
- `sbs_gate_history` - extract all gate validation results for trend analysis
- `sbs_build_history` - extract all build metrics for performance analysis
- `sbs_visual_history` - extract all screenshot comparisons for regression analysis
- `sbs_tag_history` - extract all auto-tag applications for effectiveness analysis

Each follows the same architecture: DuckDB extraction → rich metadata → comprehensive export → agent analysis.
