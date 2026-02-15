/-
Verso blueprint document for LeanArchitect.
-/
import SBSBlueprint
import Architect

open Verso.Genre.SBSBlueprint

#doc (SBSBlueprint) "LeanArchitect Blueprint" =>

# Introduction

LeanArchitect provides the `@[blueprint]` attribute system for annotating Lean 4 declarations
with informal mathematical descriptions, dependency metadata, and formalization status.

This document presents the architecture and design of LeanArchitect through the Side-by-Side
Blueprint system — itself powered by LeanArchitect.

# Core Types

The foundational data structures that represent blueprint metadata.

## Node Status

:::leanNode "la:node-status"
:::

## Node Part

:::leanNode "la:node-part"
:::

## Node

:::leanNode "la:node"
:::

# Dependency Inference

:::leanNode "la:collect-used"
:::

# Output Generation

:::leanNode "la:output-latex-results"
:::
