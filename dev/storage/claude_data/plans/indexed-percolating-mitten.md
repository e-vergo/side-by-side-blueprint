# Plan: Expand Chebotarev Cyclotomic Blueprint (Issue #584)

## Objective
Decompose the three coarse lemmas in Section 2.5 of the blueprint into smaller, formalizable sub-lemmas using `@[blueprint]` annotations in Lean.

## Current State
- **File**: `PrimeNumberTheoremAnd/Wiener.lean` (lines 4011-4085)
- **Existing lemmas** (as `blueprint_comment`):
  1. `Dedekind-factor`: ζ_L(s) = ∏_χ L(χ,s)
  2. `Dedekind-pole`: ζ_L has simple pole at s=1
  3. `Dedekind-nonvanishing`: L(χ,s) ≠ 0 on Re(s)=1 for χ ≠ 1
- **References**: Sharifi's notes Props 7.1.16, 7.1.19, Thm 7.1.12

## Execution Plan (Sequential Agents)

### Agent 1: Research & Outline Dedekind-factor Decomposition
**Task**: Research the mathematical decomposition of ζ_L(s) = ∏_χ L(χ,s) and produce a detailed outline of sub-lemmas needed.

Expected sub-lemmas:
- Definition of Dedekind zeta function ζ_L
- Definition of Artin L-function for 1-dimensional characters
- Prime ideal factorization in cyclotomic extensions
- Frobenius element characterization
- Character orthogonality relations
- Local factor identity matching

**Output**: Detailed list of sub-lemma statements with dependencies

---

### Agent 2: Research & Outline Dedekind-pole Decomposition
**Task**: Research the proof that ζ_L has a simple pole at s=1 and identify sub-lemmas.

Expected sub-lemmas:
- Euler product convergence for Re(s) > 1
- Meromorphic continuation to Re(s) > 0
- Class number formula components (class number, regulator, discriminant)
- Residue formula at s=1
- Order of pole = 1

**Output**: Detailed list of sub-lemma statements with dependencies

---

### Agent 3: Research & Outline Dedekind-nonvanishing Decomposition
**Task**: Research the non-vanishing proof for Artin L-functions on Re(s)=1 and identify sub-lemmas.

Expected sub-lemmas:
- At s=1: derive from factorization + simple pole (if L(χ,1)=0, get contradiction)
- Trivial character gives ζ_K(s)
- For s=1+it, t≠0: adapt 3-4 trick or Mertens argument
- Logarithmic derivative bounds

**Output**: Detailed list of sub-lemma statements with dependencies

---

### Agent 4: Write Lean Annotations
**Task**: Take the three decomposition outlines and write them as `@[blueprint]` annotations in `PrimeNumberTheoremAnd/Wiener.lean`, replacing the existing coarse `blueprint_comment` blocks.

Format per the project's LeanArchitect conventions:
```lean
@[blueprint "label"
  (statement := /-- LaTeX statement -/)
  (uses := [dep1, dep2])
  (latexEnv := "lemma")
]
theorem name : statement := sorry
```

**Output**: Modified Wiener.lean with expanded blueprint annotations

---

### Agent 5: Verify & Validate
**Task**:
1. Run `lake build` to ensure no syntax errors
2. Check that blueprint generates correctly
3. Review dependency graph for correctness

**Output**: Confirmation of successful build and blueprint generation

## Critical Files
- `PrimeNumberTheoremAnd/Wiener.lean` (primary modification target)
- `blueprint/src/blueprint.tex` (verify integration)

## Verification
1. `lake build PrimeNumberTheoremAnd.Wiener` compiles without errors
2. Blueprint website regenerates with new sub-lemmas visible
3. Dependency graph shows correct `\uses{}` relationships
