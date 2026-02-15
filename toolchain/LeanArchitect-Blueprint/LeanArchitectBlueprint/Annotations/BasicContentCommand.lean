import Architect

open Architect

namespace LeanArchitectBlueprint.Annotations

-- === Architect.Basic ===

-- NodeStatus instances (ToJson, FromJson, ToExpr)
-- Note: Inhabited instance is trivial (just sets default), not separately annotated.

attribute [blueprint "la:node-status-to-json"
  (title := "NodeStatus JSON Serialization")
  (statement := /-- Serializes \texttt{NodeStatus} to its canonical JSON string representation.
  Each constructor maps to a lowercase string: \texttt{"notReady"}, \texttt{"ready"},
  \texttt{"sorry"}, \texttt{"proven"}, \texttt{"fullyProven"}, \texttt{"mathlibReady"}.

  These strings appear in \texttt{manifest.json} and are consumed by Dress and Runway
  for graph rendering and dashboard display.

  \uses{la:node-status} -/)
  (proof := /-- Pattern-matches on all six constructors, returning the corresponding
  JSON string literal. -/)
  (uses := ["la:node-status"])]
  instToJsonNodeStatus

attribute [blueprint "la:node-status-from-json"
  (title := "NodeStatus JSON Deserialization")
  (statement := /-- Deserializes a JSON string to \texttt{NodeStatus}, with backwards
  compatibility for legacy status values.

  In addition to the six canonical strings, accepts:
  \begin{itemize}
    \item \texttt{"stated"} $\mapsto$ \texttt{notReady} (pre-v2 format)
    \item \texttt{"inMathlib"} $\mapsto$ \texttt{mathlibReady} (pre-v2 format)
  \end{itemize}

  Returns an error for any unrecognized string, ensuring strict validation
  of manifest data.

  \uses{la:node-status} -/)
  (proof := /-- Pattern-matches on the input string with a catch-all that throws a
  descriptive error message. -/)
  (uses := ["la:node-status"])]
  instFromJsonNodeStatus

attribute [blueprint "la:node-status-to-expr"
  (title := "NodeStatus Metaprogramming Serialization")
  (statement := /-- Converts \texttt{NodeStatus} to a Lean expression (\texttt{Expr}) for
  compile-time metaprogramming. Each constructor is mapped to its corresponding
  \texttt{mkConst} application.

  This instance is required by the \texttt{@[blueprint]} attribute elaborator,
  which stores \texttt{Node} values (containing \texttt{NodeStatus} fields) into
  the environment extension at elaboration time.

  \uses{la:node-status} -/)
  (proof := /-- Manual instance mapping each constructor to \texttt{mkConst ``NodeStatus.<ctor>}.
  The type expression is \texttt{mkConst ``NodeStatus}. -/)
  (uses := ["la:node-status"])]
  instToExprNodeStatus

