# Side-by-Side Blueprint Monorepo

> **This monorepo contains the Side-by-Side Blueprint formalization documentation toolchain.**

---

## Tool Development

A coherent, compact, and dedicated environment for developing the **Side-by-Side Blueprint tool** itself:

- **SubVerso** - Syntax highlighting with O(1) indexed lookups
- **Verso** - Document framework with SBSBlueprint/VersoPaper genres
- **LeanArchitect** - `@[blueprint]` attribute with 8 metadata + 3 status options
- **Dress** - Artifact generation, graph layout, validation
- **Runway** - Site generator, dashboard, paper/PDF

---

## Quick Reference

### Build Commands

```bash
./dev/build-sbs-test.sh   # SBS-Test (~2 min)
./dev/build-gcr.sh        # GCR (~5 min)
./dev/build-pnt.sh        # PNT (~20 min)
```

### Key Documentation

| Document | Purpose | Category |
|----------|---------|----------|
| [ARCHITECTURE.md](../permanent/ARCHITECTURE.md) | Build pipeline, components | Permanent |
| [GOALS.md](../permanent/GOALS.md) | Project vision, problem statement | Permanent |

---

## Repository Structure

```
Side-by-Side-Blueprint/
  forks/                    # Forked Lean 4 repositories
    subverso/               # Syntax highlighting
    verso/                  # Document framework
    LeanArchitect/          # @[blueprint] attribute
  toolchain/                # Core toolchain components
    Dress/                  # Artifact generation
    Runway/                 # Site generator
    SBS-Test/               # Minimal test project
    dress-blueprint-action/ # CI/CD + assets
  showcase/                 # Production examples
    General_Crystallographic_Restriction/
    PrimeNumberTheoremAnd/
  dev/                      # Development tooling
    markdowns/
      permanent/            # Architectural bedrock
      living/               # Current state (this file)
    build-*.sh              # One-click build scripts
```
