# SBS Rewrite Wave 1-2 Execution Plan

## Overview

Execute issues #225-229 (Waves 1-2 of #224) via sequential agent orchestration, then validate with a testing agent.

## Baseline Timing (GCR, 61 nodes, Lake cached)

| Phase | Time | % | Notes |
|-------|------|---|-------|
| **build_dep_graph** | **24.1s** | **56.2%** | PRIMARY BOTTLENECK |
| generate_verso | 7.9s | 18.4% | Verso doc generation |
| sync_repos | 5.7s | 13.3% | Git operations |
| generate_site | 3.6s | 8.4% | Runway HTML |
| start_server | 1.0s | 2.3% | HTTP server |
| Lake build phases | <0.1s | <0.5% | Already cached |
| **Total** | **42.9s** | 100% | |

**Key insight**: `build_dep_graph` (extract_blueprint graph) takes 24 seconds and runs every build. This is where caching has the most impact.

## Execution Model

**Orchestrator** (top-level chat): Spawns one `sbs-developer` agent per issue, waits for completion, then spawns next.

**Each agent**: Implements its issue, may spawn parallel subagents for non-overlapping work.

**Final agent**: Runs comprehensive testing to validate build time improvements.

---

## Agent 1: Graph Output Cache (#225)

**Scope**: `dev/scripts/sbs/build/caching.py` + `orchestrator.py`

**Target**: Skip 24.1s `build_dep_graph` when graph unchanged OR when not needed

**The Problem**: `extract_blueprint graph` runs every build and takes 24s. It:
- Loads Lean environment
- Constructs graph from @[blueprint] nodes
- Runs O(n³) transitive reduction
- Runs Sugiyama layout algorithm
- Writes SVG + JSON + manifest

**Two-Pronged Solution**:

### A. `--skip-graph` Flag (for dev iteration)
Add CLI flag to skip graph generation entirely. Useful when:
- Working on CSS/styling
- Working on non-graph site features
- Rapid iteration where graph is irrelevant

```bash
python build.py --skip-graph  # Skip graph generation entirely
```

### B. Graph Cache (for normal builds)
Hash the INPUT (manifest.json from Lake build), cache the OUTPUT (dep-graph.json, dep-graph.svg).

**Implementation**:
1. Add `--skip-graph` flag to build.py argparse
2. If `--skip-graph`: skip `generate_dep_graph()` phase entirely
3. Otherwise: check graph cache before generation
4. Cache key: SHA256 of manifest.json content
5. Cache hit: copy cached files, skip generation
6. Cache miss: run normally, save outputs to cache

**Cache Location**: `.lake/build/dressed/.graph_cache/{manifest_hash}/`
```
.graph_cache/
└── {hash}/
    ├── dep-graph.json
    ├── dep-graph.svg
    └── manifest.json  (copy for verification)
```

**Files Modified**:
- `dev/scripts/sbs/build/caching.py` (add graph cache functions)
- `dev/scripts/sbs/build/orchestrator.py` (add --skip-graph flag, integrate cache)

---

## Agent 2: Asset Pipeline Optimization (#226)

**Scope**: `dev/scripts/sbs/build/caching.py` + `orchestrator.py`

**Implementation**:
1. Add `get_asset_hashes(assets_dir)` → dict of filename → SHA256
2. Add `load_asset_hash_cache(cache_path)` / `save_asset_hash_cache()`
3. In asset copy phase:
   - Compare current hashes vs cached
   - Skip unchanged files
   - Update cache after copy

**Cache Location**: `{cache_dir}/{project}/asset_hashes.json`

**Files Modified**:
- `dev/scripts/sbs/build/caching.py` (add asset hash functions)
- `dev/scripts/sbs/build/orchestrator.py` (integrate into asset copy)

---

## Agent 3: Unified Configuration (#227)

**Scope**: `toolchain/Runway/Runway/Config.lean` + `dev/scripts/sbs/build/config.py`

**Implementation**:
1. Extend `Config` struct with optional fields:
   ```lean
   workflow : Option String := none  -- "lean-first" | "paper-first" | "hybrid"
   statementSource : Option String := none  -- "delimiters" | "attribute" | "both"
   validation : Option ValidationConfig := none
   ```
2. Add `ValidationConfig` structure:
   ```lean
   structure ValidationConfig where
     statementMatch : Bool := true
     dependencyCheck : Bool := true
     paperCompleteness : Bool := true
   ```
3. Update FromJson/ToJson instances
4. Python config.py: Parse and expose new fields

**Files Modified**:
- `toolchain/Runway/Runway/Config.lean` (extend schema)
- `dev/scripts/sbs/build/config.py` (parse new fields)

---

## Agent 4: Per-Declaration Content Cache (#228)

**Scope**: `toolchain/Dress/` (Lean) + `dev/scripts/sbs/build/caching.py` (Python)

**This is the most complex task - agent may spawn subagents for Lean vs Python work.**

**Implementation**:

