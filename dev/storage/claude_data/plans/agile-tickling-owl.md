# Plan: Clear All Sorry Statements

## Overview

~150 sorry statements across 15 files. Work will be orchestrated with 2 agents working in parallel on independent files at each phase.

---

## Dependency Order

```
FiniteO2Classification.lean (2)
        ↓
PointGroups.lean (8)
        ↓
BravaisTypes.lean (2)    Definition.lean (8)
        ↓                       ↓
        └──────→ Structure.lean (9) ←──────┘
                       ↓
    ┌──────────────────┼──────────────────┐
    ↓                  ↓                  ↓
Groups/*.lean    Classification/*.lean   Wallpaper proofs
```

Independent files that can be done anytime:
- Basic.lean (2) - basis construction
- Parametric.lean (1) - N-dimensional generalization

---

## Execution Phases

### Phase 1: Foundation (2 parallel agents)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | FiniteO2Classification.lean | 2 | CRITICAL BLOCKER - finite subgroup classification |
| B | Basic.lean | 2 | Basis span/linear independence |

### Phase 2: Point Groups (2 parallel agents)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | PointGroups.lean | 8 | Crystallographic restriction applications |
| B | Parametric.lean | 1 | Quotient compactness |

### Phase 3: Definitions (2 parallel agents)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | Definition.lean | 8 | Translation lattice extraction |
| B | BravaisTypes.lean | 2 | Lattice classification |

### Phase 4: Structure (1 agent, dependency bottleneck)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | Structure.lean | 9 | Depends on Definition + PointGroups |

### Phase 5: Simple Groups (2 parallel agents)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | Oblique.lean | 3 | p1, p2 - simplest groups |
| B | CenteredRectangular.lean | 3 | cm, cmm - nearly complete |

### Phase 6: Complex Groups Batch 1 (2 parallel agents)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | Square.lean | 17 | p4, p4m, p4g |
| B | Hexagonal.lean | 34 | p3, p3m1, p31m, p6, p6m |

### Phase 7: Complex Groups Batch 2 (1 agent)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | Rectangular.lean | 24 | pm, pg, pmm, pmg, pgg - glide reflections |

### Phase 8: Classification (2 parallel, then 1)
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | Verification.lean | 19 | isWallpaperGroup theorem stubs |
| B | Distinctness.lean | 9 | Non-isomorphism proofs |

Then:
| Agent | File | Sorries | Notes |
|-------|------|---------|-------|
| A | Completeness.lean | 7 | Final completeness theorem |

---

## Common Patterns (Batch-Solvable)

1. **properlyDiscontinuous** (~9 occurrences)
   - All follow same pattern: lattice discreteness argument
   - Can template once, apply to all groups

2. **Cocompact fundamental domain** (~12 occurrences)
   - Pattern: `latticeFundamentalDomain Λ B` is compact + covers
   - Two sorries per group, nearly identical

3. **isSymmorphic for symmorphic groups** (~8 occurrences)
   - Pattern: section `s(A) = (0, A)`
   - Straightforward once infrastructure exists

4. **Lattice preservation under action** (~6 occurrences)
   - Pattern: `A ∈ PointGroup ∧ v ∈ Λ ⟹ A(v) ∈ Λ`
   - Prove for each point group: C₂, C₃, C₄, C₆, D₁, D₂, D₃, D₄, D₆

---

## Files Summary

| File | Sorries | Phase | Complexity |
|------|---------|-------|------------|
| FiniteO2Classification.lean | 2 | 1 | Complex |
| Basic.lean | 2 | 1 | Medium |
| PointGroups.lean | 8 | 2 | Medium |
| Parametric.lean | 1 | 2 | Medium |
| Definition.lean | 8 | 3 | Medium-Complex |
| BravaisTypes.lean | 2 | 3 | Complex |
| Structure.lean | 9 | 4 | Medium |
| Oblique.lean | 3 | 5 | Easy |
| CenteredRectangular.lean | 3 | 5 | Easy |
| Square.lean | 17 | 6 | Medium |
| Hexagonal.lean | 34 | 6 | Medium |
| Rectangular.lean | 24 | 7 | Complex |
| Verification.lean | 19 | 8 | Easy (stubs) |
| Distinctness.lean | 9 | 8 | Medium |
| Completeness.lean | 7 | 8 | Medium |
| **TOTAL** | **148** | | |

---

## Agent Instructions Template

Each agent will receive:
1. Full file path
2. List of sorry locations with line numbers
3. Instructions to:
   - Read all imports first
   - Use MCP tools: `lean_goal`, `lean_diagnostic_messages`, `lean_hover_info`
   - Search for lemmas: `lean_leansearch`, `lean_loogle`, `lean_local_search`
   - Test each proof step immediately
   - Never use axioms or sorry replacements
   - Report back when complete or blocked

---

## Verification

After each phase:
1. Run `lake build` - must pass with no new errors
2. Check sorry count decreased: `grep -r "sorry" WallpaperGroups/ | wc -l`

After all phases:
1. `lake build` passes with 0 sorry warnings
2. `./deploy.sh` regenerates docs
3. Dependency graph shows all theorems connected

---

## Risk Mitigation

- If an agent gets stuck on a complex sorry, it should:
  1. Document the blocker clearly
  2. Move to next sorry in same file
  3. Report back for human review

- If a phase has dependency issues:
  1. Pause dependent phase
  2. Complete blocking phase first
  3. Resume with updated context
