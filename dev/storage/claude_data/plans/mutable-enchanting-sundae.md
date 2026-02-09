# Task: DuckDB Query Layer + Oracle Evolution (#118, #128)

## Summary

Replace ALL archive data access (27 call sites across 2 files) with a lifespan-scoped DuckDB instance. Eliminate `load_archive_index()` entirely. Replace `/oracle` skill + `sbs_oracle_query` with unified `ask_oracle` MCP tool. DuckDB becomes the singular data substrate for the entire MCP server.

## Decisions (from alignment)

- **Both issues** in one session, sequential (#118 then #128)
- **Full unification** — all 27 `load_archive_index()` call sites migrated, function deleted
- **Lifespan-scoped DuckDB** in AppContext with mtime-based staleness + explicit invalidation after writes
- **JSONL session data** loaded into DuckDB
- **Oracle concept index** loaded into DuckDB (parsed from `sbs-oracle.md`)
- **`sbs_oracle_query` replaced entirely** by `ask_oracle`
- **`/oracle` skill deleted**, `sbs-oracle.md` retained as source data

## Architecture

```
BEFORE:  sbs_tools.py → sbs_self_improve.py → load_archive_index() → json.load()
         sbs_tools.py → sbs_utils.py → load_archive_index() → json.load()
         sbs_tools.py → sbs_utils.py → load_oracle_content() → file read + regex

AFTER:   sbs_tools.py → DuckDBLayer (lifespan-scoped, in AppContext)
                           ├─ entries table        (from archive_index.json)
                           ├─ index_metadata table (global_state, last_epoch_entry)
                           ├─ questions table      (from JSONL session files)
                           ├─ skill_intervals view (derived from entries)
                           ├─ oracle_concepts table (from sbs-oracle.md)
                           └─ oracle_files table   (from sbs-oracle.md)
```

**Write path unchanged:** Skill tools still write via `sbs archive upload` subprocess. After write, they call `db.invalidate()` to force reload on next read.

**Read path unified:** Every tool that reads archive/oracle data goes through `DuckDBLayer`.

## Schema

```sql
CREATE TABLE entries (
    entry_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP,
    project VARCHAR,
    build_run_id VARCHAR,
    notes TEXT,
    tags VARCHAR[],
    auto_tags VARCHAR[],
    screenshots VARCHAR[],
    trigger VARCHAR,
    quality_overall FLOAT,
    quality_scores JSON,
    quality_delta JSON,
    gs_skill VARCHAR,
    gs_substate VARCHAR,
    state_transition VARCHAR,
    epoch_summary JSON,
    gate_validation JSON,
    issue_refs VARCHAR[],
    pr_refs INTEGER[],
    repo_commits JSON,
    rubric_id VARCHAR,
    synced_to_icloud BOOLEAN,
    added_at TIMESTAMP
);

CREATE TABLE index_metadata (
    global_state_skill VARCHAR,
    global_state_substate VARCHAR,
    last_epoch_entry VARCHAR,
    version VARCHAR
);

CREATE TABLE questions (
    session_file VARCHAR,
    timestamp TIMESTAMP,
    question_text TEXT,
    header VARCHAR,
    options JSON,
    multi_select BOOLEAN,
    user_answer TEXT
);

CREATE TABLE oracle_concepts (
    concept VARCHAR,
    primary_location VARCHAR,
    notes TEXT,
    section VARCHAR
);

CREATE TABLE oracle_files (
    file_path VARCHAR,
    section VARCHAR,
    concept VARCHAR,
    notes TEXT
);

-- Derived view for skill session grouping
CREATE VIEW skill_sessions AS
WITH boundaries AS (
    SELECT *,
        SUM(CASE WHEN state_transition IN ('phase_start','skill_start')
                  AND gs_skill IS NOT NULL
                  AND (LAG(state_transition) OVER (ORDER BY entry_id)
                       IN ('phase_end','handoff','phase_fail')
                       OR LAG(gs_skill) OVER (ORDER BY entry_id) IS NULL
                       OR LAG(gs_skill) OVER (ORDER BY entry_id) != gs_skill)
            THEN 1 ELSE 0 END) OVER (ORDER BY entry_id) AS session_id
    FROM entries WHERE gs_skill IS NOT NULL
)
SELECT * FROM boundaries;

-- Derived view for skill intervals (question correlation)
CREATE VIEW skill_intervals AS
SELECT
    MIN(created_at) AS start_ts,
    MAX(created_at) AS end_ts,
    gs_skill AS skill,
    gs_substate AS substate,
    session_id
FROM skill_sessions
GROUP BY session_id, gs_skill, gs_substate;
```

## Wave Structure

### Wave 1: DuckDB Foundation (1 agent)

**New:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py`

```python
class DuckDBLayer:
    def __init__(self, archive_dir: Path, session_dir: Path, oracle_path: Path): ...
    def ensure_loaded(self) -> None: ...        # Lazy init, create tables, load all data
    def refresh_if_stale(self) -> None: ...     # Check mtimes, reload if changed
    def invalidate(self) -> None: ...           # Force reload on next query (after writes)
    def close(self) -> None: ...                # Cleanup

    # --- Core access (replaces load_archive_index) ---
    def get_global_state(self) -> tuple[Optional[str], Optional[str]]: ...  # (skill, substate)
    def get_metadata(self) -> dict: ...         # global_state + last_epoch_entry + projects list
    def get_entry(self, entry_id: str) -> Optional[dict]: ...
    def get_entries(self, **filters) -> list[dict]: ...  # project, tags, since, trigger, limit
    def get_epoch_entries(self, epoch_entry_id: Optional[str]) -> list[dict]: ...
    def get_entries_by_project(self, project: str) -> list[dict]: ...
    def list_projects(self) -> list[str]: ...

    # --- Analytics (replaces sbs_self_improve.py) ---
    def analysis_summary(self) -> AnalysisSummary: ...
    def entries_since_self_improve(self) -> SelfImproveEntries: ...
    def successful_sessions(self) -> SuccessPatterns: ...
    def comparative_analysis(self) -> ComparativeAnalysis: ...
    def system_health(self) -> SystemHealthReport: ...
    def user_patterns(self) -> UserPatternAnalysis: ...
    def skill_stats(self, as_findings: bool) -> SkillStatsResult: ...
    def phase_transition_health(self, as_findings: bool) -> PhaseTransitionHealthResult: ...
    def interruption_analysis(self, as_findings: bool) -> InterruptionAnalysisResult: ...
    def gate_failures(self, as_findings: bool) -> GateFailureReport: ...
    def tag_effectiveness(self, as_findings: bool) -> TagEffectivenessResult: ...
    def question_analysis(self, since, until, skill, limit) -> QuestionAnalysisResult: ...
    def question_stats(self, since, until) -> QuestionStatsResult: ...

    # --- Oracle (replaces search_oracle + archive enrichment) ---
    def oracle_query(self, query, max_results, min_relevance, fuzzy,
                     include_archive, include_issues, include_quality) -> AskOracleResult: ...

    # --- Context generation (replaces generate_context_block) ---
    def build_context_block(self, include: list[str]) -> str: ...
```

**Modified:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py`
- Add `duckdb_layer: Optional[DuckDBLayer]` to `AppContext`
- Initialize in `app_lifespan()` with archive_dir, session_dir, oracle_path
- Call `close()` in lifespan cleanup

**Modified:** `forks/sbs-lsp-mcp/pyproject.toml`
- Add `duckdb>=1.2.0` to dependencies

**New:** `forks/sbs-lsp-mcp/tests/test_duckdb_layer.py`
- Schema creation from mock archive data (reuse conftest fixtures)
- Core access methods (get_global_state, get_entries, get_epoch_entries)
- Analytics query methods (all 13)
- Oracle query methods
- Refresh-on-stale and invalidation behavior
- Empty archive edge case

### Wave 2: Full Migration (1 agent)

Migrate ALL 27 `load_archive_index()` call sites + oracle call sites in `sbs_tools.py`.

**Modified:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`

All tools extract DuckDBLayer via: `db = ctx.request_context.lifespan_context["duckdb_layer"]`

| Tool (line) | Current | After |
|-------------|---------|-------|
| `sbs_archive_state` (220) | `load_archive_index()` → `.global_state`, `.by_project` | `db.get_metadata()` |
| `sbs_epoch_summary` (267) | `load_archive_index()` → `get_epoch_entries()` | `db.get_epoch_entries()` |
| `sbs_context` (354) | `load_archive_index()` → `.global_state`, `.entries` | `db.build_context_block()` |
| `sbs_oracle_query` (107) | `load_oracle_content()` → `search_oracle()` | **REPLACED by `ask_oracle`** → `db.oracle_query()` |
| `sbs_visual_history` (1260) | `load_archive_index()` → `.get_entries_by_project()` | `db.get_entries_by_project()` |
| `sbs_search_entries` (1356) | `load_archive_index()` → filter loop | `db.get_entries(**filters)` |
| `sbs_issue_log` (1818) | `load_archive_index()` → `.global_state` | `db.get_global_state()` |
| `sbs_skill_status` (3055) | `load_archive_index()` → `.global_state`, `.entries` | `db.get_global_state()` + `db.get_entries()` |
| `sbs_skill_start` (3123,3157) | `load_archive_index()` ×2 (check + reload) | `db.get_global_state()` + `db.invalidate()` after write |
| `sbs_skill_transition` (3204) | `load_archive_index()` → `.global_state` | `db.get_global_state()` + `db.invalidate()` after write |
| `sbs_skill_end` (3312) | `load_archive_index()` → `.global_state` | `db.get_global_state()` + `db.invalidate()` after write |
| `sbs_skill_fail` (3391) | `load_archive_index()` → `.global_state` | `db.get_global_state()` + `db.invalidate()` after write |
| `sbs_skill_handoff` (3474) | `load_archive_index()` → `.global_state` | `db.get_global_state()` + `db.invalidate()` after write |
| `sbs_improvement_capture` (3566) | `load_archive_index()` → `.entries`, `.by_tag` | `db.get_entries()` |
| 14 analytics tools (2768-3030) | `_impl()` in `sbs_self_improve.py` | `db.<method>()` |

**Deleted:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` (1,670 lines)

**Modified:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_utils.py`
- DELETE `load_archive_index()` function
- DELETE `get_epoch_entries()` helper
- DELETE `generate_context_block()` helper
- DELETE `load_oracle_content()`, `parse_oracle_sections()`, `search_oracle()` (moved to DuckDB)
- KEEP: Non-archive utilities (file path helpers, constants like `ARCHIVE_DIR`, `SBS_ROOT`)

**Modified:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py`
- New `AskOracleResult` model (replaces `OracleQueryResult`)
- Keep all existing analytics models (API contract preserved)

**Updated tests:**
- `test_archive_tools.py` — update to use DuckDB fixtures instead of mock archive index
- `test_oracle_tools.py` — replace `sbs_oracle_query` tests with `ask_oracle` tests
- `test_skill_tools.py` — update fixtures for DuckDB-based state access

### Wave 3: Skill Deletion + Documentation (1 agent)

**Deleted:** `.claude/skills/oracle/SKILL.md`

**Modified:** `CLAUDE.md`
- Remove `/oracle` from Custom Skills section
- Update MCP tool table: `sbs_oracle_query` → `ask_oracle` with new description
- Update "Oracle-First Approach" to reference `ask_oracle`
- Remove `/oracle` from multiagent exclusion list
- Update MCP tool count references

**Modified:** `.claude/agents/sbs-oracle.md`
- Reframe as oracle data file (concept index source), not agent definition
- Remove agent-specific instructions (model, spawning behavior)
- Keep: concept index, file purpose map, how-to patterns, gotchas, cross-repo impact map

**Modified:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/instructions.py`
- Update server instructions if they reference `sbs_oracle_query`

### Wave 4: Integration Verification (1 agent)

- `cd forks/sbs-lsp-mcp && uv run pytest tests/ -v` — all MCP tests pass
- `sbs_run_tests(tier="evergreen")` — all evergreen SBS tests pass
- `sbs_run_tests(repo="mcp")` — MCP repo tests pass
- Verify `sbs_self_improve.py` is deleted
- Verify `load_archive_index()` is gone from `sbs_utils.py`
- Verify `/oracle` skill is gone from `.claude/skills/`
- Verify no remaining imports of deleted modules

## File Summary

| Action | File | Wave |
|--------|------|------|
| NEW | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py` | 1 |
| NEW | `forks/sbs-lsp-mcp/tests/test_duckdb_layer.py` | 1 |
| MOD | `forks/sbs-lsp-mcp/pyproject.toml` | 1 |
| MOD | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py` | 1 |
| MOD | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | 2 |
| MOD | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_utils.py` | 2 |
| MOD | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | 2 |
| DEL | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` | 2 |
| MOD | `forks/sbs-lsp-mcp/tests/test_archive_tools.py` | 2 |
| MOD | `forks/sbs-lsp-mcp/tests/test_oracle_tools.py` | 2 |
| MOD | `forks/sbs-lsp-mcp/tests/test_skill_tools.py` | 2 |
| DEL | `.claude/skills/oracle/SKILL.md` | 3 |
| MOD | `CLAUDE.md` | 3 |
| MOD | `.claude/agents/sbs-oracle.md` | 3 |
| MOD | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/instructions.py` | 3 |

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  mcp_tests: all_pass
  regression: >= 0
  dead_code: zero          # No remaining load_archive_index() calls, no sbs_self_improve imports
```

## Verification

1. `cd forks/sbs-lsp-mcp && uv run pytest tests/ -v` — all MCP tests pass
2. `sbs_run_tests(tier="evergreen")` — all evergreen SBS tests pass
3. `sbs_run_tests(repo="mcp")` — MCP repo tests pass
4. `grep -r "load_archive_index" forks/sbs-lsp-mcp/src/` — zero results
5. `grep -r "sbs_self_improve" forks/sbs-lsp-mcp/src/` — zero results
6. `grep -r "sbs_oracle_query" forks/sbs-lsp-mcp/src/` — zero results
7. `ls .claude/skills/oracle/` — does not exist

## Risks

- **DuckDB JSONL parsing:** Session JSONL files have nested JSON. May need Python pre-processing before DuckDB ingestion — DuckDB's `read_json_auto` might not handle the nesting.
- **Session grouping SQL:** The window-function CTE for session detection is the most complex query. If it proves fragile, the DuckDBLayer can precompute sessions during loading (Python) and store in a sessions table.
- **Skill tool write-then-read:** After subprocess writes to `archive_index.json`, `db.invalidate()` forces reload. If the subprocess fails silently, DuckDB could serve stale data. Mitigation: skill tools already check subprocess return codes.