**Lean side** (`toolchain/Dress/Dress/Cache.lean` - new file):
1. `computeDeclarationHash(name, node, subversoVersion)` → content hash
2. `getCachePath(hash)` → cache directory path
3. `checkCache(hash)` → returns cached artifacts if valid
4. `writeToCache(hash, artifacts)` → persist artifacts

**Lean side** (`Dress/Generate/Declaration.lean` - modify):
1. Before generation: compute hash, check cache
2. If hit: copy from cache, skip generation
3. If miss: generate normally, save to cache

**Cache structure**:
```
.lake/build/dressed/.decl_cache/
├── index.json              # label -> hash mapping
└── {content_hash}/
    ├── decl.json
    ├── decl.tex
    ├── decl.html
    └── decl.hovers.json
```

**Files Modified**:
- `toolchain/Dress/Dress/Cache.lean` (new)
- `toolchain/Dress/Dress/Generate/Declaration.lean` (integrate cache)
- `toolchain/Dress/Dress.lean` (import Cache)

---

## Agent 5: JSON Schema Stabilization (#229)

**Scope**: `dev/schemas/` (new directory)

**Implementation**:
1. Create JSON Schema files based on exploration findings:
   - `manifest.schema.json` - stats, nodes, messages, projectNotes, keyDeclarations, checks
   - `dep-graph.schema.json` - width, height, nodes[], edges[]
   - `declaration.schema.json` - name, label, highlighting
   - `hovers.schema.json` - hovers map

2. Add optional schema validation to build.py:
   ```python
   def validate_artifact(artifact_path, schema_name):
       # Optional: validate JSON against schema
   ```

3. Document schemas in `dev/schemas/README.md`

**Files Created**:
- `dev/schemas/manifest.schema.json`
- `dev/schemas/dep-graph.schema.json`
- `dev/schemas/declaration.schema.json`
- `dev/schemas/hovers.schema.json`
- `dev/schemas/README.md`

---

## Agent 6: Validation & Testing

**Scope**: Validate all changes work together

**Testing Protocol**:
1. Run evergreen tests: `pytest sbs/tests/pytest -m evergreen`
2. Build GCR (has 61 nodes, good test case)
3. Measure build times:
   - Full build (clean cache)
   - Incremental build (graph cache hit)
   - After CSS-only change
4. Validate site generation works
5. Run `sbs compliance --project GCR`

**Success Criteria** (GCR baseline: 42.9s):
| Scenario | Before | Target | Savings |
|----------|--------|--------|---------|
| `--skip-graph` flag | 42.9s | ~18s | 24s (skip build_dep_graph) |
| Graph cache hit | 42.9s | ~18s | 24s (cached graph) |
| CSS-only change | 42.9s | ~5s | 37s (fast path) |
| Full rebuild | 42.9s | ~40s | 3s (asset skip) |

---

## Execution Order

```
Orchestrator
    │
    ├── Agent 1: #225 Manifest Hash Cache
    │   └── (single agent, Python only)
    │
    ├── Agent 2: #226 Asset Pipeline
    │   └── (single agent, Python only)
    │
    ├── Agent 3: #227 Unified Config
    │   └── (may spawn: Lean subagent + Python subagent)
    │
    ├── Agent 4: #228 Per-Declaration Cache
    │   └── (will spawn: Lean subagent + Python subagent)
    │
    ├── Agent 5: #229 JSON Schemas
    │   └── (single agent, schema files only)
    │
    └── Agent 6: Testing & Validation
        └── (single agent, runs tests + benchmarks)
```

---

## Critical Files Summary

**Python Build Layer** (`dev/scripts/sbs/build/`):
- `caching.py` - Core caching logic (Agents 1, 2)
- `orchestrator.py` - Build flow (Agents 1, 2)
- `config.py` - Configuration parsing (Agent 3)

**Lean Layer**:
- `toolchain/Runway/Runway/Config.lean` - Config schema (Agent 3)
- `toolchain/Dress/Dress/Cache.lean` - New cache module (Agent 4)
- `toolchain/Dress/Dress/Generate/Declaration.lean` - Declaration gen (Agent 4)

**New Files**:
- `dev/schemas/*.schema.json` - JSON schemas (Agent 5)

---

## Verification

After all agents complete:
1. All pytest tests pass
2. GCR builds successfully with timing logged
3. Build times meet targets:
   - Graph cache hit: ~18s (was 42.9s)
   - Full rebuild: <45s
4. Compliance check passes
5. No regressions in visual output

---

## Priority Order by Impact

Based on timing analysis, the agents are ordered by expected savings:

| Agent | Issue | Target Phase | Savings |
|-------|-------|--------------|---------|
| 1 | #225 | build_dep_graph (24.1s) | **~24s** |
| 2 | #226 | Asset copying | ~0.1s |
| 3 | #227 | Config (enabler) | 0s |
| 4 | #228 | Per-decl generation | ~2-5s |
| 5 | #229 | Schemas (infra) | 0s |

**Agent 1 is the highest impact** - skipping `build_dep_graph` saves 24 seconds per build.
