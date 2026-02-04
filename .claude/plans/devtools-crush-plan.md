# Devtools Crush: Build System + Meta-Tooling Improvements

**Issues:** #197, #186, #198, #199, #200, #201, #196, #192
**Scope:** Build system reliability, performance optimization, timing instrumentation, tooling cleanup
**Strategy:** 4 sequential waves with parallel agents within waves

---

## Architecture Principles

1. **Incremental by default, clean on demand** - Builds reuse artifacts unless explicitly rebuilding
2. **Fast feedback loops** - CSS-only path + pre-flight validation enable rapid iteration
3. **Measure then optimize** - Instrumentation before optimization
4. **Quality of life** - Fix annoying issues even if low impact

---

## Wave 1: Fix Blockers (CRITICAL)

**Issues:** #197, #186 (duplicate), #198
**Goal:** Eliminate 60% build failure rate + add early validation
**Parallelism:** 2 agents (non-overlapping files)

### Agent 1.1: Fix clean_artifacts Bug (#197, #186)

**Problem:** `clean_artifacts()` removes dressed/ artifacts before skip logic checks them, causing 60% failure rate.

**Files:**
- `dev/scripts/sbs/build/orchestrator.py` (primary)
  - Lines 462-492: `clean_artifacts()` function
  - Lines 240-280: `run()` method calling clean_artifacts
  - Lines 156-175: `_needs_project_build()` skip logic
- `dev/scripts/sbs/build/caching.py`
  - Lines 45-78: `has_dressed_artifacts()` check

**Changes:**
1. Add `--clean` flag support to BuildOrchestrator
2. Make `clean_artifacts()` conditional:
   ```python
   if self.config.force_clean or lake_manifests_changed():
       self.clean_artifacts()
   ```
3. Remove unconditional `clean_artifacts()` call from normal build flow
4. Add cleanup on build failure (for retry scenarios)

**Success Criteria:**
- Normal builds preserve dressed/ artifacts when Lean unchanged
- `--clean` flag forces full cleanup
- Build failure rate drops from 60% to <5%
- Skip logic works correctly (Lean unchanged → skip build)

---

### Agent 1.2: Add Pre-flight Validation (#198)

**Problem:** Builds waste 2+ minutes before discovering missing files or bad state.

**Files:**
- `dev/scripts/sbs/build/orchestrator.py`
  - New function: `_validate_project_structure()` (add before run())
  - Update `run()` to call validation gate

**Changes:**
1. Create `_validate_project_structure()` validation gate:
   ```python
   def _validate_project_structure(self) -> None:
       """Pre-flight checks before expensive operations."""
       # Check git status clean in toolchain repos
       # Check required files exist (runway.json, lakefile.lean)
       # Check Lake manifests parseable
       # Check assets directory exists if specified
   ```
2. Call at start of `run()` before any expensive operations
3. Fail fast with clear error messages
4. Add `--skip-validation` flag for emergency bypasses

**Success Criteria:**
- Missing runway.json caught before build starts
- Dirty git state caught before Lake runs
- Invalid manifests caught before 90s update_manifests phase
- Clear error messages point to fix

---

### Wave 1 Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  test_filter: "test_build or test_orchestrator"
  validation:
    - Build SBSTest with unchanged Lean sources (must skip Lake)
    - Build SBSTest with --clean flag (must run Lake)
    - Trigger pre-flight failures (missing file, dirty git)
  regression: >= 0
