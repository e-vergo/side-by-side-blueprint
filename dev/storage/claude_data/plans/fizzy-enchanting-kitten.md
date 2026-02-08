# Plan: SBS Housekeeping & Test Project Setup

## Overview

Three sequential tasks to complete the repository reorganization and create a CI test project:

1. Move and rename `SBS.md` → `ARCHITECTURE.md` in parent directory
2. Update `build_blueprint.sh` paths
3. Fork LeanProject and create `SBS-Test` MVP project

---

## Task 1: Move and Rename SBS.md

**Agent instruction**: Move file and update internal path references.

**Actions**:
```bash
mv /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction/SBS.md \
   /Users/eric/GitHub/Side-By-Side-Blueprint/ARCHITECTURE.md
```

**Edit** `ARCHITECTURE.md` lines 9-14 - update repository paths from `/Users/eric/GitHub/{repo}` to `/Users/eric/GitHub/Side-By-Side-Blueprint/{repo}`:
- LeanArchitect
- Dress
- Runway
- subverso
- dress-blueprint-action
- General_Crystallographic_Restriction

---

## Task 2: Update build_blueprint.sh

**File**: [scripts/build_blueprint.sh](General_Crystallographic_Restriction/scripts/build_blueprint.sh)

**Edit** lines 26-29:
```bash
# FROM:
SUBVERSO_PATH="/Users/eric/GitHub/subverso"
LEAN_ARCHITECT_PATH="/Users/eric/GitHub/LeanArchitect"
DRESS_PATH="/Users/eric/GitHub/Dress"
RUNWAY_PATH="/Users/eric/GitHub/Runway"

# TO:
SUBVERSO_PATH="/Users/eric/GitHub/Side-By-Side-Blueprint/subverso"
LEAN_ARCHITECT_PATH="/Users/eric/GitHub/Side-By-Side-Blueprint/LeanArchitect"
DRESS_PATH="/Users/eric/GitHub/Side-By-Side-Blueprint/Dress"
RUNWAY_PATH="/Users/eric/GitHub/Side-By-Side-Blueprint/Runway"
```

---

## Task 3: Create SBS-Test Project

### 3.1 Fork and Clone
```bash
gh repo fork leanprover-community/LeanProject --clone=false --fork-name SBS-Test --org e-vergo
gh repo clone e-vergo/SBS-Test /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
```

### 3.2 Project Structure
```
SBS-Test/
├── SBSTest.lean              # Root import
├── SBSTest/
│   ├── Chapter1/
│   │   ├── Definitions.lean  # @[blueprint] defs, term mode
│   │   └── Lemmas.lean       # Tactic mode proofs
│   ├── Chapter2/
│   │   └── Theorems.lean     # Integer theorems, LaTeX math
│   └── Chapter3/
│       └── Advanced.lean     # Primes, cross-chapter deps
├── blueprint/
│   └── src/
│       └── blueprint.tex     # Multi-chapter structure
├── lakefile.toml             # Mathlib + Dress + Runway deps
├── runway.json               # Site config
└── .github/
    └── workflows/
        └── blueprint.yml     # dress-blueprint-action CI
```

### 3.3 Feature Coverage

| Feature | Test Location |
|---------|---------------|
| `@[blueprint "label"]` attribute | All Lean files |
| Definitions (`def:` labels) | Chapter1/Definitions.lean |
| Theorems (`thm:` labels) | Chapter2/Theorems.lean, Chapter3 |
| Lemmas (`lem:` labels) | Chapter1/Lemmas.lean |
| Term mode proofs | Chapter1/Definitions.lean |
| Tactic mode proofs | Chapter1/Lemmas.lean, Chapter2, Chapter3 |
| `\uses{...}` dependencies | Cross-references between nodes |
| Multi-chapter structure | 4 chapters in blueprint.tex |
| `\inputleannode{label}` | Throughout blueprint.tex |
| Syntax highlighting + hovers | Automatic via Dress/SubVerso |
| Proof toggle sync | Tactic proofs |
| Homepage stats | Automatic via Runway |
| Dependency graph | Generated from `\uses{}` |
| Mathlib dependency | Tests cache workflow |
| GitHub Actions CI | `.github/workflows/blueprint.yml` |

### 3.4 Key Files Content

**lakefile.toml**:
- `name = "SBSTest"`
- Requires: mathlib, Dress (e-vergo/Dress), Runway (e-vergo/Runway)

**runway.json**:
```json
{
  "title": "SBS-Test: Blueprint Feature Demonstration",
  "projectName": "SBSTest",
  "githubUrl": "https://github.com/e-vergo/SBS-Test",
  "blueprintTexPath": "blueprint/src/blueprint.tex"
}
```

**blueprint.yml workflow**:
- Uses `e-vergo/dress-blueprint-action@v1`
- Enables: build-dressed, blueprint-facet, build-pdf, build-web
- Uses Mathlib cache
- Deploys to GitHub Pages on main branch

### 3.5 Lean Content (MVP)

~13 declarations across 4 files:
- **Chapter1/Definitions.lean**: `isPositive`, `double`, `succ_positive`, `double_positive`
- **Chapter1/Lemmas.lean**: `add_positive`, `max_positive` (tactic proofs)
- **Chapter2/Theorems.lean**: `square_nonneg`, `sum_squares_nonneg`, `binomial_square`
- **Chapter3/Advanced.lean**: `two_prime`, `three_prime`, `odd_prime`, `double_succ_positive`

**@[blueprint] syntax** (following existing pattern):
```lean
@[blueprint "thm:label"
  (statement := /-- LaTeX statement with $math$. \uses{dep1, dep2} -/)
  (proof := /-- Proof explanation. -/)]
theorem name : Type := proof
```

---

## Execution Order

1. **Agent 1**: Move SBS.md → ARCHITECTURE.md, update internal paths
2. **Agent 2**: Update build_blueprint.sh paths (lines 26-29)
3. **Agent 3**: Fork LeanProject, create SBS-Test structure
4. **Agent 4**: Write Lean source files (Chapter1, Chapter2, Chapter3)
5. **Agent 5**: Write blueprint.tex, runway.json, workflow yml
6. **Agent 6**: Initial commit and push to e-vergo/SBS-Test

---

## Verification

1. **Local test of build_blueprint.sh**:
   ```bash
   cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
   ./scripts/build_blueprint.sh
   ```
   Verify it finds all dependency paths correctly.

2. **SBS-Test local build**:
   ```bash
   cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
   lake exe cache get
   BLUEPRINT_DRESS=1 lake build
   lake build :blueprint
   ```

3. **GitHub Actions**: Push to main and verify CI succeeds, Pages deploys.

4. **Visual inspection**: Check deployed site has:
   - Multi-chapter navigation
   - Side-by-side Lean/LaTeX display
   - Hover tooltips on Lean code
   - Proof toggle working
   - Dependency graph visible
   - Homepage stats accurate
