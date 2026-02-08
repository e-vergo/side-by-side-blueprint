# Plan: Fix Stale .olean Detection (#281)

## Context

Stale `.olean` files are a persistent issue. During dev work, builds and serves succeed but served content doesn't reflect latest code. The root cause: `build.py`'s skip logic (`has_lean_changes()`) only checks `.lean` source hashes in the *target repo*. It misses upstream dependency rebuilds, stale `.lake/packages/` nested builds, and stale `lakefile.olean`. Additionally, `sbs_serve_project` MCP tool serves from a nonexistent `_site/` directory instead of `.lake/build/runway/`.

**Outcome:** `sbs_build_project` always produces fresh builds by default. New `sbs clean` CLI for manual recovery. Fixed serve tool with freshness warning.

## Alignment Summary

| Decision | Choice |
|----------|--------|
| Skip logic | Always run Lake. Add `--skip-lake` opt-in for explicit fast path. |
| Clean command | `--project NAME` + `--all`. `--check` dry-run, `--force` for deletion. |
| Serve fix | `_site` → `.lake/build/runway/`. Pre-serve freshness warning. |
| Repos touched | `dev/scripts/sbs/` + `forks/sbs-lsp-mcp/` + new tests |

## Wave 1: Core Changes (3 parallel agents)

### Agent A: Invert Skip Logic

**Files:** `dev/scripts/sbs/build/config.py`, `dev/scripts/sbs/build/orchestrator.py`

**config.py** — Replace `force_lake: bool = False` with `skip_lake: bool = False` at line 78.

**orchestrator.py** — 8 modification sites:

1. **Lines 594-596** (toolchain skip): Replace `force_lake`+`has_lean_changes` gate → simple `skip_lake` check. When `skip_lake` is False (default), Lake always runs for every toolchain repo.

2. **Lines 644-661** (`_needs_project_build`): Simplify — return `True` unless `skip_lake` is set.

3. **Lines 820-822** (project build guard): Use `skip_lake` instead of `_needs_project_build()` for the skip message.

4. **Lines ~1036** (CSS fast path): Replace `force_lake` reference with `skip_lake` in condition.

5. **Lines ~1088** (manifest update): Guard with `not skip_lake` instead of `force_lake or has_lean_changes`.

6. **Lines ~1122** (mathlib cache): Same pattern.

7. **Lines 1269-1273** (CLI argument): Replace `--force-lake` with `--skip-lake`. Add deprecated `--force-lake` that prints warning and is a no-op.

8. **Line 1312** (config construction): `skip_lake=args.skip_lake`.

**Key insight:** `caching.py` needs no changes. `has_lean_changes()` and `get_lean_sources_hash()` are still called in the `skip_lake` code path and for hash saving after successful builds.

### Agent B: `sbs clean` Command

**Files:** `dev/scripts/sbs/commands/clean.py` (NEW), `dev/scripts/sbs/build/phases.py`, `dev/scripts/sbs/cli.py`

**New `commands/clean.py`:**
- `cmd_clean(args) -> int` — CLI handler
- `clean_repo(name, repo_path, cache_dir, full=False, dry_run=False) -> list[str]` — per-repo cleanup
- `_collect_clean_targets(name, repo_path, cache_dir, full) -> list[tuple[str, int]]` — dry-run sizing

Clean targets per repo:
| Target | Default | `--full` only |
|--------|---------|---------------|
| `.lake/build/` | Yes | — |
| `lakefile.olean` | Yes | — |
| `~/.sbs-cache/{name}/lean_hash` | Yes | — |
| `.lake/packages/` | No | Yes |

CLI flags: `--project NAME`, `--all`, `--full`, `--check` (dry-run), `--force` (required for `--all`).

**phases.py** — Enhance `clean_build_artifacts()` (line 134) to also remove `lakefile.olean` and optionally `~/.sbs-cache/{name}/lean_hash`. Add `include_lakefile_olean: bool = True` param.

**cli.py** — Add `clean` subparser in `create_parser()`, add dispatch in `main()`.

### Agent C: Fix Serve Tool

**Files:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`

1. **Lines 888-897**: Replace all `_site` paths with `.lake/build/runway`:
   ```
   "SBSTest": SBS_ROOT / "toolchain" / "SBS-Test" / ".lake" / "build" / "runway",
   ```

2. **Pre-serve freshness check** (insert before server start): Compare `manifest.json` mtime vs current time. If artifacts >24h old, include warning in `ServeResult`. If runway dir doesn't exist, return error directing user to build first.

3. Fix `python` → `python3` for macOS compatibility in server spawn.

## Wave 2: Tests (1 agent)

**Files:** `dev/scripts/sbs/tests/pytest/test_clean.py` (NEW), `dev/scripts/sbs/tests/pytest/test_build_staleness.py` (NEW)

**test_clean.py** (`@pytest.mark.evergreen`):
- `test_clean_check_reports_targets` — dry-run returns correct list
- `test_clean_repo_removes_build_dir` — `.lake/build/` removed
- `test_clean_repo_removes_lakefile_olean` — `lakefile.olean` removed
- `test_clean_repo_dry_run_preserves_files` — no deletion in dry run
- `test_clean_repo_full_removes_packages` — `--full` removes `.lake/packages/`
- `test_clean_nonexistent_repo_is_noop` — no error on missing path

**test_build_staleness.py** (`@pytest.mark.evergreen`):
- `test_default_config_does_not_skip` — `BuildConfig().skip_lake is False`
- `test_skip_lake_config` — `BuildConfig(skip_lake=True).skip_lake is True`
- `test_force_lake_deprecated` — old flag triggers warning (if we keep it)

## Wave 3: Validation (sequential)

1. Run evergreen tests: `pytest sbs/tests/pytest -m evergreen --tb=short`
2. Verify `sbs clean --check --project SBSTest` runs without error
3. Verify `python3 build.py --dry-run --verbose` does NOT skip any toolchain repo
4. Verify `python3 build.py --dry-run --verbose --skip-lake` DOES skip
5. Grep for any remaining `force_lake` references (should be zero except deprecated flag handler)

## CLAUDE.md Update

- Replace `--force-lake` references with `--skip-lake`
- Update the "Lean Source Skip" paragraph to describe the inverted default
- Add `sbs clean` to the CLI reference

## Gate Requirements

- All evergreen tests pass (100%)
- `sbs clean --project SBSTest --check` exits 0
- No `force_lake` references remain in non-deprecated code paths
- MCP serve tool paths point to `.lake/build/runway/`

## Files Modified Summary

| File | Change Type | Agent |
|------|------------|-------|
| `dev/scripts/sbs/build/config.py` | Modify | A |
| `dev/scripts/sbs/build/orchestrator.py` | Modify (8 sites) | A |
| `dev/scripts/sbs/commands/clean.py` | NEW | B |
| `dev/scripts/sbs/build/phases.py` | Modify | B |
| `dev/scripts/sbs/cli.py` | Modify | B |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | Modify | C |
| `dev/scripts/sbs/tests/pytest/test_clean.py` | NEW | Wave 2 |
| `dev/scripts/sbs/tests/pytest/test_build_staleness.py` | NEW | Wave 2 |
| `CLAUDE.md` | Modify | Wave 2 |