```

**Measurement:**
- Baseline: Current build failure rate = 60%
- Target: Build failure rate < 5%
- Method: Run 20 builds with unchanged Lean, count failures

---

## Wave 2: Instrumentation (MEASUREMENT)

**Issues:** #199, #200
**Goal:** Add missing timing categories for optimization decisions
**Parallelism:** 2 agents (non-overlapping files)

### Agent 2.1: Persist Archive Timing Categories (#199)

**Problem:** Archive operations compute timings but don't persist them.

**Files:**
- `dev/scripts/sbs/archive/upload.py`
  - Line ~150: `archive_upload()` function
  - Add timing parameter passing to archive entry creation
- `dev/scripts/sbs/archive/entry.py`
  - Verify ArchiveEntry.archive_timings field exists

**Changes:**
1. Capture timing dict in `upload.py`:
   ```python
   timings = {
       'extraction': extraction_time,
       'porcelain': porcelain_time,
       'tagging': tagging_time,
       'push': push_time
   }
   ```
2. Pass timings to archive entry creation
3. Persist in archive_index.json

**Success Criteria:**
- `archive_timings` field populated in new entries
- Can query timing data via MCP tools
- All 4 categories tracked (extraction, porcelain, tagging, push)

---

### Agent 2.2: QA Evaluation Timing Instrumentation (#200)

**Problem:** QA phase duration unknown, can't optimize converge iterations.

**Files:**
- `dev/scripts/sbs/qa/compliance.py`
  - Add timing to evaluation loop
- `dev/scripts/sbs/qa/capture.py`
  - Add timing to screenshot capture
- `dev/scripts/sbs/build/orchestrator.py`
  - Add qa_timing to phase_timings dict

**Changes:**
1. Add per-page timing in compliance loop:
   ```python
   page_timings = {}
   for page in pages:
       start = time.time()
       navigate(); capture(); evaluate()
       page_timings[page] = time.time() - start
   ```
2. Store in unified_ledger.json under new `qa_timings` field
3. Add to BuildMetrics dataclass
4. Report in build summary

**Success Criteria:**
- Per-page QA timing recorded (navigate, capture, evaluate)
- Total QA phase duration in unified_ledger.json
- Can identify slowest pages for optimization
- Timing accessible via validators

---

### Wave 2 Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  test_filter: "test_archive or test_qa"
  validation:
    - Archive entry has populated archive_timings field
    - QA run produces page-level timing data
    - unified_ledger.json contains qa_timings
  regression: >= 0
```

**Measurement:**
- Archive timings: 4/4 categories populated
- QA timings: Per-page data for all tested pages
- Method: Run build + QA, inspect ledger JSON

---

## Wave 3: Optimization (SPEEDUP)

**Issues:** #201
**Goal:** 5-7x speedup for CSS-only converge iterations
**Parallelism:** 1 agent (complex, touches orchestrator)

### Agent 3.1: CSS-Only Fast Rebuild Path (#201)

**Problem:** CSS changes trigger full 210s rebuild cycle, wasting 180s on unnecessary Lean/Lake operations.

**Files:**
- `dev/scripts/sbs/build/orchestrator.py`
  - New function: `_is_css_only_change()` (detects CSS-only changes)
  - Update `run()` to branch on CSS-only path
- `dev/scripts/sbs/build/config.py`
  - Add css_fast_path boolean flag

**Changes:**
1. Detect CSS-only changes:
   ```python
   def _is_css_only_change(self) -> bool:
       """Check if only CSS files changed since last build."""
       css_files = [
           "dress-blueprint-action/assets/common.css",
           "dress-blueprint-action/assets/blueprint.css",
           "dress-blueprint-action/assets/dep_graph.css",
           "dress-blueprint-action/assets/paper.css"
       ]
       changed = get_changed_files_since_last_build()
       return all(f in css_files for f in changed) and len(changed) > 0
   ```

2. Add fast path branch in `run()`:
   ```python
   if self._is_css_only_change() and not self.config.force_full_build:
       logger.info("CSS-only change detected, using fast path")
       self._start_phase("generate_site")
       self.generate_site()
       self._end_phase("generate_site")

       if self.config.capture:
           self._start_phase("capture")
           self.run_capture()
           self._end_phase("capture")

       # Skip: update_manifests, build_toolchain, build_project, generate_verso
   ```

3. Track CSS file hashes to detect changes
4. Add `--force-full-build` flag to override fast path

**Success Criteria:**
- CSS-only change detected correctly
- Fast path skips Lake/Lean/Verso phases
- Site regenerates with new CSS
- Screenshots reflect CSS changes
- Timing: 210s → 30-45s (5-7x speedup)

---

### Wave 3 Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  test_filter: "test_build"
  validation:
    - Modify only common.css, verify fast path triggers
    - Verify site regenerates with CSS changes
    - Verify screenshots update
    - Time CSS-only build: must be < 60s
  timing:
    css_only_build: < 60s
  regression: >= 0
