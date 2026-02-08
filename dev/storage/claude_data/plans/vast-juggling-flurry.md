# Plan: Issue #36 - Document Behavioral Preferences + Enhancements

## Summary

Four-wave implementation adding behavioral preferences to CLAUDE.md, enhancing the oracle with configurable args, integrating tests into gating, and creating an interactive testing tier.

**Issue:** #36 - Document Claude behavioral preferences: proactive logging, oracle-first, aggressive delegation

**Expanded Scope:**
- Documentation changes (CLAUDE.md)
- Oracle enhancement (5 new args)
- Gating integration (evergreen enforcement + change-based selection)
- Interactive testing tier (new `@interactive` marker + Playwright tests)

---

## Wave Architecture

| Wave | Focus | Files | Gate |
|------|-------|-------|------|
| 1 | CLAUDE.md documentation | 1 file | Manual review |
| 2 | Oracle enhancement | 3 files + tests | 100% pytest pass |
| 3 | Gating integration | 3 files + tests | 100% pytest pass |
| 4 | Interactive testing | 4 files (3 new) | 100% pytest pass |

---

## Wave 1: CLAUDE.md Documentation

**Objective:** Add 4 behavioral preferences under User Preferences

### Files to Modify

| File | Action |
|------|--------|
| `CLAUDE.md` | Add 4 new preference subsections |

### Content to Add

```markdown
### Proactive Bug Logging

When encountering clear bugs during work, log them autonomously via `/log` without waiting for user direction. This applies when there's unambiguous evidence of a real bug (error messages, broken behavior, failing tests). Gray areas still require confirmation.

### Oracle-First Approach

Use `sbs_oracle_query` reflexively as the default starting point for understanding:
- Where files/concepts are located
- How components relate to each other
- What exists before searching manually

The oracle should be the go-to before Glob/Grep for orientation questions.

**Configurable arguments:**
| Arg | Type | Purpose |
|-----|------|---------|
| `result_type` | string | Filter to "files", "concepts", or "all" |
| `scope` | string | Limit to specific repo (e.g., "Dress", "Runway") |
| `include_raw_section` | bool | Return full section content |
| `min_relevance` | float | Filter low-relevance matches (0.0-1.0) |
| `fuzzy` | bool | Enable fuzzy matching for typos |

### Aggressive Delegation

Top-level chat serves as orchestrator only:
- Discusses requirements with user
- Spawns `sbs-developer` agents for ALL file writing
- Synthesizes results
- Rarely (if ever) writes files directly

**Goal:** Preserve orchestrator context by delegating implementation work to agents.

### Testing Suite at Gating

Before any phase transition in `/task`, the evergreen test tier runs automatically:
- `pytest sbs/tests/pytest -m evergreen --tb=short`
- 100% pass rate required for transition
- Failures block progression (no silent skips)

Change-based validator selection ensures only relevant validators run based on modified repos.
```

### Validation
- Manual review of rendered markdown

---

## Wave 2: Oracle Enhancement

**Objective:** Add 5 configurable args to `sbs_oracle_query`

### Files to Modify

| File | Changes |
|------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | Add 5 new parameters to `sbs_oracle_query` |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_utils.py` | Update `search_oracle()` with filter logic |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | Add result_type to response if needed |

### New Parameters

```python
sbs_oracle_query(
    query: str,
    max_results: int = 10,
    # NEW:
    result_type: str = "all",        # "files" | "concepts" | "all"
    scope: Optional[str] = None,     # "Dress", "Runway", etc.
    include_raw_section: bool = False,
    min_relevance: float = 0.0,      # 0.0-1.0
    fuzzy: bool = False,
)
```

### Filter Implementation in `search_oracle()`

1. `result_type`: Skip file matches if "concepts", skip concepts if "files"
2. `scope`: Check `file_path.startswith(scope)` or `info['section'] == scope`
3. `min_relevance`: Filter `relevance < min_relevance` before sorting
4. `fuzzy`: Use `difflib.get_close_matches()` for approximate matching

### Tests to Create

| File | Tests |
|------|-------|
| `dev/scripts/sbs/tests/pytest/oracle/test_oracle_filters.py` (new) | 5 tests for new params |

```python
@pytest.mark.evergreen
class TestOracleFilters:
    def test_result_type_files_only(self): ...
    def test_result_type_concepts_only(self): ...
    def test_scope_limits_to_directory(self): ...
    def test_min_relevance_filters_low_scores(self): ...
    def test_fuzzy_matches_typos(self): ...
