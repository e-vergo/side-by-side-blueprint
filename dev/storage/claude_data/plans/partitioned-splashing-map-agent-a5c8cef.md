# Mathlib Compliance Review

## Files Reviewed
1. `/Users/eric/GitHub/General_Crystallographic_Restriction/Crystallographic/FiniteOrder/Basic.lean`
2. `/Users/eric/GitHub/General_Crystallographic_Restriction/Crystallographic/FiniteOrder/Order.lean`
3. `/Users/eric/GitHub/General_Crystallographic_Restriction/Crystallographic/Companion.lean`
4. `/Users/eric/GitHub/General_Crystallographic_Restriction/Crystallographic/Companion/Cyclotomic.lean`

---

## CRITICAL ISSUES

None. All files compile without errors and contain complete proofs.

---

## REQUIRED ISSUES (Must fix for Mathlib submission)

### File 1: FiniteOrder/Basic.lean

**R1.1 - Line 40: Name `integerMatrixOrders` violates convention**
- Issue: Type-like set definitions should use UpperCamelCase
- Current: `integerMatrixOrders`
- Mathlib standard: Would be `IntegerMatrixOrders`
- However, this appears to be a set (not a type), so snake_case could be defended

**R1.2 - Line 92: Name `embedMatrixSum` could be more descriptive**
- Issue: Doesn't clearly indicate it's a block diagonal embedding
- Suggestion: `embedMatrixBlockDiag` or `embedMatrixUpperLeft`
- The current name doesn't communicate that identity is placed in lower-right

**R1.3 - Line 110: Definition and declaration naming inconsistency**
- Issue: `embedMatrixSum.monoidHom` uses dot notation for a def, not lemma
- Mathlib convention: Dot notation typically reserved for lemmas about a definition
- Suggestion: Make this `embedMatrixSumMonoidHom` (no dot)

**R1.4 - Line 117: Similar issue with `embedMatrixSum.monoidHom_injective`**
- Should be: `embedMatrixSumMonoidHom_injective` or integrated into the definition

**R1.5 - Line 152: `finSumEquiv` is redundant**
- Issue: This is just `finSumFinEquiv.symm` from Mathlib
- Mathlib guideline: Don't create aliases for single applications of existing definitions
- Suggestion: Remove this def and use `finSumFinEquiv.symm` directly

**R1.6 - Line 158: `reindexMonoidEquiv` may duplicate Mathlib**
- Issue: This looks like it might exist in Mathlib already
- Action needed: Search Mathlib for `Matrix.reindex` or similar
- If it exists, use the library version

### File 2: FiniteOrder/Order.lean

**R2.1 - Line 58: Blueprint statement doesn't match theorem statement**
- Issue: Blueprint says "coprime orders" but theorem is about LCM (more general)
- The blueprint annotation is on the wrong theorem
- Fix: Update blueprint text to match `lcm_mem_integerMatrixOrders`

### File 3: Companion.lean

**R3.1 - Line 64: `companion` uses unused parameters**
- Issue: Parameters `_hp` and `_hn` are underscored but should be implicit/instances
- Current: `(p : R[X]) (_hp : p.Monic) (_hn : 0 < p.natDegree)`
- Mathlib style: If proofs are always provided explicitly, they should be named without underscore
- Better: Either use them in the definition or make them truly implicit with `{}`

**R3.2 - Line 76-108: `private` lemmas use inconsistent placement**
- Issue: All `private` lemmas should be marked clearly
- Some docstrings on private lemmas are overly detailed
- Mathlib guideline: Private lemmas need minimal docs, just enough for maintainer understanding

**R3.3 - Line 555: Long proof blocks exceed typical Mathlib style**
- Issue: The proof of `companion_charpoly` (lines 493-553) is 60 lines
- Mathlib preference: Break very long proofs into named intermediate lemmas
- The private lemmas help, but the main proof could still be shortened

### File 4: Companion/Cyclotomic.lean

**R4.1 - Line 41: Unused parameter naming**
- Issue: `(m : ℕ) (_hm : 0 < m)` - `_hm` is unused
- Better: Remove if truly unused, or omit the underscore if it's for documentation

**R4.2 - Line 56: Complex proof could use more structure**
- Issue: The proof of `companion_cyclotomic_orderOf` (lines 56-207) is 150+ lines
- This is pushing the limits of acceptable proof length
- Consider: Breaking the contradiction argument into a separate lemma

