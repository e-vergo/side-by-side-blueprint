# Task Plan: Permissions Review + Test Suite Refactor

**Issues:** #40, #34
**PR:** Single PR covering both issues

---

## Summary

Two complementary housekeeping tasks:
1. **#40**: Add deny rules to prevent bypassing PR workflow and build scripts
2. **#34**: Consolidate test suite to reduce duplication and improve transparency

---

## Test Suite Overview (Pre-Refactor)

| Category | Files | Lines | Tests |
|----------|-------|-------|-------|
| validators | 6 | 4,130 | 92 |
| root-level | 6 | 2,764 | 283 |
| mvp | 9 | 1,554 | 115 |
| oracle | 3 | 751 | ~25 |
| readme | 1 | 249 | 27 |
| interactions | 1 | 215 | 3 |
| **Total** | **26** | **9,663** | **545** |

---

## Phase 1: Test Suite Refactor (#34)

### Wave 1.1: Create shared validator fixtures

**New file:** `dev/scripts/sbs/tests/pytest/validators/conftest.py`

Extract common fixtures from the 6 validator test files:
- `temp_screenshots_dir(pages: list[str])` - parametrized screenshot directory
- `empty_screenshots_dir()` - empty directory for edge cases
- `common_css_path()` - path to real common.css
- `real_css_dir()` - path to CSS assets

### Wave 1.2: Create base test mixins

**New file:** `dev/scripts/sbs/tests/pytest/validators/base_test.py`

```python
class ValidatorPropertiesTestMixin:
    """Reusable tests for validator.name and validator.category"""
    validator_name: str
    validator_category: str = "visual"

class HeuristicResponseTestMixin:
    """Reusable tests for AI response parsing (JSON, fallback, edge cases)"""
```

### Wave 1.3: Refactor validator test files

Update these 6 files to use mixins and shared fixtures:
- `test_color_match.py` (472 lines)
- `test_variable_coverage.py` (590 lines)
- `test_dashboard_clarity.py` (778 lines)
- `test_jarring_check.py` (648 lines)
- `test_professional_score.py` (806 lines)
- `test_toggle_discoverability.py` (836 lines)

**Target:** Reduce validator tests from 4,130 → ~3,680 lines (~450 line reduction)

### Wave 1.4: Root conftest cleanup

**Modify:** `dev/scripts/sbs/tests/pytest/conftest.py`

Extract repeated archive entry creation into helper:
```python
def _create_test_entry(entry_id, project, tags, notes) -> ArchiveEntry:
    """Shared entry creation for fixtures."""
```

Consolidate 4 repetitive fixtures using the helper.

### Wave 1.5: CLI test assertion helpers

**Modify:** `dev/scripts/sbs/tests/pytest/test_cli.py`

Add CLIResult helper methods to reduce 36 repetitive assertions:
```python
def assert_success(result, msg=""):
def assert_contains(result, text, msg=""):
```

### Wave 1.6: Regenerate TEST_CATALOG.md

Run `sbs test-catalog` to update documentation with new structure.

---

## Phase 2: Permissions Review (#40)

### Wave 2.1: Add deny rules

**Modify:** `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(.venv/bin/pip install:*)",
      "Bash(.venv/bin/playwright install:*)"
    ],
    "deny": [
      "Bash(git push:*)",
      "Bash(git push)",
      "Bash(lake build:*)",
      "Bash(lake build)"
    ]
  }
}
```

**Rationale:**
- `git push` → Use PR workflow (`sbs_pr_create`, `gh pr create`)
- `lake build` → Use `build.py` or MCP `sbs_build_project`
- MCP skill tools (`sbs_skill_start` etc.) remain allowed - they ARE the proper abstraction

### Wave 2.2: Manual verification

Test that deny rules work:
1. `git push` → blocked
2. `lake build` → blocked
3. `sbs_build_project` MCP → works
4. `build.py` script → works

---

## Files Changed

**New:**
- `dev/scripts/sbs/tests/pytest/validators/conftest.py`
- `dev/scripts/sbs/tests/pytest/validators/base_test.py`

**Modified:**
- `.claude/settings.json` (add deny rules)
- `dev/scripts/sbs/tests/pytest/conftest.py` (extract archive entry helper)
- `dev/scripts/sbs/tests/pytest/test_cli.py` (add assertion helpers)
- `dev/scripts/sbs/tests/pytest/validators/test_color_match.py`
- `dev/scripts/sbs/tests/pytest/validators/test_variable_coverage.py`
- `dev/scripts/sbs/tests/pytest/validators/test_dashboard_clarity.py`
- `dev/scripts/sbs/tests/pytest/validators/test_jarring_check.py`
- `dev/scripts/sbs/tests/pytest/validators/test_professional_score.py`
- `dev/scripts/sbs/tests/pytest/validators/test_toggle_discoverability.py`
- `dev/storage/TEST_CATALOG.md` (regenerated)

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

---

## Verification

1. **Test count unchanged:** `pytest sbs/tests/pytest/ --collect-only` shows 545 tests
2. **All tests pass:** `pytest sbs/tests/pytest/ -v` (full suite)
3. **Validator line reduction:** `wc -l` on validator tests shows ~450 fewer lines
4. **Root conftest cleaner:** Helper function reduces fixture boilerplate
5. **CLI assertions cleaner:** Helper methods reduce assertion repetition
6. **Deny rules work:** Manual test that `git push` and `lake build` are blocked
7. **Workflows intact:** `build.py` and MCP tools still work