```

### Validation
```bash
pytest sbs/tests/pytest/oracle/ -v
```

---

## Wave 3: Gating Integration

**Objective:** Enforce evergreen tier + connect change detection to validator selection

### Files to Modify

| File | Changes |
|------|---------|
| `dev/scripts/sbs/archive/gates.py` | Add `tier` param to `evaluate_test_gate()`, default to "evergreen" |
| `dev/scripts/sbs/tests/compliance/mapping.py` | Add `REPO_VALIDATOR_MAPPING` + `get_validators_for_changes()` |
| `.claude/skills/task/SKILL.md` | Update gate schema documentation |

### Implementation: gates.py

```python
def evaluate_test_gate(gate: GateDefinition, tier: str = "evergreen") -> GateResult:
    cmd = [pytest_path, "sbs/tests/pytest", "-q", "--tb=no"]
    if tier != "all":
        cmd.extend(["-m", tier])
    # ... run and parse
```

### Implementation: mapping.py

```python
REPO_VALIDATOR_MAPPING: dict[str, list[str]] = {
    "dress-blueprint-action": ["T5", "T6", "T7", "T8"],
    "Dress": ["T5", "T6", "T3"],
    "Runway": ["T3", "T4", "T5", "T6", "T7", "T8"],
    "LeanArchitect": ["T5"],
    "subverso": ["T7", "T8"],
    "verso": ["T7", "T8"],
    "SBS-Test": ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"],
}

def get_validators_for_changes(changed_repos: list[str]) -> list[str]:
    validators = set()
    for repo in changed_repos:
        validators.update(REPO_VALIDATOR_MAPPING.get(repo, []))
    return sorted(validators)
```

### Tests to Add

| File | Tests |
|------|-------|
| `dev/scripts/sbs/tests/pytest/test_gates.py` | Add tier filtering tests |

```python
@pytest.mark.evergreen
def test_evergreen_tier_adds_marker(self, mock_run):
    # Verify -m evergreen in command
```

### Validation
```bash
pytest sbs/tests/pytest/test_gates.py -v
```

---

## Wave 4: Interactive Testing Tier

**Objective:** New `@interactive` marker + Playwright infrastructure + sidebar test

### Files to Create

| File | Purpose |
|------|---------|
| `dev/scripts/sbs/tests/pytest/interactions/__init__.py` | Package init |
| `dev/scripts/sbs/tests/pytest/interactions/conftest.py` | Playwright fixtures |
| `dev/scripts/sbs/tests/pytest/interactions/test_sidebar.py` | Proof of concept |

### Files to Modify

| File | Changes |
|------|---------|
| `dev/scripts/sbs/tests/pytest/conftest.py` | Register `@interactive` marker |

### Marker Registration

```python
config.addinivalue_line(
    "markers",
    "interactive: tests requiring browser automation (Playwright)"
)
```

### Fixtures (interactions/conftest.py)

- `project_root()` - SBS-Test path
- `site_dir()` - Built _site directory
- `server_port()` - Auto-find free port
- `base_url()` - Start HTTP server, yield URL
- `browser()` - Playwright chromium instance
- `page()` - Fresh page per test

### Proof of Concept Test

```python
@pytest.mark.interactive
class TestSidebarToggle:
    def test_sidebar_visible_on_load(self, page, base_url): ...
    def test_sidebar_toggle_exists(self, page, base_url): ...
    def test_sidebar_collapses_on_click(self, page, base_url): ...
```

### Validation
```bash
pytest sbs/tests/pytest/interactions/ -m interactive -v
```

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T1: ">= 1.0"
    T2: ">= 1.0"
    T5: ">= 1.0"
    T6: ">= 1.0"
  regression: ">= 0"
```

**100% pass rate required for all waves.**

---

## Verification

### Per-Wave Verification

| Wave | Command | Expected |
|------|---------|----------|
| 1 | Manual review | CLAUDE.md renders correctly |
| 2 | `pytest sbs/tests/pytest/oracle/ -v` | All pass |
| 3 | `pytest sbs/tests/pytest/test_gates.py -v` | All pass |
| 4 | `pytest sbs/tests/pytest/interactions/ -m interactive -v` | All pass |

### Final Verification

```bash
# Run all evergreen tests
pytest sbs/tests/pytest -m evergreen -v

# Run interactive tests
pytest sbs/tests/pytest/interactions/ -m interactive -v

# Validate project
python -m sbs validate-all --project SBSTest
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Playwright not installed | `pytest.skip()` in fixture |
| _site not built | `pytest.skip()` with message |
| MCP server needs restart | Document post-wave 2 |
| Fuzzy matching slow | Opt-in only via param |

---

## Notes

- Wave 1-3 are independent, Wave 4 depends on Wave 3
- Single `sbs-developer` agent per wave
- Commits go to feature branch, PR created at execution start
- MCP server restart needed after Wave 2 for oracle changes to take effect