---

## SUGGESTED IMPROVEMENTS

### S1: Import Organization

**S1.1 - All files: Imports could be more minimal**
- FiniteOrder/Basic.lean imports `Mathlib.Algebra.CharP.Two` - only used for one small lemma
- Consider: Moving `ringChar_matrix_int` to a separate file or generalizing it
- Companion.lean has extensive imports - verify all are needed

### S2: Documentation

**S2.1 - Missing docstring for `private` intermediate constructs**
- Line 186 in FiniteOrder/Basic.lean: `let A'` could have a comment
- Line 500 in Companion.lean: The matrix `A` in the proof needs explanation

**S2.2 - Proof tactics documentation**
- Several uses of `omega` could benefit from brief comments explaining what arithmetic goal is being solved
- Example: Line 90 in Companion.lean has a naked `omega` - what's the constraint?

### S3: Proof Style

**S3.1 - Excessive use of `simp only` with single reducers**
- Multiple instances of `simp only [↓reduceIte]` could be `rfl` or split with `if_pos`/`if_neg`
- Example: Lines 87-96 in Companion.lean

**S3.2 - Some `have` statements lack names when they should have them**
- Line 75 in FiniteOrder/Order.lean: `have h1` could be `have orderOf_preserved`
- This improves readability and makes proof structure clearer

**S3.3 - Long `by` blocks could use structured proofs**
- The proof at lines 60-78 in FiniteOrder/Basic.lean could use `show` statements
- Would make the two directions of the `constructor` clearer

### S4: Code Organization

**S4.1 - Section usage**
- FiniteOrder/Basic.lean could use sections to group related lemmas
- Example: Lines 198-244 are all about `blockDiag2` - wrap in a section

**S4.2 - Notation considerations**
- `blockDiag2` could potentially have notation like `A ⊕ᵈ B` for clarity
- However, this might be overkill for a specialized result

### S5: Specific Simplifications

**S5.1 - Line 62 in FiniteOrder/Basic.lean**
- The proof structure could use `CharP.intCast_eq_zero_iff` more directly
- Current approach is more verbose than necessary

**S5.2 - Line 143 in FiniteOrder/Basic.lean**
- Direct use of `obtain` instead of `let` then `use` would be cleaner
- `obtain ⟨A, hA⟩ := hm` then destructure

**S5.3 - Line 241 in Companion.lean**
- `blockDiag2_pow` could reference a more general Mathlib lemma if one exists
- The proof is just `Matrix.fromBlocks_diagonal_pow` - consider if the wrapper is needed

### S6: Naming Consistency

**S6.1 - Theorem naming patterns**
- Mix of `_eq_` vs `_iff_` in lemma names
- Example: `blockDiag2_eq_one_iff` (line 225) is good
- But other similar results don't follow the pattern

**S6.2 - Parameter naming**
- Inconsistent use of `M, N, K` vs `m, n, k` for natural numbers
- Mathlib convention: Use lowercase for values, uppercase for types
- Example: Line 177 uses `M N` for nat values

---

## POSITIVE OBSERVATIONS

1. **Excellent documentation**: Module headers are comprehensive and well-structured
2. **Blueprint integration**: Good use of `@[blueprint]` annotations throughout
3. **No sorries**: All proofs are complete
4. **Good proof structure**: Private lemmas are used effectively to break down complex proofs
5. **Clear mathematical exposition**: The proofs follow clear mathematical arguments
6. **Appropriate automation**: Good balance of automation (simp, omega) vs explicit proof terms
7. **Type safety**: Good use of `Fin` and dependent types
8. **Clean compilation**: All files build without warnings or errors

---

## SUMMARY

**Ready for Mathlib submission after addressing Required issues.** The code quality is high, proofs are complete, and documentation is thorough. The main issues are:

1. Naming conventions (especially around definitions with dots)
2. Some definitional redundancy (aliases for existing Mathlib defs)
3. A few very long proofs that push style guidelines

None of these are blockers, but they should be addressed before submission. The Suggested improvements would make the code more polished but are not mandatory.

**Estimated work**: The Required issues could be addressed in 1-2 hours of focused refactoring. Most are naming/organizational changes rather than mathematical content changes.
