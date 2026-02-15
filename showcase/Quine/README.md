# Quine: A Self-Verifying Quine in Lean 4

![Lean](https://img.shields.io/badge/Lean-v4.27.0-blue)
![Mathlib](https://img.shields.io/badge/Mathlib-v4.27.0-purple)
![Nodes](https://img.shields.io/badge/Blueprint-8%20nodes-green)
![License](https://img.shields.io/badge/License-Apache%202.0-orange)

A quine in Lean 4 that proves its own correctness within Lean's type theory. The program outputs its own source code, and the proof of correctness is itself part of the quined output -- making the construction genuinely self-referential at multiple levels.

**Live Demo:** [e-vergo.github.io/Quine](https://e-vergo.github.io/Quine/)

This is a showcase project for the [Side-by-Side Blueprint](https://github.com/e-vergo/Side-By-Side-Blueprint) toolchain, demonstrating how formal self-reference can be documented with side-by-side displays, dependency graphs, and academic paper generation.

**What to explore:**
- **Blueprint**: Side-by-side documentation of the quine mechanism and its proofs
- **Dependency Graph**: 8-node visualization showing the self-referential dependency structure
- **Paper (HTML and PDF)**: Standalone academic paper with links to formal proofs
- **Dashboard**: Progress overview with key theorems and verification status

## The Concept

### Quines and Self-Reference

A *quine* is a program that, when executed, produces its own source code as output. The classical construction, rooted in Kleene's recursion theorem, decomposes the program into a *prefix* (the reconstruction logic) and a *data string* (encoding the suffix). The program reconstructs itself as:

```
prefix || quote(d) || d
```

where `d` is the data string and `quote` adds the necessary escaping.

### What Makes This Different

Most quines simply output their source. This one *proves* it does so, and the proof is part of the source being quined. Three layers of verification reinforce each other:

1. **Compile-time proof**: The Lean kernel verifies `quine_formula! = include_str! "Quine.lean"` by definitional equality
2. **Self-referential witness**: The quine output contains the text of its own correctness theorem
3. **Runtime verification**: The compiled binary can execute, capture its output, and empirically confirm it matches the source

### Main Result

**Theorem (Quine Correctness).** The quine formula equals the source file, verified by `rfl`.

```lean
theorem quine_correct : quine_formula! = include_str! "Quine.lean" := rfl
```

Both sides elaborate to identical string literals at compile time. The kernel verifies definitional equality -- no axioms, no tactics, just `rfl`.

### Self-Reference Theorems

The quine output contains the text of its own correctness proof:

```lean
theorem self_referential :
    (file_contains! "Quine.lean", "theorem quine_correct") = true := rfl
```

And its own blueprint annotations (the metadata generating the dependency graph):

```lean
theorem annotations_self_referential :
    (file_contains! "Quine.lean", "@[blueprint") = true := rfl
```

### Custom Elaborators

The construction uses three custom elaborators:

| Elaborator | Purpose |
|------------|---------|
| `include_str!` | Reads a file at elaboration time, returning its contents as a string literal |
| `quine_formula!` | Reconstructs the source from the data string `d` at elaboration time |
| `file_contains!` | Checks substring containment at elaboration time, reducing to `Bool.true` or `Bool.false` |

## Live Documentation

| Page | Description |
|------|-------------|
| [Dashboard](https://e-vergo.github.io/Quine/) | Project overview with verification status |
| [Blueprint](https://e-vergo.github.io/Quine/chapter-1.html) | Side-by-side LaTeX and Lean with proof toggles |
| [Dependency Graph](https://e-vergo.github.io/Quine/dep_graph.html) | Interactive 8-node visualization with pan/zoom |
| [Paper (HTML)](https://e-vergo.github.io/Quine/paper_tex.html) | Academic paper with links to Lean proofs |
| [Paper (PDF)](https://e-vergo.github.io/Quine/paper.pdf) | Printable PDF version |

## Project Structure

```
Quine/
├── Quine.lean                 # The quine: source, proofs, and executable (~160 lines)
├── blueprint/src/
│   ├── blueprint.tex          # LaTeX blueprint document
│   └── paper.tex              # Academic paper source
├── runway.json                # Site configuration
├── lakefile.toml              # Lake build configuration
└── lean-toolchain             # Lean version (v4.27.0)
```

The entire formalization lives in a single file. The 7 sections of `Quine.lean` are:

| Section | Contents |
|---------|----------|
| 1. Utilities | `findSubstr`, custom elaborators (`include_str!`, `quine_formula!`, `file_contains!`) |
| 2. Quine Data | `d` -- the Kleene payload encoding the file suffix |
| 3. Verification Harness | `verifyQuine` -- runtime output-vs-source comparison |
| 4. Executable | `main` -- reconstructs source from data, with `--verify` flag |
| 5. Proofs | `quine_correct`, `self_referential`, `annotations_self_referential` |
| 6. Verification Proofs | `verify_self_referential` -- the verification code is itself quined |
| 7. Post-Elaboration | `initialize` block -- imperative check during module initialization |

## Key Formalizations

| Label | Lean Name | Description |
|-------|-----------|-------------|
| `find_substr` | `Quine.findSubstr` | Substring finder for marker location |
| `quine_data` | `Quine.d` | Kleene payload encoding the file suffix |
| `verify_quine` | `Quine.verifyQuine` | Runtime binary-vs-source verification |
| `quine_main` | `main` | Quine entry point with `--verify` mode |
| `quine_correct` | `Quine.quine_correct` | Core theorem: quine formula = source file |
| `self_ref` | `Quine.self_referential` | Output contains its own correctness proof |
| `annotations_ref` | `Quine.annotations_self_referential` | Output contains its own blueprint metadata |
| `verify_self_ref` | `Quine.verify_self_referential` | Output contains its own verification code |

## Building

### Prerequisites

- Lean 4.27.0 (specified in `lean-toolchain`)
- Mathlib v4.27.0

### One-Click Build (Recommended)

From the monorepo root:

```bash
./dev/build-quine.sh
```

Or from the project directory:

```bash
cd showcase/Quine
python ../../../dev/scripts/build.py
```

This validates configuration, builds the toolchain in dependency order, fetches mathlib cache, compiles the quine with blueprint artifact generation, generates the dependency graph and site, and starts a local server at http://localhost:8000.

### Manual Build

```bash
# Fetch mathlib cache
lake exe cache get

# Build the Lean project with blueprint artifacts
lake build

# Generate dependency graph and manifest
lake exe Dress extract_blueprint graph

# Generate the site
lake exe Runway build runway.json
```

### Runtime Verification

After building, the quine binary can verify itself empirically:

```bash
.lake/build/bin/quine --verify
```

This executes the binary, captures its output, compares it to `Quine.lean`, and writes `soundness.json` for dashboard integration.

### CI/CD

The live documentation is built via GitHub Actions using [dress-blueprint-action](https://github.com/e-vergo/dress-blueprint-action).

## Documentation Toolchain

This project uses the **[Side-by-Side Blueprint](https://github.com/e-vergo/Side-By-Side-Blueprint)** toolchain, a pure Lean implementation consisting of:

- **Dress**: Captures blueprint artifacts during elaboration (syntax highlighting, code blocks, metadata)
- **Runway**: Generates the interactive website, dashboard, and paper
- **LeanArchitect**: Provides the `@[blueprint]` attribute for tagging declarations
- **SubVerso**: O(1) indexed syntax highlighting with semantic information

The toolchain runs entirely during build time and requires only Lean.

## Attribution

- **Side-by-Side Blueprint**: Documentation toolchain by [e-vergo](https://github.com/e-vergo/Side-By-Side-Blueprint)
- **LeanArchitect**: Based on [hanwenzhu/LeanArchitect](https://github.com/hanwenzhu/LeanArchitect)

## Author

Eric Vergo

## License

Apache 2.0
