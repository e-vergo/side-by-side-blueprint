# Plan: Move Graph Generation from Runway to Dress

## Current Status: Blocked - Needs Clarification

## Issue Identified

The Graph module in Runway has a critical dependency on `Runway.Latex.Ast`:

**Build.lean imports:**
```lean
import Runway.Latex.Ast
```

**Uses these types from Runway.Latex:**
- `Latex.Document` - parsed LaTeX document
- `Latex.Block` - block-level LaTeX content
- `Latex.TheoremMetadata` - metadata for theorem environments

**Dependency chain:**
- `Runway.Graph.Build` → imports `Runway.Latex.Ast`
- `Runway.Graph.Layout` → imports `Runway.Graph.Build`
- `Runway.Graph.Svg` → imports `Runway.Graph.Layout`

**The problem:**
- Runway depends on Dress (in lakefile.lean: `require Dress from git`)
- If Graph moves to Dress, it cannot import from Runway (would be circular)
- The LaTeX AST types are only available in Runway, not Dress

## Options to Resolve

### Option A: Also move LaTeX module to Dress
Move `Runway/Latex/` (Token.lean, Lexer.lean, Ast.lean, Parser.lean) to Dress alongside Graph.

**Pros:** Clean solution, Graph code stays unchanged
**Cons:** Larger scope than requested, may affect other Runway modules

### Option B: Rewrite Graph to not depend on LaTeX AST
Create standalone graph types in Dress that don't depend on LaTeX parsing.

**Pros:** Minimal code movement
**Cons:** Requires significant rewrite, may lose functionality

### Option C: Define minimal types in Dress
Create a subset of LaTeX types in Dress that Graph needs, independent of parsing.

**Pros:** Graph works independently
**Cons:** Type duplication, needs conversion layer

## Awaiting User Decision

Need clarification on which approach to take before proceeding with implementation.
