/-
Verso blueprint document for LeanArchitect.
Presents the architecture through key declarations using the SBSBlueprint genre.
-/
import SBSBlueprint
import LeanArchitectBlueprint

open Verso.Genre.SBSBlueprint

#doc (SBSBlueprint) "LeanArchitect Blueprint" =>

# Introduction

LeanArchitect provides the `@[blueprint]` attribute for annotating Lean 4 declarations
with informal mathematical descriptions, dependency metadata, and formalization status.
It is the foundation layer of the Side-by-Side Blueprint toolchain.

This document is self-referential: LeanArchitect's `@[blueprint]` attribute is used
here to document LeanArchitect itself.

# Core Types

The foundational data structures that represent blueprint metadata.

## Node Status

The six-level status model drives visual representation in the dependency graph:

:::leanNode "la:node-status"
:::

## Node Part

Each node has a statement and optionally a proof, both represented as NodePart values:

:::leanNode "la:node-part"
:::

## Node

The central data structure aggregating all annotation metadata:

:::leanNode "la:node"
:::

## Node With Position

Enriches a Node with source location data for mapping back to Lean files:

:::leanNode "la:node-with-pos"
:::

# The `@[blueprint]` Attribute

## Configuration

All 24 user-facing options are captured in the Config structure:

:::leanNode "la:config"
:::

## Parsing the Uses Clause

Dependency declarations are parsed into four parallel arrays:

:::leanNode "la:elab-blueprint-uses"
:::

## Main Configuration Parser

The central parser transforms raw syntax into a populated Config:

:::leanNode "la:elab-blueprint-config"
:::

## Node Assembly

The Config is transformed into a complete Node through a multi-step assembly process:

:::leanNode "la:mk-node"
:::

# Dependency Inference

## The CollectUsed Traversal

A recursive expression tree walk discovers blueprint dependencies:

:::leanNode "la:collect-used-collect"
:::

## Top-Level API

Returns disjoint statement and proof dependency sets:

:::leanNode "la:collect-used"
:::

# Validation

## Statement Validation

Advisory diagnostics for LaTeX quality:

:::leanNode "la:validate-statement"
:::

## Cross-Reference Analysis

Heuristic drift detection between Lean signatures and LaTeX statements:

:::leanNode "la:cross-reference-check"
:::

# Output Generation

## LaTeX Output

The complete output for a module, consisting of a header and per-node artifacts:

:::leanNode "la:latex-output"
:::

## Dependency Resolution

Resolves the dependency set of a NodePart into LaTeX labels:

:::leanNode "la:node-part-infer-uses"
:::

## Node Rendering

Converts a positioned node into its full LaTeX representation:

:::leanNode "la:node-with-pos-to-latex"
:::

## Filesystem Output

Writes the module's complete LaTeX output to disk:

:::leanNode "la:output-latex-results"
:::

# Integration Points

## RPC Endpoint

Blueprint metadata for the VS Code infoview panel:

:::leanNode "la:blueprint-info"
:::

## Proof Docstrings

Tactic-level documentation accumulated during proof construction:

:::leanNode "la:get-proof-doc-string"
:::

## Module Loading

Offline analysis via environment reconstruction:

:::leanNode "la:run-env-of-imports"
:::
