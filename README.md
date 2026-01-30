# Side-by-Side Blueprint

![Lean](https://img.shields.io/badge/Lean-v4.27.0-blue)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

Pure Lean toolchain for formalization documentation that displays formal proofs alongside LaTeX theorem statements.

## Screenshots

![Dashboard](SBS-Test/images/Dashboard.png)
*Dashboard with project stats and key theorems*

![Blueprint](SBS-Test/images/blueprint.png)
*Side-by-side LaTeX and Lean display*

![Dependency Graph](SBS-Test/images/dep_graph.png)
*Interactive dependency visualization*

![Paper](SBS-Test/images/paper_web.png)
*Generated paper with proof links*

## Features

- Side-by-side display of LaTeX statements and Lean proofs
- Interactive dependency graph with Sugiyama layout
- Dashboard with stats, key theorems, validation checks
- PDF/Paper generation with `\paperstatement{}` and `\paperfull{}` hooks
- 6-status color model for proof completion tracking
- Module reference support (`\inputleanmodule{}`)
- Rainbow bracket highlighting for nested expressions

## Repository Structure

| Repository | Purpose |
|------------|---------|
| [Runway](https://github.com/e-vergo/Runway) | Site generator + dashboard + paper/PDF |
| [Dress](https://github.com/e-vergo/Dress) | Artifact generation + graph layout + validation |
| [LeanArchitect](https://github.com/e-vergo/LeanArchitect) | `@[blueprint]` attribute and metadata |
| [subverso](https://github.com/e-vergo/subverso) | Syntax highlighting (fork with O(1) lookups) |
| [dress-blueprint-action](https://github.com/e-vergo/dress-blueprint-action) | GitHub Action for CI/CD |
| [SBS-Test](https://github.com/e-vergo/SBS-Test) | Minimal test project |
| [General_Crystallographic_Restriction](https://github.com/e-vergo/General_Crystallographic_Restriction) | Production example |
| [PrimeNumberTheoremAnd](https://github.com/e-vergo/PrimeNumberTheoremAnd) | Large-scale integration (530 annotations) |

## Getting Started

1. Add Dress as a dependency in your `lakefile.toml`:
   ```toml
   [[require]]
   name = "Dress"
   git = "https://github.com/e-vergo/Dress"
   rev = "main"
   ```

2. Add `@[blueprint]` annotations to theorems:
   ```lean
   @[blueprint "thm:main"]
   theorem main_result : ... := by
     ...
   ```

3. Create `blueprint/src/blueprint.tex` with LaTeX structure

4. Configure `runway.json` with site settings

5. For CI/CD, use [dress-blueprint-action](https://github.com/e-vergo/dress-blueprint-action)

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed build pipeline documentation.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture and build pipeline
- [GOALS.md](GOALS.md) - Project vision and design goals

## License

Apache 2.0 - see [LICENSE](LICENSE)
