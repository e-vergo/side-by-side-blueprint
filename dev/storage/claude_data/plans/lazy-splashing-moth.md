# Plan: Mathlib Compliance Review of All Crystallographic Files

## Objective

Review all 10 Lean files in `Crystallographic/` for Mathlib compliance and update `MATHLIB_SUBMISSION_PLAN.md` with findings.

## Files to Review (10 total, ~2,983 lines)

| File | Lines | Module |
|------|-------|--------|
| `Companion/Basic.lean` | 606 | Companion matrix definitions |
| `Companion/Cyclotomic.lean` | 203 | Cyclotomic companions |
| `FiniteOrder/Basic.lean` | 234 | Integer matrix orders |
| `FiniteOrder/Order.lean` | 99 | Order lemmas |
| `Psi/Basic.lean` | 275 | Psi function definition |
| `Psi/Bounds.lean` | 472 | Psi bounds |
| `CrystallographicRestriction/Forward.lean` | 303 | Forward direction |
| `CrystallographicRestriction/Backward.lean` | 454 | Backward direction |
| `Main/MainTheorem.lean` | 77 | Main theorem |
| `Main/Lemmas.lean` | 260 | Supporting lemmas |

## Execution Strategy

### Phase 1: Review Batch 1 (4 agents in parallel)
Launch mathlib-compliance-reviewer for:
1. `Companion/Basic.lean` (largest, 606 lines)
2. `Companion/Cyclotomic.lean` (203 lines)
3. `FiniteOrder/Basic.lean` (234 lines)
4. `FiniteOrder/Order.lean` (99 lines)

### Phase 2: Review Batch 2 (4 agents in parallel)
Launch mathlib-compliance-reviewer for:
5. `Psi/Basic.lean` (275 lines)
6. `Psi/Bounds.lean` (472 lines)
7. `CrystallographicRestriction/Forward.lean` (303 lines)
8. `CrystallographicRestriction/Backward.lean` (454 lines)

### Phase 3: Review Batch 3 (2 agents in parallel)
Launch mathlib-compliance-reviewer for:
9. `Main/MainTheorem.lean` (77 lines)
10. `Main/Lemmas.lean` (260 lines)

### Phase 4: Consolidate & Update
1. Collect all review findings
2. Categorize issues by severity (Critical/Required/Suggested)
3. Cross-reference with existing MATHLIB_SUBMISSION_PLAN.md tiers
4. Update MATHLIB_SUBMISSION_PLAN.md with:
   - Per-file compliance status
   - Blocking issues for Mathlib submission
   - Prioritized fix list
   - Updated readiness assessment for each tier

## Expected Output in MATHLIB_SUBMISSION_PLAN.md

Add new section: **Compliance Review Results (DATE)**

```markdown
## Compliance Review Results

### File-by-File Status

| File | Status | Critical | Required | Suggested |
|------|--------|----------|----------|-----------|
| ... | Ready/Needs Work | N | N | N |

### Blocking Issues (Must Fix Before Submission)
- Issue 1: File.lean - description
- ...

### Recommended Fixes (Should Fix)
- ...

### Tier Readiness Assessment
- Tier 1: X/Y lemmas ready
- Tier 2: X/Y lemmas ready
- ...
```

## Verification

1. All 10 files reviewed
2. MATHLIB_SUBMISSION_PLAN.md updated with compliance findings
3. Clear action items identified for each tier
