# Task #59: Integrate Validator Runs into Archive Uploads

## Summary

Add `--validate` flag to `sbs archive upload` that runs T1-T6 validators programmatically and attaches quality scores to archive entries. Replace the existing build-trigger subprocess approach with a unified runner.

## Wave 1: Validator Runner + T1 Validator (Foundation)

### New: `dev/scripts/sbs/tests/validators/runner.py`

Core orchestration module:
- `VALIDATOR_TO_METRIC` mapping: validator name -> metric ID
- `resolve_project(project)` — resolves project name/root, falls back to SBSTest
- `build_validation_context(project, project_root)` — constructs `ValidationContext` with auto-detected paths (screenshots_dir, site_dir, repo_commits)
- `run_validators(project, metric_ids=None, update_ledger=True, skip_heuristic=False)` — discovers validators, runs them, updates ledger, returns `RunnerResult`
- Heuristic validators (T3/T4/T7/T8) gracefully skipped when `skip_heuristic=True` or no screenshots exist

### New: `dev/scripts/sbs/tests/validators/cli_execution.py`

T1 validator (CLI Execution):
- Name: `"cli-execution"`, category: `"code"`
- Runs evergreen pytest suite via `subprocess.run()`
- Parses pass/fail counts
- Returns binary 100.0/0.0 score

### Mapping Table

| Validator Name | Metric ID | Status |
|---|---|---|
| `cli-execution` | `t1-cli-execution` | **NEW** |
| `ledger-health` | `t2-ledger-population` | EXISTS |
| `dashboard-clarity` | `t3-dashboard-clarity` | EXISTS (heuristic) |
| `toggle-discoverability` | `t4-toggle-discoverability` | EXISTS (heuristic) |
| `status-color-match` | `t5-color-match` | EXISTS |
| `css-variable-coverage` | `t6-css-coverage` | EXISTS |
| `jarring-check` | `t7-jarring` | EXISTS (heuristic) |
| `professional-score` | `t8-professional` | EXISTS (heuristic) |

## Wave 2: Archive Integration

### Modified: `dev/scripts/sbs/cli.py` (~3 lines)

Add `--validate` flag to `archive_upload_parser` (after line 486).

### Modified: `dev/scripts/sbs/archive/cmd.py` (~2 lines)

Pass `validate=` kwarg from args through to `archive_upload()`. Add quality score to summary output.

### Modified: `dev/scripts/sbs/archive/upload.py` (~20 lines)

1. Add `validate: bool = False` param to `archive_upload()`
2. Replace lines 347-357 (subprocess auto-validation) with programmatic runner call:
   - If `--validate` passed: run all validators via `run_validators()`
   - If build trigger with no scores: run validators (backward compat)
   - Reload quality scores from updated ledger after run

## Wave 3: Tests

### New: `dev/scripts/sbs/tests/pytest/validators/test_cli_execution.py`

- Validator property tests (name, category)
- Mocked subprocess for pass/fail scenarios
- Marked `@pytest.mark.evergreen`

### New: `dev/scripts/sbs/tests/pytest/validators/test_runner.py`

- Mapping completeness (all 8 metrics covered)
- `resolve_project()` with explicit and None
- `run_validators()` with mocked registry
- Heuristic skip behavior
- Ledger update path
- Marked `@pytest.mark.evergreen`

## File Inventory

| Action | File | Purpose |
|--------|------|---------|
| NEW | `dev/scripts/sbs/tests/validators/runner.py` | Validator runner |
| NEW | `dev/scripts/sbs/tests/validators/cli_execution.py` | T1 validator |
| NEW | `dev/scripts/sbs/tests/pytest/validators/test_cli_execution.py` | T1 tests |
| NEW | `dev/scripts/sbs/tests/pytest/validators/test_runner.py` | Runner tests |
| EDIT | `dev/scripts/sbs/cli.py` | Add --validate flag |
| EDIT | `dev/scripts/sbs/archive/cmd.py` | Pass validate kwarg |
| EDIT | `dev/scripts/sbs/archive/upload.py` | Replace subprocess with runner |

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: ">= 0.8"
    T6: ">= 0.8"
  regression: ">= 0"
```

## Verification

1. `python3 -c "from sbs.tests.validators.runner import run_validators; print(run_validators('SBSTest', metric_ids=['t1','t2','t5','t6']))"`
2. `python3 -m sbs archive upload --validate --dry-run --project SBSTest`
3. `pytest sbs/tests/pytest/validators/test_cli_execution.py sbs/tests/pytest/validators/test_runner.py -v`
4. `pytest sbs/tests/pytest -m evergreen -v`
