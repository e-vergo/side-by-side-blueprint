# Timing Instrumentation Plan for GCR Build

## Objective
Capture accurate timing data to understand where build time is spent, especially for artifact generation phases.

## Current State Assessment

### Existing Timing Infrastructure (Already Good)
The build orchestrator (`dev/scripts/sbs/build/orchestrator.py`) has comprehensive phase-level timing via `_start_phase`/`_end_phase` that logs to `unified_ledger.json`.

**15 phases currently tracked:**
- validation, sync_repos, update_manifests, compliance_checks, quality_validators
- clean_build, build_toolchain, fetch_mathlib_cache, build_project, build_blueprint
- generate_verso, build_dep_graph, generate_site, final_sync, start_server, capture

### Historical Data Analysis

**ReductiveGroups (54s total, cached Lake):**
| Phase | Time | % |
|-------|------|---|
| build_dep_graph | 24.0s | 44.5% |
| fetch_mathlib_cache | 11.5s | 21.3% |
| build_project | 4.5s | 8.3% |
| sync_repos | 3.8s | 7.0% |
| generate_verso | 2.7s | 5.0% |
| generate_site | 2.6s | 4.8% |
| Others | <5s | <10% |

**SBSTest (93s total):**
| Phase | Time | % |
|-------|------|---|
| generate_verso | 65.1s | 70% |
| generate_site | 14.5s | 15.6% |
| build_dep_graph | 6.3s | 6.8% |

### Key Insight
**`build_dep_graph` is the primary bottleneck** when Lake artifacts are cached. For ReductiveGroups it takes 24s (44.5% of build time).

## What `build_dep_graph` Does Internally

The `extract_blueprint graph` command (`Dress/Main.lean`) runs these operations sequentially:
1. **runEnvOfImports** - Load Lean environment with all modules
2. **Graph.fromEnvironment** - Build graph from blueprint nodes
3. **graph.transitiveReduction** - O(n^3) Floyd-Warshall algorithm
4. **Graph.Layout.layout** - Sugiyama algorithm (~O(n^2))
5. **Graph.Svg.renderToFile** - SVG generation
6. **Graph.writeJsonFile** - JSON serialization
7. **Manifest JSON write**

Currently NO timing traces exist inside this code path.

## Execution Plan

### Step 1: Run GCR Build with Verbose Mode
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/showcase/GCR
python ../../dev/scripts/build.py --verbose
```

This will:
- Capture all phase timings to unified_ledger.json
- Print timing breakdown at the end
- GCR has cached Lake artifacts, so we'll see the "steady state" timing

### Step 2: Capture and Report Timing Breakdown

From the build output and ledger, report:
- Total build time
- Time per phase
- Which phases are cacheable vs must-run-every-time
- Comparison with historical data

### Step 3: (Future) Add Sub-Phase Timing to Lean Executables

**Not doing now**, but for future reference:
- Add `IO.getCurrentTime` calls around each operation in `runGraphCmd`
- Add similar timing to Runway's `runBuild` function
- Output timing JSON that the orchestrator can parse and record

## Expected Findings

Based on historical data, expect:
- **Total time**: ~5-7 minutes for GCR
- **Lake build**: Fast (cached mathlib artifacts)
- **Artifact generation**: ~30-60s
- **Graph generation**: ~20-30s (the expensive part)
- **Site generation**: ~5-15s

## Key Questions to Answer

1. How much of `build_dep_graph` is:
   - Environment loading?
   - Graph construction?
   - Transitive reduction?
   - Layout algorithm?
   - SVG/JSON writing?

2. What's cacheable?
   - Transitive reduction result (same graph = same result)
   - Layout coordinates (deterministic for same graph)
   - SVG rendering (deterministic for same layout)

3. What MUST run every time?
   - Graph construction (depends on Lean code)
   - Asset copying (fast anyway)
   - Final git sync
