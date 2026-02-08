# Plan: Clear All 158 Sorries via Parallel Agent Orchestration

## Configuration
- **Parallelism**: 2-3 agents at a time
- **Scope**: All 158 sorries
- **Stuck policy**: Exhaust all search tools and tactics before escalating

## Sorry Distribution

| File | Count | Phase |
|------|-------|-------|
| Wallpaper/Definition.lean | 7 | 1 |
| Wallpaper/Structure.lean | 9 | 1 |
| Lattice/BravaisTypes.lean | 5 | 1 |
| Groups/Oblique.lean | 3 | 2 |
| Groups/Rectangular.lean | 26 | 2 |
| Groups/CenteredRectangular.lean | 13 | 2 |
| Groups/Square.lean | 19 | 2 |
| Groups/Hexagonal.lean | 35 | 2 |
| Crystallographic/PointGroups.lean | 7 | 2 |
| Classification/Verification.lean | 18 | 3 |
| Classification/Distinctness.lean | 9 | 3 |
| Classification/Completeness.lean | 7 | 3 |

## Execution Plan

### Phase 1: Foundation (21 sorries)
These files provide infrastructure needed by Groups and Classification.

**Batch 1.1** (2 agents parallel):
- Agent A: `Wallpaper/Definition.lean` (7 sorries)
- Agent B: `Lattice/BravaisTypes.lean` (5 sorries)

**Batch 1.2** (1 agent, depends on 1.1):
- Agent C: `Wallpaper/Structure.lean` (9 sorries)

**Checkpoint**: `lake build`, verify no regressions

### Phase 2: Groups + Crystallography (103 sorries)
Groups files are independent of each other. Process in batches of 2-3.

**Batch 2.1** (3 agents parallel):
- Agent D: `Groups/Oblique.lean` (3 sorries) - smallest, quick win
- Agent E: `Crystallographic/PointGroups.lean` (7 sorries)
- Agent F: `Groups/CenteredRectangular.lean` (13 sorries)

**Batch 2.2** (2 agents parallel):
- Agent G: `Groups/Square.lean` (19 sorries)
- Agent H: `Groups/Rectangular.lean` (26 sorries)

**Batch 2.3** (1 agent, largest file):
- Agent I: `Groups/Hexagonal.lean` (35 sorries)

**Checkpoint**: `lake build`, verify no regressions

### Phase 3: Classification (34 sorries)
Depends on all Groups files being complete.

**Batch 3.1** (2 agents parallel):
- Agent J: `Classification/Verification.lean` (18 sorries)
- Agent K: `Classification/Distinctness.lean` (9 sorries)

**Batch 3.2** (1 agent, final):
- Agent L: `Classification/Completeness.lean` (7 sorries)

**Final verification**: `lake build`, `grep -r "sorry" WallpaperGroups/`

## Agent Protocol

Each agent receives these instructions:

### Before Starting
1. Read the target file completely
2. Read ALL local imports (use `lean_file_outline` for efficiency)
3. Use `lean_local_search` to understand available lemmas

### During Proof Work
1. Work directly in the actual file (no scratch files)
2. Check `lean_diagnostic_messages` after every edit
3. Use `lean_goal` to understand proof state before writing tactics
4. Try automation first: `grind`, `simp?`, `exact?`, `apply?`, `omega`
5. Use `lean_multi_attempt` to test multiple tactics without editing
6. Search for lemmas: `lean_leansearch`, `lean_loogle`, `lean_leanfinder`
7. When stuck: `lean_state_search`, `lean_hammer_premise`

### When Stuck
1. Try `grind` with various options (`grind?`, `grind (splits := 10)`)
2. Use all search tools to find relevant Mathlib lemmas
3. Break into smaller helper lemmas if needed
4. Document the specific blocker in a comment but DO NOT leave sorry
5. If truly blocked after exhaustive attempts, report specific error and goal state

### Never
- Introduce new sorries
- Delete partial progress
- Skip diagnostic checks
- Give up without trying all tactics and search tools

## Critical Files to Read First

Agents must read these imports to understand the project:

```
WallpaperGroups/Basic.lean
WallpaperGroups/Euclidean/Plane.lean
WallpaperGroups/Euclidean/EuclideanGroup.lean
WallpaperGroups/Lattice/Basic.lean
WallpaperGroups/Wallpaper/Definition.lean (after Phase 1)
WallpaperGroups/Wallpaper/Structure.lean (after Phase 1)
```

## Verification Criteria

After each batch:
1. `lake build` succeeds with no errors
2. `grep -r "sorry" <modified_files>` returns nothing
3. `lean_diagnostic_messages` shows no errors for modified files

Final success criteria:
- `grep -rn "sorry" WallpaperGroups/` returns no results
- `lake build` completes successfully
- All 17 wallpaper groups verified