```

**Measurement:**
- Baseline: CSS change → 210s rebuild
- Target: CSS change → 30-45s rebuild
- Method: Touch CSS file, run build, measure duration

---

## Wave 4: Cleanup (POLISH)

**Issues:** #196, #192
**Goal:** Remove duplicate footers, close non-issue
**Parallelism:** 2 agents (trivial, non-overlapping)

### Agent 4.1: Fix Duplicate Attribution Footers (#196)

**Problem:** `/log` skill and MCP tools both add "Created with Claude Code" footers.

**Files:**
- `.claude/skills/log/SKILL.md`
  - Lines 365-376: Remove footer addition logic
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`
  - Verify MCP tools keep their attribution (no change needed)

**Changes:**
1. Remove footer text from `/log` skill (lines 365-376 in SKILL.md)
2. Let MCP tools handle attribution (sbs_issue_create, sbs_pr_create)
3. Single source of truth: attribution happens in MCP layer only

**Success Criteria:**
- Issues created via `/log` have single footer
- PRs created have single footer
- Attribution still present (from MCP tools)

---

### Agent 4.2: Close SLS Reference Issue (#192)

**Problem:** Issue claims SLS references exist, but exploration found none.

**Files:** None (issue closure only)

**Changes:**
1. Call `sbs_issue_close(number=192, comment="No SLS references found in codebase - already clean. Verified via grep across .md, .py, .lean files.")`

**Success Criteria:**
- Issue #192 closed with explanation

---

### Wave 4 Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  test_filter: "test_skills or test_log"
  validation:
    - Create issue via /log, verify single footer
    - Create PR via sbs_pr_create, verify single footer
  regression: >= 0
```

---

## Deferred Issues

**#195 - User interaction hooks for preference mining**
- Scope: 5-10 issue project (real-time hooks + correlation engine + structured schema)
- ROI unclear without specific use cases
- Current passive capture sufficient
- Action: Keep issue open, revisit in 2-3 months during L2 introspection

---

## Overall Success Metrics

### Reliability
- **Build failure rate:** 60% → <5%
- **Pre-flight catches:** 100% of detectable issues before expensive operations

### Performance
- **CSS-only rebuild:** 210s → 30-45s (5-7x speedup)
- **Normal build:** No regression (same duration ±5%)

### Instrumentation
- **Archive timing coverage:** 4/4 categories populated
- **QA timing coverage:** Per-page data for all tested pages

### Quality of Life
- **Attribution footers:** 0 duplicates
- **Backlog cleanup:** 1 non-issue closed

---

## Test Strategy

### Evergreen Tests
All waves must pass existing evergreen test suite:
```bash
pytest dev/scripts/sbs/tests/pytest -m evergreen --tb=short
```

### Integration Tests (Manual Verification)
1. **Wave 1:** Build SBSTest 20x with unchanged Lean, measure failure rate
2. **Wave 2:** Run build + archive + QA, inspect ledger JSON for timing data
3. **Wave 3:** Touch CSS file, run build, verify <60s duration + correct output
4. **Wave 4:** Create issue via `/log`, verify single footer

---

## Execution Plan

```
Wave 1 (Critical Blockers)
├── Agent 1.1: Fix clean_artifacts (#197, #186)
└── Agent 1.2: Add pre-flight validation (#198)
    └── Gate: Build reliability tests

Wave 2 (Measurement)
├── Agent 2.1: Archive timing persistence (#199)
└── Agent 2.2: QA timing instrumentation (#200)
    └── Gate: Timing data validation

Wave 3 (Optimization)
└── Agent 3.1: CSS fast rebuild path (#201)
    └── Gate: Performance validation (<60s)

Wave 4 (Cleanup)
├── Agent 4.1: Fix duplicate footers (#196)
└── Agent 4.2: Close #192
    └── Gate: Quality checks
```

**Total agents:** 7
**Parallelism:** Up to 2 concurrent agents per wave
**Estimated scope:** ~400 lines of new code, ~50 lines removed

---

## Files Modified Summary

| Repository | Files Changed | Lines Added | Lines Removed |
|------------|---------------|-------------|---------------|
| dev/scripts | orchestrator.py, caching.py, upload.py, compliance.py, capture.py | ~350 | ~20 |
| .claude/skills | log/SKILL.md | 0 | ~15 |
| forks/sbs-lsp-mcp | (verification only, no changes) | 0 | 0 |

**Total:** 6 files modified, ~350 LOC added, ~35 LOC removed