attribute [blueprint "la:node-to-expr"
  (keyDeclaration := true)
  (title := "Node Metaprogramming Serialization")
  (statement := /-- Manual \texttt{ToExpr} instance for \texttt{Node} that explicitly serializes
  all 16 fields, including those with default values.

  The derived \texttt{ToExpr} instance for structures with default-valued fields
  produces incorrect expressions---it omits defaults, causing deserialization to
  silently use wrong values. This manual instance ensures field-by-field fidelity
  via \texttt{Lean.mkAppN (mkConst ``Node.mk) \#[toExpr n.field1, \ldots]}.

  \uses{la:node, la:node-part, la:node-status} -/)
  (proof := /-- Constructs the expression by applying \texttt{Node.mk} to an array of
  all 16 field expressions, each produced by recursive \texttt{toExpr} calls.
  The type expression is \texttt{mkConst ``Node}. -/)
  (uses := ["la:node", "la:node-part", "la:node-status"])]
  instToExprNode

attribute [blueprint "la:node-not-ready"
  (title := "Node notReady Predicate")
  (statement := /-- Backwards-compatibility predicate that checks whether a node's status
  is \texttt{notReady}. Returns \texttt{true} iff \texttt{n.status == .notReady}.

  Preserved for API consumers that predate the six-status model.

  \uses{la:node, la:node-status} -/)
  (proof := /-- Direct equality check on the \texttt{status} field using \texttt{BEq}. -/)
  (uses := ["la:node", "la:node-status"])]
  Architect.Node.notReady

attribute [blueprint "la:node-with-pos"
  (keyDeclaration := true)
  (title := "Node With Position")
  (statement := /-- Extension of \texttt{Node} that adds source location metadata
  for mapping blueprint nodes back to their Lean source files.

  Fields:
  \begin{itemize}
    \item \texttt{hasLean : Bool} --- whether the node's name exists in the environment
      (should always be \texttt{true} for nodes added by \texttt{@[blueprint]})
    \item \texttt{location : Option DeclarationLocation} --- the module and source range
    \item \texttt{file : Option System.FilePath} --- resolved filesystem path
  \end{itemize}

  Used by \texttt{BlueprintContent} to order declarations by source position
  and by Dress to generate per-declaration artifacts with source links.

  \uses{la:node} -/)
  (proof := /-- A structure extending \texttt{Node} with three additional fields.
  Derives \texttt{Repr} but not \texttt{ToJson} (position data is transient). -/)
  (uses := ["la:node"])]
  Architect.NodeWithPos

attribute [blueprint "la:node-to-node-with-pos"
  (title := "Node to NodeWithPos Conversion")
  (statement := /-- Enriches a \texttt{Node} with source location data by querying the
  Lean environment at elaboration time.

  The resolution proceeds in three steps:
  \begin{enumerate}
    \item Check if the node's \texttt{name} exists in the environment
    \item Look up the module index and declaration ranges via
      \texttt{getModuleIdxFor?} and \texttt{findDeclarationRanges?}
    \item Resolve the source file path via \texttt{findWithExt "lean"} on the search path
  \end{enumerate}

  If the name is not in the environment, returns \texttt{hasLean := false} with
  \texttt{none} for location and file.

  \uses{la:node, la:node-with-pos} -/)
  (proof := /-- A \texttt{CoreM} computation that queries the environment for module indices,
  declaration ranges, and resolves the source file via the search path. -/)
  (uses := ["la:node", "la:node-with-pos"])]
  Architect.Node.toNodeWithPos

attribute [blueprint "la:latex-label-state"
  (title := "LaTeX Label Lookup State")
  (statement := /-- The state type for the LaTeX label $\to$ Lean names mapping:
  $\texttt{SMap String (Array Name)}$.

  This is a sorted map from LaTeX label strings to arrays of Lean constant names,
  supporting the many-to-one relationship where multiple Lean declarations can
  share a single LaTeX label. -/)
  (proof := /-- A type abbreviation for \texttt{SMap String (Array Name)}. -/)]
  Architect.LatexLabelToLeanNames.State

attribute [blueprint "la:latex-label-entry"
  (title := "LaTeX Label Lookup Entry")
  (statement := /-- A single entry in the LaTeX label registry: a pair of a LaTeX label
  string and the Lean constant name it maps to.

  Type: $\texttt{String} \times \texttt{Name}$. -/)
  (proof := /-- A type abbreviation for \texttt{String $\times$ Name}. -/)]
  Architect.LatexLabelToLeanNames.Entry

attribute [blueprint "la:add-lean-name-of-latex-label"
  (title := "Register LaTeX Label Mapping")
  (statement := /-- Registers a mapping from a LaTeX label to a Lean constant name in the
  persistent environment extension \texttt{latexLabelToLeanNamesExt}.

  This is called during \texttt{@[blueprint]} attribute elaboration to record
  the association between a node's \texttt{latexLabel} and its fully qualified
  Lean name.

  \uses{la:latex-label-state, la:latex-label-entry} -/)
  (proof := /-- Delegates to \texttt{latexLabelToLeanNamesExt.addEntry} with a
  \texttt{(latexLabel, name)} pair. -/)
  (uses := ["la:latex-label-state", "la:latex-label-entry"])]
  Architect.addLeanNameOfLatexLabel

attribute [blueprint "la:get-lean-names-of-latex-label"
  (title := "Resolve LaTeX Label to Lean Names")
  (statement := /-- Looks up all Lean constant names associated with a given LaTeX label
  string. Returns the array of names, or an empty array if the label is not
  registered.

  Used by Dress during dependency graph construction to resolve
  \texttt{usesLabels} references to actual Lean constants.

  \uses{la:latex-label-state} -/)
  (proof := /-- Queries \texttt{latexLabelToLeanNamesExt.getState} and uses
  \texttt{findD} with an empty array default. -/)
  (uses := ["la:latex-label-state"])]
  Architect.getLeanNamesOfLatexLabel

attribute [blueprint "la:try-resolve-const"
  (title := "Resolve Identifier with Error Recovery")
  (statement := /-- Resolves a user-provided identifier to a fully qualified Lean constant name
  using \texttt{realizeGlobalConstNoOverloadWithInfo}.

  If resolution fails and the option \texttt{blueprint.ignoreUnknownConstants} is
  \texttt{true}, silently returns the raw identifier name instead of throwing.
  Otherwise, throws an error with a hint about the option.

  This powers the \texttt{uses} and \texttt{proofUses} fields of
  \texttt{@[blueprint]}, allowing authors to reference constants that may
  not yet exist (forward references during incremental formalization). -/)
  (proof := /-- A \texttt{CoreM} computation wrapped in try/catch. On failure, checks
  the \texttt{blueprint.ignoreUnknownConstants} option to decide between
  returning the raw identifier or re-throwing with an extended message. -/)]
  Architect.tryResolveConst


-- === Architect.Content ===

attribute [blueprint "la:blueprint-content"
  (keyDeclaration := true)
  (title := "Blueprint Content")
  (statement := /-- The sum type for elements that appear in a module's blueprint output.
  A module's blueprint content is the ordered interleaving of:

  \begin{itemize}
    \item \texttt{node}: an annotated declaration (\texttt{NodeWithPos}) from
      \texttt{@[blueprint]}
    \item \texttt{modDoc}: a module docstring from \texttt{blueprint\_comment}
  \end{itemize}

  Contents are sorted by source position to preserve the author's intended
  narrative flow. This is analogous to doc-gen4's \texttt{ModuleMember}.

  \uses{la:node-with-pos} -/)
  (proof := /-- A two-constructor inductive type. -/)
  (uses := ["la:node-with-pos"])]
  Architect.BlueprintContent

attribute [blueprint "la:blueprint-content-decl-range"
  (title := "Blueprint Content Declaration Range")
  (statement := /-- Extracts the source declaration range from a \texttt{BlueprintContent}
  value, used for sorting contents by source position.

  For \texttt{node} values, delegates to the \texttt{NodeWithPos.location} field.
  For \texttt{modDoc} values, uses the \texttt{ModuleDoc.declarationRange} field.
  Returns \texttt{none} if the node has no location information.

  \uses{la:blueprint-content, la:node-with-pos} -/)
  (proof := /-- Pattern-matches on constructors, extracting the range via
  \texttt{Option.map} for nodes and \texttt{some} for module docs. -/)
  (uses := ["la:blueprint-content", "la:node-with-pos"])]
  Architect.BlueprintContent.declarationRange

attribute [blueprint "la:blueprint-content-order"
  (title := "Blueprint Content Source Order")
  (statement := /-- A comparison function for sorting \texttt{BlueprintContent} values by
  their source position. Uses \texttt{Position.lt} on the \texttt{pos} field
  of declaration ranges.

  When both values have ranges, compares by starting position. If only the
  left value has a range, it sorts first. Otherwise, preserves the original
  order (returns \texttt{false}).

  \uses{la:blueprint-content, la:blueprint-content-decl-range} -/)
  (proof := /-- Pattern-matches on the pair of \texttt{Option DeclarationRange} values
  and delegates to \texttt{Position.lt}. -/)
  (uses := ["la:blueprint-content", "la:blueprint-content-decl-range"])]
  Architect.BlueprintContent.order

attribute [blueprint "la:get-main-module-blueprint-contents"
  (keyDeclaration := true)
  (title := "Get Current Module Blueprint Contents")
  (statement := /-- Retrieves all blueprint contents (nodes and module docstrings) from the
  current module being elaborated, sorted by source position.

  This is the primary entry point for Dress's per-module artifact generation:
  during the \texttt{dressed} Lake facet, each module calls this function to
  collect its annotated declarations and docstrings for LaTeX output.

  \uses{la:blueprint-content, la:blueprint-content-order, la:node-to-node-with-pos} -/)
  (proof := /-- A \texttt{CoreM} computation that:
  \begin{enumerate}
    \item Reads all entries from \texttt{blueprintExt} and converts each to
      \texttt{NodeWithPos} via \texttt{Node.toNodeWithPos}
    \item Reads module docstrings from \texttt{moduleBlueprintDocExt}
    \item Concatenates and sorts by \texttt{BlueprintContent.order} via \texttt{qsort}
  \end{enumerate} -/)
  (uses := ["la:blueprint-content", "la:blueprint-content-order", "la:node-to-node-with-pos"])]
  Architect.getMainModuleBlueprintContents

attribute [blueprint "la:get-blueprint-contents"
  (title := "Get Imported Module Blueprint Contents")
  (statement := /-- Retrieves all blueprint contents from a previously imported module,
  identified by its fully qualified module name.

  Unlike \texttt{getMainModuleBlueprintContents}, this operates on imported
  (already-compiled) modules via \texttt{getModuleIdx?} and
  \texttt{getModuleEntries}. Returns an empty array if the module is not found.

  Used by Runway when rendering chapters: each chapter page queries the
  blueprint contents of its constituent modules.

  \uses{la:blueprint-content, la:blueprint-content-order, la:node-to-node-with-pos} -/)
  (proof := /-- A \texttt{CoreM} computation that looks up the module index, reads
  entries from both \texttt{blueprintExt} and \texttt{moduleBlueprintDocExt}
  via their module-level accessors, then sorts by source position. -/)
  (uses := ["la:blueprint-content", "la:blueprint-content-order", "la:node-to-node-with-pos"])]
  Architect.getBlueprintContents


-- === Architect.Command ===

attribute [blueprint "la:add-main-module-blueprint-doc"
  (title := "Add Module Blueprint Docstring")
  (statement := /-- Registers a module docstring in the \texttt{moduleBlueprintDocExt}
  persistent environment extension.

  Called by the \texttt{blueprint\_comment} command elaborator to store
  documentation text that will be interleaved with annotated declarations
  in the module's blueprint output. -/)
  (proof := /-- Delegates to \texttt{moduleBlueprintDocExt.addEntry} with the
  provided \texttt{ModuleDoc} value. -/)]
  Architect.addMainModuleBlueprintDoc

attribute [blueprint "la:get-main-module-blueprint-doc"
  (title := "Get Current Module Blueprint Docstrings")
  (statement := /-- Retrieves all \texttt{blueprint\_comment} docstrings registered in the
  current module as a \texttt{PersistentArray ModuleDoc}.

  Returns the full state of \texttt{moduleBlueprintDocExt}, which accumulates
  entries added during elaboration of the current module.

  \uses{la:add-main-module-blueprint-doc} -/)
  (proof := /-- Delegates to \texttt{moduleBlueprintDocExt.getState}. -/)
  (uses := ["la:add-main-module-blueprint-doc"])]
  Architect.getMainModuleBlueprintDoc

attribute [blueprint "la:get-module-blueprint-doc"
  (title := "Get Imported Module Blueprint Docstrings")
  (statement := /-- Retrieves \texttt{blueprint\_comment} docstrings from an imported module,
  identified by its fully qualified name.

  Returns \texttt{none} if the module is not found in the environment's import
  table. Uses \texttt{getModuleEntries} at server export level to access
  the docstrings persisted by \texttt{moduleBlueprintDocExt}.

  \uses{la:add-main-module-blueprint-doc} -/)
  (proof := /-- Looks up the module index via \texttt{env.getModuleIdx?} and maps
  over the result to call \texttt{moduleBlueprintDocExt.getModuleEntries}
  with \texttt{level := .server}. -/)
  (uses := ["la:add-main-module-blueprint-doc"])]
  Architect.getModuleBlueprintDoc?

end LeanArchitectBlueprint.Annotations
