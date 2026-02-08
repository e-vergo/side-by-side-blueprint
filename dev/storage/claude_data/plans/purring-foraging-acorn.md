# Plan: Replace Custom Code with Mathlib Infrastructure

## Objective
Comprehensive review of the General_Crystallographic_Restriction codebase to identify custom code that can be replaced with existing Mathlib infrastructure.

---

## Executive Summary

After extensive investigation with multiple search agents, **only 2 clear duplicates** were found that should be replaced. The codebase is well-structured and makes appropriate use of Mathlib. Most custom code is either domain-specific or uses different design patterns than Mathlib (e.g., Sum types vs Product types).

---

## CONFIRMED DUPLICATES (Must Replace)

### 1. `lcm_eq_mul_of_coprime`
**Location:** `Definitions/IntegerMatrixOrder.lean:264`
**Mathlib:** `Nat.Coprime.lcm_eq_mul` in `Mathlib.Data.Nat.GCD.Basic`
**Action:** Delete custom lemma, use `h.lcm_eq_mul` at call sites

### 2. `orderOf_pow_of_dvd`
**Location:** `Definitions/IntegerMatrixOrder.lean:190`
**Mathlib:** `orderOf_pow_of_dvd` in `Mathlib.GroupTheory.OrderOfElement`
**Action:** Delete custom lemma, update call sites to Mathlib version

---

## KEEP AS-IS (After Investigation)

### blockDiag2 Infrastructure
**Investigation Result:** KEEP
**Reason:**
- Uses **Sum types** (`Fin M ⊕ Fin K`) optimized for 2-block composition
- Mathlib's `blockDiagonal` uses **Product types** (`m × o`) for repetitive structures
- The critical `orderOf_blockDiag2` lemma has **no Mathlib equivalent**
- Well-integrated with `Matrix.fromBlocks` (which IS Mathlib)
- Converting would require extensive reindexing with uncertain benefit

### permMatrix Lemmas (`permMatrix_one'`, `permMatrix_mul'`, `permMatrix_pow'`, etc.)
**Investigation Result:** KEEP
**Reason:**
- These derive from `PEquiv.toMatrix_trans` and related infrastructure
- `orderOf_permMatrix'` is custom - no Mathlib equivalent
- Clean, short proofs that serve the domain-specific use case
- Would need to contribute to Mathlib rather than replace

### Custom Infrastructure (Domain-Specific)
| Item | Reason to Keep |
|------|----------------|
| `companion` matrix | Not in Mathlib, central to crystallographic proof |
| `psi` / `psiPrimePow` | Domain-specific to crystallographic restriction |
| `integerMatrixOrders` | Custom set definition |
| `cyclotomic_finset_product_dvd` | Custom coprimality reasoning |
| `orderOf_finRotate` | Custom lemma about finRotate order |
| `sum_totient_ge_psi_of_lcm_eq` | Core domain lemma |
| Rotation matrices | Concrete instances |
| `finSumEquiv` | Already wraps Mathlib's `finSumFinEquiv` |

---

## POTENTIAL CONTRIBUTIONS TO MATHLIB

These lemmas are well-written and could benefit the broader community:

1. **`orderOf_blockDiag2`** - Order of block diagonal is LCM of orders
2. **`orderOf_permMatrix'`** - Order of permutation matrix equals order of permutation
3. **`orderOf_finRotate`** - finRotate permutation has order n
4. **`companion_charpoly`** - Characteristic polynomial of companion matrix

---

## Implementation Plan

### Phase 1: Remove Duplicates
1. Delete `lcm_eq_mul_of_coprime` from IntegerMatrixOrder.lean
2. Find and update call sites to use `Nat.Coprime.lcm_eq_mul`
3. Delete `orderOf_pow_of_dvd` from IntegerMatrixOrder.lean
4. Verify Mathlib signature compatibility, update call sites
5. Build and test

### Phase 2: Verification
6. Run `lake build`
7. Run TAIL verification with SafeVerify

---

## Files to Modify

| File | Changes |
|------|---------|
| `Definitions/IntegerMatrixOrder.lean` | Remove 2 duplicate lemmas (~30 lines) |
| `Proofs/CrystallographicRestriction.lean` | Update call sites |

---

## Call Sites to Update

### For `lcm_eq_mul_of_coprime`:
```bash
# Usage pattern change:
# Before: lcm_eq_mul_of_coprime h
# After:  h.lcm_eq_mul
```

### For `orderOf_pow_of_dvd`:
**SIGNATURE DIFFERENCE - Requires derivation:**
```lean
-- Custom version (IntegerMatrixOrder.lean:190):
lemma orderOf_pow_of_dvd {G : Type*} [Monoid G] (g : G) (m d : ℕ)
    (hm : orderOf g = m) (hd : d ∣ m) (hd_pos : 0 < d) (hm_pos : 0 < m) :
    orderOf (g ^ (m / d)) = d

-- Mathlib version (GroupTheory/OrderOfElement.lean:389):
lemma orderOf_pow_of_dvd {x : G} {n : ℕ} (hn : n ≠ 0) (dvd : n ∣ orderOf x) :
    orderOf (x ^ n) = orderOf x / n
```
**Derivation:** Custom version can be derived from Mathlib:
- Substitute `n = m / d` where `m = orderOf g`
- Since `d ∣ m`, we have `(m / d) ∣ m`
- Then `orderOf (g ^ (m/d)) = m / (m/d) = d`

---

## Verification

```bash
# Build
cd /Users/eric/GitHub/General_Crystallographic_Restriction
lake build

# Full verification
cd /Users/eric/GitHub/TAIL
SAFEVERIFY_PATH=/Users/eric/GitHub/SafeVerify-standalone/.lake/build/bin/safe_verify \
lake exe tailverify --safeverify /Users/eric/GitHub/General_Crystallographic_Restriction
```

---

## Impact Assessment

| Metric | Before | After |
|--------|--------|-------|
| Custom lemmas removed | 0 | 2 |
| Lines removed | 0 | ~30 |
| Mathlib alignment | Good | Better |
| Risk | - | Low (direct replacements) |
