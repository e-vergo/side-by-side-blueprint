# Plan: Wall-Clock Time Optimization (#155)

## Summary

Instrument all workflows with timing, skip stable Lake builds, make iCloud sync async, parallelize git pushes. Extends existing infrastructure (no new systems).

## Waves

### Wave 1: Foundation (3 parallel agents)

**Agent A — Timing utilities + ArchiveEntry extension**
- Create `dev/scripts/sbs/core/timing.py`: `TimingContext` context manager, `format_duration()`, `timing_summary()`
- Edit `dev/scripts/sbs/archive/entry.py`: Add `archive_timings: dict[str, float]` field, update `to_dict()` and `from_dict()`

**Agent B — Build config + CLI flags**
- Edit `dev/scripts/sbs/build/config.py`: Add `force_lake: bool = False` to `BuildConfig`
- Edit `dev/scripts/sbs/build/orchestrator.py`: Add `--force-lake` arg in `parse_args()`, wire to config

**Agent C — Lean source detection + extended caching**
- Edit `dev/scripts/sbs/build/caching.py`: Add `get_lean_sources_hash(repo_path)` using `git diff --name-only` for fast detection, fallback to hashing `.lean` files. Add `has_lean_changes(repo_path, cache_dir)` that checks hash against last-cached value. Extend `get_cache_key()` to optionally include lean sources hash. Add `save_lean_hash()` / `load_lean_hash()` for persistent state in `.cache/<repo>/lean_hash`

### Wave 2: Core Optimizations (3 parallel agents)

**Agent D — Lake skip logic in orchestrator**
- Edit `dev/scripts/sbs/build/orchestrator.py`:
  - `build_toolchain()`: Before each repo build, check `has_lean_changes()`. Skip if unchanged and `not config.force_lake`. Log skip reason.
  - `_build_project_internal()`: Same check before `build_project_with_dress()`
  - Blueprint build: Same check before `lake build :blueprint`
  - `fetch_mathlib_cache()`: Skip if no lean changes (cache already fetched)
  - `update_manifests()`: Skip if no lean changes (manifests stable)
  - After successful build, call `save_lean_hash()` for each repo

**Agent E — Async iCloud + timing instrumentation in upload**
- Edit `dev/scripts/sbs/archive/icloud_sync.py`: Add `async_full_sync()` — launches `full_sync()` in a daemon thread, returns immediately
- Edit `dev/scripts/sbs/archive/upload.py`:
  - Import and use `TimingContext` to wrap each step in `archive_upload()`: `extraction`, `entry_creation`, `quality_scores`, `repo_commits`, `tagging`, `gate_validation`, `index_save`, `icloud_sync`, `porcelain`
  - Set `entry.archive_timings = archive_timings` before save
  - Replace `full_sync()` call (line 621) with `async_full_sync()` — fire-and-forget
  - Log timing summary at end of upload

**Agent F — Parallel git pushes**
- Edit `dev/scripts/sbs/archive/upload.py` (`ensure_porcelain()` function, lines 211-265):
  - Phase 1: Scan repos (unchanged)
  - Phase 2: Commit dirty repos (sequential — needed for correctness)
  - Phase 3: Push submodules in parallel via `ThreadPoolExecutor(max_workers=4)`
  - Phase 4: Push main repo last (after joining all threads)
  - Collect and report errors from all threads

**Note:** Agents E and F both edit `upload.py` but touch different functions. Agent E modifies `archive_upload()` (lines 345-645). Agent F modifies `ensure_porcelain()` (lines 211-265). Non-overlapping.

### Wave 3: Validators, Tests, Viz (2 parallel agents)

**Agent G — Tests + validator extension**
- Edit `dev/scripts/sbs/tests/validators/timing.py`: Extend `validate()` to also consume `archive_timings` from `context.extra`, merge into unified metrics
- Create `dev/scripts/sbs/tests/pytest/test_timing_optimization.py` (evergreen):
  - `test_timing_context_basic` — context manager records duration
  - `test_timing_context_exception` — records even on exception
  - `test_format_duration` — human-readable formatting
  - `test_lean_sources_hash` — returns hash for real repo dir
  - `test_has_lean_changes_no_changes` — returns False when hash matches
  - `test_archive_entry_timings_roundtrip` — to_dict/from_dict preserves archive_timings
  - `test_archive_timings_default_empty` — old entries deserialize with empty dict

**Agent H — Visualization + docs**
- Edit `dev/scripts/sbs/archive/visualizations.py`: Add `generate_archive_timing_chart()` — stacked bar chart of archive upload phase timings across recent entries
- Edit `dev/storage/README.md`: Document `--force-lake` flag, async iCloud behavior, `archive_timings` field

## Files Modified

| File | Wave | Change |
|------|------|--------|
| `sbs/core/timing.py` | 1A | NEW — TimingContext, format_duration, timing_summary |
| `sbs/archive/entry.py` | 1A | Add archive_timings field + serialization |
| `sbs/build/config.py` | 1B | Add force_lake to BuildConfig |
| `sbs/build/orchestrator.py` | 1B, 2D | CLI flag + skip logic in 5 phases |
| `sbs/build/caching.py` | 1C | Lean source hash detection + persistence |
| `sbs/archive/icloud_sync.py` | 2E | Add async_full_sync() |
| `sbs/archive/upload.py` | 2E, 2F | Timing instrumentation + parallel pushes |
| `sbs/tests/validators/timing.py` | 3G | Consume archive_timings |
| `sbs/tests/pytest/test_timing_optimization.py` | 3G | NEW — evergreen tests |
| `sbs/archive/visualizations.py` | 3H | Archive timing chart |
| `dev/storage/README.md` | 3H | Updated docs |

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

After each wave: `pytest sbs/tests/pytest -m evergreen --tb=short`

## Success Criteria

- Lake builds skipped when no `.lean` changes (log message confirms skip)
- `--force-lake` overrides skip logic
- iCloud sync non-blocking (archive_upload returns before sync completes)
- Git pushes parallelized (4 workers, main repo last)
- Every archive entry has `archive_timings` dict with per-step durations
- TimingValidator consumes both `phase_timings` and `archive_timings`
- Archive timing chart generates
- All evergreen tests pass

## Verification

1. `python build.py --help` shows `--force-lake`
2. `python build.py` with no Lean changes: skips Lake phases, logs reasons
3. `python build.py --force-lake`: forces Lake builds
4. `sbs archive upload --trigger manual`: completes with timing data, returns before iCloud finishes
5. Archive entry in `archive_index.json` has `archive_timings` populated
6. `pytest sbs/tests/pytest -m evergreen -v` passes 100%
